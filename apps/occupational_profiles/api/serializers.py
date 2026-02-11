"""
Serializers for occupational_profiles API.
"""

from rest_framework import serializers

from apps.occupational_profiles.models import OccupationalProfile, UserOccupationalProfile


class OccupationalProfileSerializer(serializers.ModelSerializer):
    """Serializer for OccupationalProfile model."""

    learning_path_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = OccupationalProfile
        fields = [
            "id",
            "code",
            "name",
            "description",
            "country",
            "is_operational",
            "is_active",
            "order",
            "learning_paths",
            "learning_path_count",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_learning_path_count(self, obj):
        return obj.learning_paths.count()

    def get_user_count(self, obj):
        return obj.user_assignments.filter(is_active=True).count()


class OccupationalProfileListSerializer(serializers.ModelSerializer):
    """Simplified serializer for profile lists."""

    class Meta:
        model = OccupationalProfile
        fields = ["id", "code", "name", "country", "is_operational", "is_active"]


class UserOccupationalProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserOccupationalProfile model."""

    user_name = serializers.SerializerMethodField()
    profile_name = serializers.CharField(source="profile.name", read_only=True)
    assigned_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UserOccupationalProfile
        fields = [
            "id",
            "user",
            "user_name",
            "profile",
            "profile_name",
            "assigned_by",
            "assigned_by_name",
            "assigned_at",
            "is_active",
            "notes",
        ]
        read_only_fields = ["id", "assigned_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_assigned_by_name(self, obj):
        return obj.assigned_by.get_full_name() if obj.assigned_by else None


class AssignProfileSerializer(serializers.Serializer):
    """Serializer for assigning a profile to a user."""

    user_id = serializers.IntegerField()
    profile_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, default="")
