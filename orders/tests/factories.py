
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model

from catalog.models import (
    Brand,
    Category,
    Product,
    ProductVariant,
)
from cart.models import Cart, CartItem
from orders.models import Address

from datetime import timedelta

from django.utils import timezone

from promotions.models import Coupon


User = get_user_model()


def create_user(
    email=None,
    password="TestPassword123!",
    **kwargs,
):
    email = email or f"user-{uuid4().hex[:10]}@example.com"

    return User.objects.create_user(
        email=email,
        password=password,
        **kwargs,
    )


def create_product(
    *,
    name=None,
    price=Decimal("250000.00"),
    stock=20,
    is_active=True,
    variant_active=True,
):
    suffix = uuid4().hex[:10]

    category = Category.objects.create(
        name=f"Category {suffix}",
        slug=f"category-{suffix}",
    )

    brand = Brand.objects.create(
        name=f"Brand {suffix}",
        slug=f"brand-{suffix}",
    )

    product = Product.objects.create(
        name=name or f"Product {suffix}",
        slug=f"product-{suffix}",
        description="Test product description",
        category=category,
        brand=brand,
        is_active=is_active,
    )

    variant = ProductVariant.objects.create(
        product=product,
        sku=f"SKU-{suffix}",
        name="Default variant",
        price=price,
        stock=stock,
        is_active=variant_active,
    )

    return product, variant


def create_address(user, *, is_default=True):
    suffix = uuid4().hex[:8]

    return Address.objects.create(
        user=user,
        title=f"Address {suffix}",
        recipient_name="Test Recipient",
        phone_number="09123456789",
        province="Tehran",
        city="Tehran",
        postal_code="1234567890",
        address_line="Test address",
        is_default=is_default,
    )


def create_cart(user):
    return Cart.objects.create(user=user)


def add_cart_item(cart, variant, quantity=1):
    return CartItem.objects.create(
        cart=cart,
        variant=variant,
        quantity=quantity,
    )


def create_checkout_context(
    *,
    user=None,
    quantity=2,
    price=Decimal("250000.00"),
    stock=20,
):
    user = user or create_user()

    address = create_address(user)
    cart = create_cart(user)

    product, variant = create_product(
        price=price,
        stock=stock,
    )

    cart_item = add_cart_item(
        cart,
        variant,
        quantity=quantity,
    )

    return {
        "user": user,
        "address": address,
        "cart": cart,
        "product": product,
        "variant": variant,
        "cart_item": cart_item,
    }


def create_coupon(
    *,
    code=None,
    discount_type=Coupon.DiscountType.PERCENTAGE,
    value=10,
    max_discount=None,
    min_order_amount=0,
    usage_limit=None,
    usage_limit_per_user=None,
    is_active=True,
    starts_at=None,
    expires_at=None,
):
    suffix = uuid4().hex[:8]

    now = timezone.now()

    return Coupon.objects.create(
        code=code or f"TEST{suffix}".upper(),
        description="Test coupon",
        discount_type=discount_type,
        value=Decimal(str(value)),
        max_discount=(
            Decimal(str(max_discount))
            if max_discount is not None
            else None
        ),
        min_order_amount=Decimal(str(min_order_amount)),
        usage_limit=usage_limit,
        usage_limit_per_user=usage_limit_per_user,
        starts_at=starts_at or now - timedelta(days=1),
        expires_at=expires_at or now + timedelta(days=1),
        is_active=is_active,
    )