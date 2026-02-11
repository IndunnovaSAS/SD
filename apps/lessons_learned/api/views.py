"""
ViewSets for lessons learned API.
"""

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.lessons_learned.models import (
    Category,
    LessonComment,
    LessonLearned,
)

from .serializers import (
    CategoryListSerializer,
    CategorySerializer,
    LessonAttachmentSerializer,
    LessonCommentSerializer,
    LessonLearnedCreateSerializer,
    LessonLearnedListSerializer,
    LessonLearnedSerializer,
    LessonReviewSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing lesson categories."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Category.objects.all()

        # Filter by active
        is_active = self.request.query_params.get("active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # Filter for root categories only
        root_only = self.request.query_params.get("root_only")
        if root_only and root_only.lower() == "true":
            queryset = queryset.filter(parent__isnull=True)

        return queryset.order_by("order", "name")

    def get_serializer_class(self):
        if self.action == "list":
            return CategoryListSerializer
        return CategorySerializer


class LessonLearnedViewSet(viewsets.ModelViewSet):
    """ViewSet for managing lessons learned."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = LessonLearned.objects.select_related(
            "category", "created_by", "reviewed_by"
        ).prefetch_related("attachments")

        # Filter by status
        lesson_status = self.request.query_params.get("status")
        if lesson_status:
            queryset = queryset.filter(status=lesson_status)

        # Filter by category
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Filter by type
        lesson_type = self.request.query_params.get("type")
        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)

        # Filter by severity
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        # Filter by profile
        profile = self.request.query_params.get("profile")
        if profile:
            db_engine = settings.DATABASES["default"]["ENGINE"]
            if "postgresql" in db_engine:
                queryset = queryset.filter(target_profiles__contains=[profile])
            else:
                queryset = queryset.filter(target_profiles__icontains=profile)

        # Filter by featured
        featured = self.request.query_params.get("featured")
        if featured and featured.lower() == "true":
            queryset = queryset.filter(is_featured=True)

        # Search
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(lesson__icontains=search)
                | Q(recommendations__icontains=search)
            )

        # Non-staff users see only approved lessons or their own
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(status=LessonLearned.Status.APPROVED) | Q(created_by=self.request.user)
            )

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "list":
            return LessonLearnedListSerializer
        if self.action == "create":
            return LessonLearnedCreateSerializer
        return LessonLearnedSerializer

    def retrieve(self, request, *args, **kwargs):
        """Increment view count on retrieve."""
        instance = self.get_object()

        # Increment view count (only if not the author)
        if instance.created_by != request.user:
            instance.view_count += 1
            instance.save(update_fields=["view_count"])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit_for_review(self, request, pk=None):
        """Submit a lesson for review."""
        lesson = self.get_object()

        if lesson.created_by != request.user:
            return Response(
                {"error": "Solo el autor puede enviar a revisión"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if lesson.status != LessonLearned.Status.DRAFT:
            return Response(
                {"error": "Solo se pueden enviar borradores a revisión"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lesson.status = LessonLearned.Status.PENDING_REVIEW
        lesson.save()

        return Response(LessonLearnedSerializer(lesson).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """Review a lesson (approve or reject)."""
        if not request.user.is_staff:
            return Response(
                {"error": "Solo personal autorizado puede revisar"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lesson = self.get_object()

        if lesson.status != LessonLearned.Status.PENDING_REVIEW:
            return Response(
                {"error": "La lección no está pendiente de revisión"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LessonReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        review_notes = serializer.validated_data.get("review_notes", "")

        if action == "approve":
            lesson.status = LessonLearned.Status.APPROVED
        else:
            lesson.status = LessonLearned.Status.REJECTED

        lesson.reviewed_by = request.user
        lesson.reviewed_at = timezone.now()
        lesson.review_notes = review_notes
        lesson.save()

        return Response(LessonLearnedSerializer(lesson).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive a lesson."""
        if not request.user.is_staff:
            return Response(
                {"error": "Solo personal autorizado puede archivar"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lesson = self.get_object()
        lesson.status = LessonLearned.Status.ARCHIVED
        lesson.save()

        return Response(LessonLearnedSerializer(lesson).data)

    @action(detail=True, methods=["post"])
    def toggle_featured(self, request, pk=None):
        """Toggle featured status."""
        if not request.user.is_staff:
            return Response(
                {"error": "Solo personal autorizado puede destacar"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lesson = self.get_object()
        lesson.is_featured = not lesson.is_featured
        lesson.save()

        return Response({"is_featured": lesson.is_featured})

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        """Get or add comments."""
        lesson = self.get_object()

        if request.method == "GET":
            comments = lesson.comments.filter(
                is_approved=True,
                parent__isnull=True,
            ).order_by("created_at")
            serializer = LessonCommentSerializer(comments, many=True)
            return Response(serializer.data)

        # POST - add comment
        serializer = LessonCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson_learned=lesson, user=request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_attachment(self, request, pk=None):
        """Add an attachment to a lesson."""
        lesson = self.get_object()

        if lesson.created_by != request.user and not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LessonAttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(lesson_learned=lesson)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def my_lessons(self, request):
        """Get current user's lessons."""
        lessons = (
            LessonLearned.objects.filter(created_by=request.user)
            .select_related("category")
            .order_by("-created_at")
        )

        serializer = LessonLearnedListSerializer(lessons, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_review(self, request):
        """Get lessons pending review (staff only)."""
        if not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lessons = (
            LessonLearned.objects.filter(status=LessonLearned.Status.PENDING_REVIEW)
            .select_related("category", "created_by")
            .order_by("created_at")
        )

        serializer = LessonLearnedListSerializer(lessons, many=True)
        return Response(serializer.data)


class LessonCommentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing lesson comments."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LessonCommentSerializer

    def get_queryset(self):
        return LessonComment.objects.filter(is_approved=True).order_by("created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a comment (staff only)."""
        if not request.user.is_staff:
            return Response(
                {"error": "No autorizado"},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment = self.get_object()
        comment.is_approved = True
        comment.save()

        return Response(LessonCommentSerializer(comment).data)
