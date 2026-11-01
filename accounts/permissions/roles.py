from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Only users with admin role can access.
    """

    message = "You must be an admin to access this resource."

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.is_active
            and user.role == "admin"
        )


class IsSupportOrAdmin(BasePermission):
    """
    Support and admin users can access.
    """

    message = "You do not have permission to access this resource."

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and user.is_active
            and user.role in ["support", "admin"]
        )