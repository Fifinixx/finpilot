from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allows access only to users with the ADMIN application role."""

    message = "Administrator role required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)
