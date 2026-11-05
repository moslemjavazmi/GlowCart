
from django.urls import path

from promotions.views import (
    ApplyCouponView,
    RemoveCouponView,
)

urlpatterns = [
    path(
        "orders/<uuid:order_id>/coupon/",
        ApplyCouponView.as_view(),
        name="apply-coupon",
    ),
    path(
        "orders/<uuid:order_id>/coupon/remove/",
        RemoveCouponView.as_view(),
        name="remove-coupon",
    ),
]
