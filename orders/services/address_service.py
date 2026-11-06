
from django.db import transaction
from django.db.models.deletion import ProtectedError

from rest_framework.exceptions import ValidationError

from orders.models import Address


def _lock_user(user):
    """
    Serialize address mutations for the same user.
    """
    user_model = type(user)

    return user_model.objects.select_for_update().get(
        pk=user.pk
    )


def _get_locked_address(*, address_id, user):
    """
    Fetch an address belonging to the user and lock it.
    """
    try:
        return Address.objects.select_for_update().get(
            pk=address_id,
            user=user,
        )
    except Address.DoesNotExist:
        raise ValidationError({
            "address": "Address not found."
        })


@transaction.atomic
def set_default_address(*, address, user):
    """
    Set one address as the user's default address.
    """

    _lock_user(user)

    locked_address = _get_locked_address(
        address_id=address.pk,
        user=user,
    )

    if not locked_address.is_default:
        Address.objects.filter(
            user=user,
            is_default=True,
        ).exclude(
            pk=locked_address.pk
        ).update(
            is_default=False
        )

        locked_address.is_default = True
        locked_address.save(
            update_fields=["is_default", "updated_at"]
        )

    return locked_address


@transaction.atomic
def create_address(*, user, validated_data):
    """
    Create an address for the user.
    The first address automatically becomes the default address.
    """

    _lock_user(user)

    data = validated_data.copy()
    make_default = data.pop("is_default", False)

    has_addresses = Address.objects.filter(
        user=user
    ).exists()

    if not has_addresses:
        make_default = True

    if make_default:
        Address.objects.filter(
            user=user,
            is_default=True,
        ).update(
            is_default=False
        )

    return Address.objects.create(
        user=user,
        is_default=make_default,
        **data,
    )


@transaction.atomic
def update_address(*, address, validated_data):
    """
    Update an address and optionally make it the default.
    """

    user = address.user

    _lock_user(user)

    locked_address = _get_locked_address(
        address_id=address.pk,
        user=user,
    )

    data = validated_data.copy()

    make_default = data.pop(
        "is_default",
        locked_address.is_default,
    )

    if make_default:
        Address.objects.filter(
            user=user,
            is_default=True,
        ).exclude(
            pk=locked_address.pk
        ).update(
            is_default=False
        )

    for field, value in data.items():
        setattr(locked_address, field, value)

    locked_address.is_default = make_default

    locked_address.save()

    return locked_address


@transaction.atomic
def delete_address(*, address):
    """
    Delete an address.

    If the deleted address was the default address,
    the newest remaining address becomes the default.

    Addresses referenced by existing orders cannot be deleted.
    """

    user = address.user

    _lock_user(user)

    locked_address = _get_locked_address(
        address_id=address.pk,
        user=user,
    )

    was_default = locked_address.is_default

    try:
        locked_address.delete()
    except ProtectedError:
        raise ValidationError({
            "address": (
                "This address is used by an existing order "
                "and cannot be deleted."
            )
        })

    if was_default:
        next_address = (
            Address.objects.select_for_update()
            .filter(user=user)
            .order_by("-created_at", "-pk")
            .first()
        )

        if next_address:
            next_address.is_default = True
            next_address.save(
                update_fields=["is_default", "updated_at"]
            )

    return True
