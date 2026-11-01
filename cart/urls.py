from django.urls import path

from cart.views import (
    CartView,
    AddCartItemView,
    UpdateCartItemView,
    RemoveCartItemView,
    ClearCartView,
    MergeGuestCartView,
)

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", AddCartItemView.as_view(), name="cart-add-item"),
    path(
        "items/<uuid:item_id>/",
        UpdateCartItemView.as_view(),
        name="cart-update-item",
    ),
    path(
        "items/<uuid:item_id>/remove/",
        RemoveCartItemView.as_view(),
        name="cart-remove-item",
    ),
    path("clear/", ClearCartView.as_view(), name="cart-clear"),
    path(
        "merge/",
        MergeGuestCartView.as_view(),
        name="cart-merge",
    ),
]