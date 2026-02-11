"""
Business logic services for lessons learned.
"""

import logging

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.lessons_learned.models import (
    Category,
    LessonAttachment,
    LessonComment,
    LessonLearned,
)

logger = logging.getLogger(__name__)


class LessonLearnedService:
    """Service for lessons learned operations."""

    @staticmethod
    @transaction.atomic
    def create_lesson(
        title: str,
        description: str,
        category: Category,
        situation: str,
        lesson: str,
        recommendations: str,
        created_by,
        lesson_type: str = LessonLearned.Type.OBSERVATION,
        severity: str = LessonLearned.Severity.MEDIUM,
        root_cause: str = "",
        location: str = "",
        date_occurred=None,
        tags: list = None,
        target_profiles: list = None,
        submit_for_review: bool = False,
    ) -> LessonLearned:
        """
        Create a new lesson learned.
        """
        lesson_learned = LessonLearned.objects.create(
            title=title,
            description=description,
            category=category,
            lesson_type=lesson_type,
            severity=severity,
            situation=situation,
            root_cause=root_cause,
            lesson=lesson,
            recommendations=recommendations,
            location=location,
            date_occurred=date_occurred,
            tags=tags or [],
            target_profiles=target_profiles or [],
            created_by=created_by,
            status=LessonLearned.Status.DRAFT,
        )

        if submit_for_review:
            LessonLearnedService.submit_for_review(lesson_learned)

        logger.info(f"Lesson learned created: {lesson_learned.id}")
        return lesson_learned

    @staticmethod
    def submit_for_review(lesson_learned: LessonLearned) -> LessonLearned:
        """
        Submit a lesson learned for review.
        """
        if lesson_learned.status != LessonLearned.Status.DRAFT:
            raise ValueError("Solo se pueden enviar a revisión lecciones en borrador")

        lesson_learned.status = LessonLearned.Status.PENDING_REVIEW
        lesson_learned.save()

        logger.info(f"Lesson submitted for review: {lesson_learned.id}")
        return lesson_learned

    @staticmethod
    @transaction.atomic
    def approve_lesson(
        lesson_learned: LessonLearned,
        reviewer,
        notes: str = "",
    ) -> LessonLearned:
        """
        Approve a lesson learned.
        """
        if lesson_learned.status != LessonLearned.Status.PENDING_REVIEW:
            raise ValueError("Solo se pueden aprobar lecciones pendientes de revisión")

        lesson_learned.status = LessonLearned.Status.APPROVED
        lesson_learned.reviewed_by = reviewer
        lesson_learned.reviewed_at = timezone.now()
        lesson_learned.review_notes = notes
        lesson_learned.save()

        logger.info(f"Lesson approved: {lesson_learned.id} by {reviewer.id}")
        return lesson_learned

    @staticmethod
    @transaction.atomic
    def reject_lesson(
        lesson_learned: LessonLearned,
        reviewer,
        reason: str,
    ) -> LessonLearned:
        """
        Reject a lesson learned.
        """
        if lesson_learned.status != LessonLearned.Status.PENDING_REVIEW:
            raise ValueError("Solo se pueden rechazar lecciones pendientes de revisión")

        if not reason:
            raise ValueError("Debe proporcionar un motivo de rechazo")

        lesson_learned.status = LessonLearned.Status.REJECTED
        lesson_learned.reviewed_by = reviewer
        lesson_learned.reviewed_at = timezone.now()
        lesson_learned.review_notes = reason
        lesson_learned.save()

        logger.info(f"Lesson rejected: {lesson_learned.id} by {reviewer.id}")
        return lesson_learned

    @staticmethod
    def archive_lesson(lesson_learned: LessonLearned) -> LessonLearned:
        """
        Archive a lesson learned.
        """
        lesson_learned.status = LessonLearned.Status.ARCHIVED
        lesson_learned.save()

        logger.info(f"Lesson archived: {lesson_learned.id}")
        return lesson_learned

    @staticmethod
    def toggle_featured(lesson_learned: LessonLearned) -> LessonLearned:
        """
        Toggle the featured status of a lesson.
        """
        lesson_learned.is_featured = not lesson_learned.is_featured
        lesson_learned.save()

        return lesson_learned

    @staticmethod
    def increment_view_count(lesson_learned: LessonLearned) -> None:
        """
        Increment the view count of a lesson.
        Uses F() expression to avoid race conditions.
        """
        LessonLearned.objects.filter(id=lesson_learned.id).update(view_count=F("view_count") + 1)

    @staticmethod
    def get_approved_lessons(
        category: Category = None,
        lesson_type: str = None,
        severity: str = None,
        search: str = None,
        tags: list = None,
        featured_only: bool = False,
    ):
        """
        Get approved lessons with optional filters.
        """
        queryset = LessonLearned.objects.filter(
            status=LessonLearned.Status.APPROVED
        ).select_related("category", "created_by")

        if category:
            queryset = queryset.filter(category=category)

        if lesson_type:
            queryset = queryset.filter(lesson_type=lesson_type)

        if severity:
            queryset = queryset.filter(severity=severity)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(lesson__icontains=search)
                | Q(recommendations__icontains=search)
            )

        if tags:
            for tag in tags:
                queryset = queryset.filter(tags__contains=[tag])

        if featured_only:
            queryset = queryset.filter(is_featured=True)

        return queryset

    @staticmethod
    def get_pending_reviews():
        """
        Get all lessons pending review.
        """
        return (
            LessonLearned.objects.filter(status=LessonLearned.Status.PENDING_REVIEW)
            .select_related("category", "created_by")
            .order_by("created_at")
        )

    @staticmethod
    def get_lessons_by_user(user, include_drafts: bool = True):
        """
        Get lessons created by a specific user.
        """
        queryset = LessonLearned.objects.filter(created_by=user).select_related("category")

        if not include_drafts:
            queryset = queryset.exclude(status=LessonLearned.Status.DRAFT)

        return queryset.order_by("-created_at")

    @staticmethod
    def get_related_lessons(lesson_learned: LessonLearned, limit: int = 5):
        """
        Get related lessons based on category, tags, and type.
        """
        return (
            LessonLearned.objects.filter(
                status=LessonLearned.Status.APPROVED,
            )
            .filter(Q(category=lesson_learned.category) | Q(lesson_type=lesson_learned.lesson_type))
            .exclude(id=lesson_learned.id)
            .order_by("-view_count", "-created_at")[:limit]
        )

    @staticmethod
    def get_lessons_statistics(category: Category = None) -> dict:
        """
        Get statistics for lessons learned.
        """
        from django.db.models import Avg, Count, Sum

        queryset = LessonLearned.objects.all()

        if category:
            queryset = queryset.filter(category=category)

        stats = queryset.aggregate(
            total=Count("id"),
            total_views=Sum("view_count"),
            avg_views=Avg("view_count"),
        )

        by_status = queryset.values("status").annotate(count=Count("id"))
        by_type = queryset.values("lesson_type").annotate(count=Count("id"))
        by_severity = queryset.values("severity").annotate(count=Count("id"))

        return {
            "total": stats["total"] or 0,
            "total_views": stats["total_views"] or 0,
            "average_views": float(stats["avg_views"] or 0),
            "by_status": {item["status"]: item["count"] for item in by_status},
            "by_type": {item["lesson_type"]: item["count"] for item in by_type},
            "by_severity": {item["severity"]: item["count"] for item in by_severity},
        }


