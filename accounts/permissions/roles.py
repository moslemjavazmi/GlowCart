
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Allows active admin-role users and active Django superusers.
    """

    message = "You must be an admin to access this resource."

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.is_active
            and (
                user.is_superuser
                or user.role == "admin"
            )
        )


class IsSupportOrAdmin(BasePermission):
    """
    Allows active support users, admin users, and superusers.
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.is_active
            and (
                user.is_superuser
                or user.role in ["support", "admin"]
            )
        )
