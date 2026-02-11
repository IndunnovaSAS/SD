"""
Custom authentication backends for SD LMS.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrDocumentBackend(ModelBackend):
    """
    Custom authentication backend that allows users to authenticate
    with either email or document number.

    - Operational staff (LINIERO, TECNICO, OPERADOR): Use document number
    - Professional/Admin staff: Use email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # Try to find user by email or document number
            user = User.objects.get(Q(email__iexact=username) | Q(document_number=username))
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # This should not happen, but handle it gracefully
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
