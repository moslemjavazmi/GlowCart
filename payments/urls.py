from django.urls import path

from payments.views import (
    InitializePaymentView,
    PaymentDetailView,
    ZarinpalCallbackView,
)


urlpatterns = [
    path(
        "initialize/",
        InitializePaymentView.as_view(),
        name="initialize-payment",
    ),

    path(
        "callback/zarinpal/",
        ZarinpalCallbackView.as_view(),
        name="zarinpal-callback",
    ),

    path(
        "<uuid:payment_id>/",
        PaymentDetailView.as_view(),
        name="payment-detail",
    ),
]