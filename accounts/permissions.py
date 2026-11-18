from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """Object-level: allow only the owner of the object."""

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.id
