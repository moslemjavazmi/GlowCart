from payments.models import Payment


def get_payment_gateway(provider: str):

    if provider == Payment.Provider.ZARINPAL:
        from payments.gateways.zarinpal import ZarinpalGateway
        return ZarinpalGateway()

    if provider == Payment.Provider.IDPAY:
        raise ValueError("IDPay gateway is not implemented yet.")

    raise ValueError("Unsupported payment provider.")