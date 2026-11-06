
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken,
)


def revoke_user_refresh_tokens(user):
    outstanding_tokens = OutstandingToken.objects.filter(
        user=user
    )

    for token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(
            token=token
        )
