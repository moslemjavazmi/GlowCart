
import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from cart.models import Cart, CartItem

from datetime import timedelta


from orders.models import (
    Order,
    OrderItem,
    Address,
    InventoryReservation,
)

def generate_order_number():
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:10].upper()

    return f"GC-{date_part}-{random_part}"


@transaction.atomic
def create_order(*, user, address_id):
    # 1. آدرس باید متعلق به همین کاربر باشد.

    address = Address.objects.filter(
        id=address_id,
        user=user,
    ).first()

    if not address:
        raise ValidationError({
            "address_id": "Address not found."
        })

    # 2. قفل کردن سبد خرید کاربر

    cart = Cart.objects.select_for_update().filter(
        user=user
    ).first()

    if not cart:
        raise ValidationError({
            "cart": "Your cart is empty."
        })

    # 3. دریافت آیتم‌های سبد خرید

    cart_items = list(
        CartItem.objects.filter(
            cart=cart
        ).select_related(
            "variant",
            "variant__product",
        )
    )

    if not cart_items:
        raise ValidationError({
            "cart": "Your cart is empty."
        })

    # 4. قفل کردن ردیف‌های محصولات برای جلوگیری از
    # خرید هم‌زمان بیشتر از موجودی در PostgreSQL.

    variant_ids = [item.variant_id for item in cart_items]

    locked_variants = {
        variant.id: variant
        for variant in ProductVariant.objects.select_for_update().filter(
            id__in=variant_ids
        ).select_related("product")
    }

    subtotal = Decimal("0.00")
    order_items_data = []

    # 5. بررسی قیمت، وضعیت و موجودی

    for cart_item in cart_items:
        variant = locked_variants.get(cart_item.variant_id)

        if not variant:
            raise ValidationError({
                "cart": "A product variant no longer exists."
            })

        if not variant.is_active or not variant.product.is_active:
            raise ValidationError({
                "cart": f"{variant.name} is no longer available."
            })

        if cart_item.quantity > variant.stock:
            raise ValidationError({
                "cart": (
                    f"Insufficient stock for {variant.name}. "
                    f"Available: {variant.stock}"
                )
            })

        unit_price = variant.price
        line_total = unit_price * cart_item.quantity

        subtotal += line_total

        order_items_data.append({
            "variant": variant,
            "product_name": variant.product.name,
            "variant_name": variant.name,
            "sku": variant.sku,
            "unit_price": unit_price,
            "quantity": cart_item.quantity,
            "line_total": line_total,
        })

    # 6. محاسبه مبلغ نهایی در Backend

    shipping_cost = Decimal("0.00")
    discount_amount = Decimal("0.00")

    total_amount = (
        subtotal
        + shipping_cost
        - discount_amount
    )

    if total_amount < 0:
        raise ValidationError({
            "total_amount": "Invalid order total."
        })

    # 7. ساخت سفارش با Snapshot آدرس
    expires_at = timezone.now() + timedelta(minutes=20)
    order = Order.objects.create(
        user=user,
        address=address,
        status=Order.Status.AWAITING_PAYMENT,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount_amount=discount_amount,
        total_amount=total_amount,
        expires_at=expires_at,

        recipient_name=address.recipient_name,
        phone_number=address.phone_number,
        province=address.province,
        city=address.city,
        postal_code=address.postal_code,
        address_line=address.address_line,
    )

    # 8. ساخت آیتم‌های سفارش و کاهش موجودی

    order_items = []

    for item_data in order_items_data:
        variant = item_data["variant"]

        order_items.append(
            OrderItem(
                order=order,
                **item_data,
            )
        )

        variant.stock -= item_data["quantity"]
        variant.save(update_fields=["stock"])

    OrderItem.objects.bulk_create(order_items)
    InventoryReservation.objects.bulk_create([
        InventoryReservation(
            order=order,
            variant=item.variant,
            quantity=item.quantity,
            expires_at=expires_at,
        )
        for item in order.items.all()
    ])
    # 9. خالی کردن سبد خرید

    cart.items.all().delete()

    return order
