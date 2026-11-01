
from django.db import transaction

from orders.models import Address


@transaction.atomic
def set_default_address(*, address, user):
    """
    فقط یک آدرس برای هر کاربر می‌تواند پیش‌فرض باشد.
    """

    Address.objects.filter(
        user=user,
        is_default=True,
    ).exclude(
        pk=address.pk
    ).update(
        is_default=False
    )

    if not address.is_default:
        address.is_default = True
        address.save(update_fields=["is_default", "updated_at"])

    return address


@transaction.atomic
def create_address(*, user, validated_data):
    """
    ایجاد آدرس جدید برای کاربر.
    """

    make_default = validated_data.pop("is_default", False)

    if make_default:
        Address.objects.filter(
            user=user,
            is_default=True,
        ).update(is_default=False)

    elif not Address.objects.filter(user=user).exists():
        # اولین آدرس کاربر را پیش‌فرض می‌کنیم.
        make_default = True

    return Address.objects.create(
        user=user,
        is_default=make_default,
        **validated_data,
    )


@transaction.atomic
def update_address(*, address, validated_data):
    """
    ویرایش آدرس متعلق به کاربر.
    """

    make_default = validated_data.pop("is_default", address.is_default)

    if make_default:
        Address.objects.filter(
            user=address.user,
            is_default=True,
        ).exclude(
            pk=address.pk
        ).update(
            is_default=False
        )

    for field, value in validated_data.items():
        setattr(address, field, value)

    address.is_default = make_default
    address.save()

    return address


@transaction.atomic
def delete_address(*, address):
    """
    حذف آدرس.

    اگر آدرس پیش‌فرض حذف شد، آدرس دیگری را پیش‌فرض می‌کنیم.
    """

    user = address.user
    was_default = address.is_default

    address.delete()

    if was_default:
        next_address = Address.objects.filter(
            user=user
        ).order_by("-created_at").first()

        if next_address:
            next_address.is_default = True
            next_address.save(update_fields=["is_default", "updated_at"])
