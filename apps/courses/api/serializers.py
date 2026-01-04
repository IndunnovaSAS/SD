"""
Serializers for courses API.
"""

from rest_framework import serializers

from apps.courses.models import (
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    MediaAsset,
    Module,
)


class LessonSerializer(serializers.ModelSerializer):
    """Serializer for Lesson model."""

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "description",
            "lesson_type",
            "content",
            "content_file",
            "video_url",
            "duration",
            "order",
            "is_mandatory",
            "is_offline_available",
            "metadata",
        ]
        read_only_fields = ["id"]


class LessonListSerializer(serializers.ModelSerializer):
    """Simplified serializer for lesson lists."""

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "lesson_type",
            "duration",
            "order",
            "is_mandatory",
        ]


class ModuleSerializer(serializers.ModelSerializer):
    """Serializer for Module model."""

    lessons = LessonSerializer(many=True, read_only=True)
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = [
            "id",
            "title",
            "description",
            "order",
            "lessons",
            "lesson_count",
        ]
        read_only_fields = ["id"]

    def get_lesson_count(self, obj):
        return obj.lessons.count()


class ModuleListSerializer(serializers.ModelSerializer):
    """Simplified serializer for module lists."""

    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ["id", "title", "order", "lesson_count"]

    def get_lesson_count(self, obj):
        return obj.lessons.count()


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model."""

    modules = ModuleSerializer(many=True, read_only=True)
    total_duration = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "description",
            "objectives",
            "duration",
            "course_type",
            "risk_level",
            "thumbnail",
            "status",
            "version",
            "target_profiles",
            "prerequisites",
            "validity_months",
            "created_by",
            "created_by_name",
            "published_at",
            "total_duration",
            "modules",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "published_at", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class CourseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for course lists."""

    module_count = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "course_type",
            "risk_level",
            "status",
            "duration",
            "thumbnail",
            "module_count",
            "enrollment_count",
        ]

    def get_module_count(self, obj):
        return obj.modules.count()

    def get_enrollment_count(self, obj):
        return obj.enrollments.count()


class CourseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating courses."""

    class Meta:
        model = Course
        fields = [
            "code",
            "title",
            "description",
            "objectives",
            "duration",
            "course_type",
            "risk_level",
            "thumbnail",
            "target_profiles",
            "prerequisites",
            "validity_months",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class MediaAssetSerializer(serializers.ModelSerializer):
    """Serializer for MediaAsset model."""

    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "filename",
            "original_name",
            "file",
            "file_type",
            "mime_type",
            "size",
            "thumbnail",
            "compressed_file",
            "status",
            "processing_error",
            "duration",
            "metadata",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "filename",
            "mime_type",
            "size",
            "status",
            "processing_error",
            "uploaded_by",
            "created_at",
        ]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for Enrollment model."""

    user_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "user",
            "user_name",
            "course",
            "course_title",
            "status",
            "progress",
            "started_at",
            "completed_at",
            "due_date",
            "assigned_by",
            "created_at",
        ]
        read_only_fields = ["id", "progress", "started_at", "completed_at", "created_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_course_title(self, obj):
        return obj.course.title


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating enrollments."""

    class Meta:
        model = Enrollment
        fields = ["user", "course", "due_date"]

    def create(self, validated_data):
        validated_data["assigned_by"] = self.context["request"].user
        return super().create(validated_data)


class BulkEnrollmentSerializer(serializers.Serializer):
    """Serializer for bulk enrollment."""

    user_ids = serializers.ListField(child=serializers.IntegerField())
    course_id = serializers.IntegerField()
    due_date = serializers.DateField(required=False, allow_null=True)


class LessonProgressSerializer(serializers.ModelSerializer):
    """Serializer for LessonProgress model."""

    lesson_title = serializers.SerializerMethodField()

    class Meta:
        model = LessonProgress
        fields = [
            "id",
            "enrollment",
            "lesson",
            "lesson_title",
            "is_completed",
            "progress_percent",
            "time_spent",
            "last_position",
            "completed_at",
        ]
        read_only_fields = ["id", "enrollment", "completed_at"]

    def get_lesson_title(self, obj):
        return obj.lesson.title


class LessonProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating lesson progress."""

    class Meta:
        model = LessonProgress
        fields = ["progress_percent", "time_spent", "last_position", "is_completed"]
