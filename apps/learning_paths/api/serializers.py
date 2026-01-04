"""
Serializers for learning paths API.
"""

from rest_framework import serializers

from apps.courses.api.serializers import CourseListSerializer
from apps.courses.models import Enrollment
from apps.learning_paths.models import LearningPath, PathAssignment, PathCourse


class PathCourseSerializer(serializers.ModelSerializer):
    """Serializer for PathCourse model."""

    course_detail = CourseListSerializer(source="course", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_duration = serializers.IntegerField(source="course.duration", read_only=True)
    is_unlocked = serializers.SerializerMethodField()
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = PathCourse
        fields = [
            "id",
            "course",
            "course_detail",
            "course_title",
            "course_duration",
            "order",
            "is_required",
            "unlock_after",
            "is_unlocked",
            "is_completed",
        ]
        read_only_fields = ["id"]

    def get_is_unlocked(self, obj):
        """Check if course is unlocked for current user."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        # If no unlock prerequisite, it's unlocked
        if not obj.unlock_after:
            return True

        # Check if prerequisite course is completed
        prereq_course = obj.unlock_after.course
        return Enrollment.objects.filter(
            user=request.user,
            course=prereq_course,
            status=Enrollment.Status.COMPLETED,
        ).exists()

    def get_is_completed(self, obj):
        """Check if course is completed by current user."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return Enrollment.objects.filter(
            user=request.user,
            course=obj.course,
            status=Enrollment.Status.COMPLETED,
        ).exists()


class PathCourseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PathCourse."""

    class Meta:
        model = PathCourse
        fields = ["course", "order", "is_required", "unlock_after"]


class LearningPathSerializer(serializers.ModelSerializer):
    """Serializer for LearningPath model."""

    path_courses = PathCourseSerializer(many=True, read_only=True)
    total_courses = serializers.ReadOnlyField()
    total_duration = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    user_assignment = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = [
            "id",
            "name",
            "description",
            "target_profiles",
            "status",
            "is_mandatory",
            "estimated_duration",
            "thumbnail",
            "created_by",
            "created_by_name",
            "total_courses",
            "total_duration",
            "path_courses",
            "user_assignment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_user_assignment(self, obj):
        """Get current user's assignment for this path."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        assignment = PathAssignment.objects.filter(
            user=request.user,
            learning_path=obj,
        ).first()

        if assignment:
            return PathAssignmentSerializer(assignment).data
        return None


class LearningPathListSerializer(serializers.ModelSerializer):
    """Simplified serializer for learning path lists."""

    total_courses = serializers.ReadOnlyField()
    total_duration = serializers.ReadOnlyField()
    assignment_count = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = [
            "id",
            "name",
            "description",
            "target_profiles",
            "status",
            "is_mandatory",
            "estimated_duration",
            "thumbnail",
            "total_courses",
            "total_duration",
            "assignment_count",
            "user_progress",
        ]

    def get_assignment_count(self, obj):
        return obj.assignments.count()

    def get_user_progress(self, obj):
        """Get current user's progress on this path."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        assignment = PathAssignment.objects.filter(
            user=request.user,
            learning_path=obj,
        ).first()

        if assignment:
            return float(assignment.progress)
        return None


class LearningPathCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating learning paths."""

    class Meta:
        model = LearningPath
        fields = [
            "name",
            "description",
            "target_profiles",
            "is_mandatory",
            "estimated_duration",
            "thumbnail",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class PathAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for PathAssignment model."""

    user_name = serializers.SerializerMethodField()
    learning_path_name = serializers.CharField(source="learning_path.name", read_only=True)
    learning_path_detail = LearningPathListSerializer(source="learning_path", read_only=True)

    class Meta:
        model = PathAssignment
        fields = [
            "id",
            "user",
            "user_name",
            "learning_path",
            "learning_path_name",
            "learning_path_detail",
            "status",
            "progress",
            "due_date",
            "started_at",
            "completed_at",
            "assigned_by",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "progress",
            "started_at",
            "completed_at",
            "assigned_by",
            "created_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class PathAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating path assignments."""

    class Meta:
        model = PathAssignment
        fields = ["user", "learning_path", "due_date"]

    def create(self, validated_data):
        validated_data["assigned_by"] = self.context["request"].user
        return super().create(validated_data)


class BulkPathAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk path assignment."""

    user_ids = serializers.ListField(child=serializers.IntegerField())
    learning_path_id = serializers.IntegerField()
    due_date = serializers.DateField(required=False, allow_null=True)
