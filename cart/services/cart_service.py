import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404

from catalog.models import ProductVariant
from cart.models import Cart, CartItem


def _lock_cart(cart):
    """
    Lock the Cart row so all mutations for this cart are serialized.
    """
    return Cart.objects.select_for_update().get(pk=cart.pk)


@transaction.atomic
def get_or_create_cart(*, user=None, guest_token=None):
    if user is not None and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=user,
            defaults={"guest_token": None},
        )
        return cart

    if guest_token is not None:
        cart = Cart.objects.filter(
            guest_token=guest_token,
            user__isnull=True,
        ).first()

        if cart is not None:
            return cart

    return Cart.objects.create(
        guest_token=uuid.uuid4(),
    )


@transaction.atomic
def add_item(*, cart, variant_id, quantity=1):
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    # Lock order: Cart -> ProductVariant -> CartItem
    locked_cart = _lock_cart(cart)

    variant = get_object_or_404(
        ProductVariant.objects.select_for_update(),
        id=variant_id,
        is_active=True,
        product__is_active=True,
    )

    item = (
        CartItem.objects.select_for_update()
        .filter(cart=locked_cart, variant=variant)
        .first()
    )

    new_quantity = quantity + (item.quantity if item else 0)

    if variant.stock < new_quantity:
        raise ValueError(
            f"Only {variant.stock} items are available."
        )

    if item is not None:
        item.quantity = new_quantity
        item.save(update_fields=["quantity", "updated_at"])
    else:
        item = CartItem.objects.create(
            cart=locked_cart,
            variant=variant,
            quantity=quantity,
        )

    return item


@transaction.atomic
def update_item_quantity(*, cart, item_id, quantity):
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")

    # Lock order: Cart -> ProductVariant -> CartItem
    locked_cart = _lock_cart(cart)

    # First read the variant ID. Cart lock prevents concurrent mutations
    # through the Cart service while we acquire the variant lock.
    item_reference = get_object_or_404(
        CartItem.objects.filter(cart=locked_cart),
        id=item_id,
    )

    variant = get_object_or_404(
        ProductVariant.objects.select_for_update(),
        id=item_reference.variant_id,
        is_active=True,
        product__is_active=True,
    )

    item = get_object_or_404(
        CartItem.objects.select_for_update(),
        id=item_id,
        cart=locked_cart,
    )

    if variant.stock < quantity:
        raise ValueError(
            f"Only {variant.stock} items are available."
        )

    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])

    return item


@transaction.atomic
def remove_item(*, cart, item_id):
    locked_cart = _lock_cart(cart)

    item = get_object_or_404(
        CartItem.objects.select_for_update(),
        id=item_id,
        cart=locked_cart,
    )

    item.delete()


@transaction.atomic
def clear_cart(*, cart):
    locked_cart = _lock_cart(cart)
    locked_cart.items.all().delete()


@transaction.atomic
def merge_guest_cart(*, user, guest_token):
    # Serialize guest-cart merges for the same account.
    type(user).objects.select_for_update().get(pk=user.pk)

    guest_cart = Cart.objects.filter(
        guest_token=guest_token,
        user__isnull=True,
    ).first()

    if guest_cart is None:
        user_cart, _ = Cart.objects.get_or_create(user=user)
        return user_cart

    user_cart = Cart.objects.filter(user=user).first()

    # Lock both carts in a deterministic order to reduce deadlock risk.
    cart_ids = [guest_cart.pk]

    if user_cart is not None:
        cart_ids.append(user_cart.pk)

    locked_carts = {
        cart.pk: cart
        for cart in (
            Cart.objects.select_for_update()
            .filter(pk__in=cart_ids)
            .order_by("pk")
        )
    }

    guest_cart = locked_carts.get(guest_cart.pk)

    if guest_cart is None:
        user_cart, _ = Cart.objects.get_or_create(user=user)
        return user_cart

    if user_cart is None:
        guest_cart.user = user
        guest_cart.guest_token = None
        guest_cart.save(
            update_fields=["user", "guest_token", "updated_at"]
        )
        return guest_cart

    user_cart = locked_carts[user_cart.pk]

    guest_items = list(
        CartItem.objects.select_for_update()
        .filter(cart=guest_cart)
        .order_by("variant_id")
    )

    variant_ids = sorted({
        item.variant_id
        for item in guest_items
    })

    # Lock all variants in a deterministic order.
    variants = {
        variant.pk: variant
        for variant in (
            ProductVariant.objects.select_for_update()
            .filter(pk__in=variant_ids)
            .order_by("pk")
        )
    }

    for guest_item in guest_items:
        variant = variants.get(guest_item.variant_id)

        if variant is None:
            continue

        if not variant.is_active or not variant.product.is_active:
            continue

        user_item = (
            CartItem.objects.select_for_update()
            .filter(
                cart=user_cart,
                variant=variant,
            )
            .first()
        )

        existing_quantity = (
            user_item.quantity if user_item else 0
        )

        available_quantity = max(variant.stock, 0)

        final_quantity = min(
            existing_quantity + guest_item.quantity,
            available_quantity,
        )

        # Preserve the existing user-cart quantity if stock is insufficient.
        if final_quantity <= existing_quantity:
            continue

        if user_item is not None:
            user_item.quantity = final_quantity
            user_item.save(
                update_fields=["quantity", "updated_at"]
            )
        else:
            CartItem.objects.create(
                cart=user_cart,
                variant=variant,
                quantity=final_quantity,
            )

    guest_cart.delete()

    return user_cart