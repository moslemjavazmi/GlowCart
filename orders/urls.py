
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from orders.views.address_views import AddressViewSet

from orders.views.order_views import (
    CreateOrderView,
    OrderListView,
    OrderDetailView,
)

from orders.views.order_views import (
    CreateOrderView,
    OrderListView,
    OrderDetailView,
    CancelOrderView,
)
router = DefaultRouter()

router.register(
    "addresses",
    AddressViewSet,
    basename="address",
)


urlpatterns = [
    path(
        "create/",
        CreateOrderView.as_view(),
        name="create-order",
    ),

    path(
        "",
        OrderListView.as_view(),
        name="order-list",
    ),

    path(
        "<uuid:order_id>/cancel/",
        CancelOrderView.as_view(),
        name="cancel-order",
    ),

    path(
        "<uuid:id>/",
        OrderDetailView.as_view(),
        name="order-detail",
    ),

    path("", include(router.urls)),
]