class LessonAttachmentService:
    """Service for lesson attachments."""

    @staticmethod
    def add_attachment(
        lesson_learned: LessonLearned,
        file,
        file_type: str,
        original_name: str,
        description: str = "",
    ) -> LessonAttachment:
        """
        Add an attachment to a lesson learned.
        """
        attachment = LessonAttachment.objects.create(
            lesson_learned=lesson_learned,
            file=file,
            file_type=file_type,
            original_name=original_name,
            description=description,
        )

        logger.info(f"Attachment added to lesson {lesson_learned.id}: {attachment.id}")
        return attachment

    @staticmethod
    def delete_attachment(attachment: LessonAttachment) -> None:
        """
        Delete an attachment.
        """
        # Delete file from storage
        if attachment.file:
            attachment.file.delete(save=False)

        attachment.delete()


class LessonCommentService:
    """Service for lesson comments."""

    @staticmethod
    def add_comment(
        lesson_learned: LessonLearned,
        user,
        content: str,
        parent: LessonComment = None,
    ) -> LessonComment:
        """
        Add a comment to a lesson learned.
        """
        if parent and parent.lesson_learned != lesson_learned:
            raise ValueError("El comentario padre no pertenece a esta lección")

        comment = LessonComment.objects.create(
            lesson_learned=lesson_learned,
            user=user,
            content=content,
            parent=parent,
        )

        return comment

    @staticmethod
    def get_comments(lesson_learned: LessonLearned, approved_only: bool = True):
        """
        Get comments for a lesson learned.
        """
        queryset = (
            LessonComment.objects.filter(
                lesson_learned=lesson_learned,
                parent__isnull=True,  # Only top-level comments
            )
            .select_related("user")
            .prefetch_related("replies__user")
        )

        if approved_only:
            queryset = queryset.filter(is_approved=True)

        return queryset.order_by("created_at")

    @staticmethod
    def moderate_comment(
        comment: LessonComment,
        approved: bool,
    ) -> LessonComment:
        """
        Approve or reject a comment.
        """
        comment.is_approved = approved
        comment.save()

        return comment

    @staticmethod
    def delete_comment(comment: LessonComment) -> None:
        """
        Delete a comment and its replies.
        """
        comment.delete()


class CategoryService:
    """Service for lesson categories."""

    @staticmethod
    def get_active_categories():
        """
        Get all active categories with hierarchy.
        """
        return (
            Category.objects.filter(
                is_active=True,
                parent__isnull=True,
            )
            .prefetch_related("children")
            .order_by("order", "name")
        )

    @staticmethod
    def get_category_tree():
        """
        Get category tree structure.
        """
        categories = Category.objects.filter(is_active=True).order_by("order", "name")

        tree = []
        category_map = {}

        for cat in categories:
            node = {
                "id": cat.id,
                "name": cat.name,
                "icon": cat.icon,
                "children": [],
            }
            category_map[cat.id] = node

            if cat.parent_id is None:
                tree.append(node)
            elif cat.parent_id in category_map:
                category_map[cat.parent_id]["children"].append(node)

        return tree

    @staticmethod
    def get_category_statistics():
        """
        Get lesson counts per category.
        """
        from django.db.models import Count

        return (
            Category.objects.filter(is_active=True)
            .annotate(
                lesson_count=Count(
                    "lessons_learned",
                    filter=Q(lessons_learned__status=LessonLearned.Status.APPROVED),
                )
            )
            .values("id", "name", "lesson_count")
        )
