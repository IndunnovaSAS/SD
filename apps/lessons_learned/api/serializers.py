"""
Serializers for lessons learned API.
"""

from rest_framework import serializers

from apps.lessons_learned.models import (
    Category,
    LessonAttachment,
    LessonComment,
    LessonLearned,
)


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "parent",
            "icon",
            "order",
            "is_active",
            "children",
        ]
        read_only_fields = ["id"]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True).order_by("order", "name")
        return CategorySerializer(children, many=True).data


class CategoryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for category lists."""

    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "parent", "parent_name", "icon", "is_active"]


class LessonAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for LessonAttachment model."""

    class Meta:
        model = LessonAttachment
        fields = [
            "id",
            "file",
            "file_type",
            "original_name",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class LessonCommentSerializer(serializers.ModelSerializer):
    """Serializer for LessonComment model."""

    user_name = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = LessonComment
        fields = [
            "id",
            "user",
            "user_name",
            "content",
            "parent",
            "is_approved",
            "replies",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "is_approved", "created_at", "updated_at"]

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_replies(self, obj):
        if obj.parent is None:  # Only get replies for top-level comments
            replies = obj.replies.filter(is_approved=True).order_by("created_at")
            return LessonCommentSerializer(replies, many=True).data
        return []


class LessonLearnedSerializer(serializers.ModelSerializer):
    """Serializer for LessonLearned model."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    attachments = LessonAttachmentSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = LessonLearned
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "lesson_type",
            "severity",
            "status",
            "situation",
            "root_cause",
            "lesson",
            "recommendations",
            "location",
            "date_occurred",
            "tags",
            "target_profiles",
            "created_by",
            "created_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "review_notes",
            "view_count",
            "is_featured",
            "attachments",
            "comment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "reviewed_by",
            "reviewed_at",
            "review_notes",
            "view_count",
            "created_at",
            "updated_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None

    def get_comment_count(self, obj):
        return obj.comments.filter(is_approved=True).count()


class LessonLearnedListSerializer(serializers.ModelSerializer):
    """Simplified serializer for lesson lists."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LessonLearned
        fields = [
            "id",
            "title",
            "category",
            "category_name",
            "lesson_type",
            "severity",
            "status",
            "location",
            "date_occurred",
            "tags",
            "created_by_name",
            "view_count",
            "is_featured",
            "created_at",
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class LessonLearnedCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating lessons learned."""

    class Meta:
        model = LessonLearned
        fields = [
            "title",
            "description",
            "category",
            "lesson_type",
            "severity",
            "situation",
            "root_cause",
            "lesson",
            "recommendations",
            "location",
            "date_occurred",
            "tags",
            "target_profiles",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class LessonReviewSerializer(serializers.Serializer):
    """Serializer for reviewing lessons learned."""

    action = serializers.ChoiceField(choices=["approve", "reject"])
    review_notes = serializers.CharField(required=False, allow_blank=True)
