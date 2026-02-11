"""
API views for occupational_profiles app.
"""

from django.shortcuts import get_object_or_404

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import User
from apps.occupational_profiles.models import OccupationalProfile, UserOccupationalProfile

from .serializers import (
    OccupationalProfileListSerializer,
    OccupationalProfileSerializer,
    UserOccupationalProfileSerializer,
)


class OccupationalProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for OccupationalProfile CRUD operations."""

    queryset = OccupationalProfile.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return OccupationalProfileListSerializer
        return OccupationalProfileSerializer

    def get_queryset(self):
        queryset = OccupationalProfile.objects.prefetch_related("learning_paths")

        # Filter by country
        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(country=country)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter by operational type
        is_operational = self.request.query_params.get("is_operational")
        if is_operational is not None:
            queryset = queryset.filter(is_operational=is_operational.lower() == "true")

        return queryset

    @action(detail=True, methods=["get"])
    def users(self, request, pk=None):
        """Get all users with this profile."""
        profile = self.get_object()
        assignments = UserOccupationalProfile.objects.filter(
            profile=profile,
            is_active=True,
        ).select_related("user", "assigned_by")
        serializer = UserOccupationalProfileSerializer(assignments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def assign_user(self, request, pk=None):
        """Assign this profile to a user."""
        profile = self.get_object()
        user_id = request.data.get("user_id")
        notes = request.data.get("notes", "")

        user = get_object_or_404(User, pk=user_id)

        assignment, created = UserOccupationalProfile.objects.update_or_create(
            user=user,
            profile=profile,
            defaults={
                "assigned_by": request.user,
                "is_active": True,
                "notes": notes,
            },
        )

        serializer = UserOccupationalProfileSerializer(assignment)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class UserOccupationalProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for UserOccupationalProfile operations."""

    queryset = UserOccupationalProfile.objects.all()
    serializer_class = UserOccupationalProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = UserOccupationalProfile.objects.select_related("user", "profile", "assigned_by")

        # Filter by user
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by profile
        profile_id = self.request.query_params.get("profile")
        if profile_id:
            queryset = queryset.filter(profile_id=profile_id)

        # Filter by active status
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=False, methods=["post"])
    def bulk_assign(self, request):
        """Assign a profile to multiple users."""
        profile_id = request.data.get("profile_id")
        user_ids = request.data.get("user_ids", [])
        notes = request.data.get("notes", "")

        profile = get_object_or_404(OccupationalProfile, pk=profile_id)
        created_count = 0

        for user_id in user_ids:
            try:
                user = User.objects.get(pk=user_id)
                _, created = UserOccupationalProfile.objects.update_or_create(
                    user=user,
                    profile=profile,
                    defaults={
                        "assigned_by": request.user,
                        "is_active": True,
                        "notes": notes,
                    },
                )
                if created:
                    created_count += 1
            except User.DoesNotExist:
                continue

        return Response(
            {
                "profile": profile.name,
                "assigned": created_count,
                "skipped": len(user_ids) - created_count,
            },
            status=status.HTTP_201_CREATED,
        )
