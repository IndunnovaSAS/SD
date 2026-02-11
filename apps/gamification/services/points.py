"""
Point service for gamification.

Handles all point-related operations including awarding, deducting, and tracking points.
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.gamification.models import (
    Level,
    PointCategory,
    PointTransaction,
    UserPoints,
)


class PointService:
    """Service for managing user points."""

    @staticmethod
    def get_or_create_user_points(user) -> UserPoints:
        """Get or create user points record."""
        user_points, _ = UserPoints.objects.get_or_create(user=user)
        return user_points

    @staticmethod
    def award_points(
        user,
        points: int,
        category_slug: str,
        description: str,
        reference_type: str = "",
        reference_id: int | None = None,
        skip_achievement_check: bool = False,
        **metadata,
    ) -> tuple[int, bool]:
        """
        Award points to a user.

        Returns tuple of (points_awarded, leveled_up).

        Args:
            skip_achievement_check: If True, skip checking achievements after awarding points.
                                   Used to prevent infinite recursion when awarding points
                                   from achievement rewards.
        """
        # Convertir puntos negativos a positivos
        points = abs(points)

        category = PointCategory.objects.filter(slug=category_slug, is_active=True).first()
        if not category:
            return 0, False

        user_points = PointService.get_or_create_user_points(user)
        old_level = user_points.level

        with transaction.atomic():
            adjusted_points = user_points.add_points(
                points=points,
                category=category,
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata=metadata,
            )

        leveled_up = user_points.level and (
            not old_level or user_points.level.number > old_level.number
        )

        # Check for achievements after awarding points (unless skipped to prevent recursion)
        if not skip_achievement_check:
            # Lazy import to avoid circular dependency
            from apps.gamification.services.achievements import AchievementService

            AchievementService.check_achievements(user)

        return adjusted_points, leveled_up

    @staticmethod
    def deduct_points(
        user,
        points: int,
        category_slug: str,
        description: str,
        **metadata,
    ) -> bool:
        """
        Deduct points from a user.

        Returns True if successful, False if insufficient points.
        """
        user_points = PointService.get_or_create_user_points(user)

        if user_points.available_points < points:
            return False

        category = PointCategory.objects.filter(slug=category_slug, is_active=True).first()
        if not category:
            return False

        with transaction.atomic():
            PointTransaction.objects.create(
                user=user,
                category=category,
                transaction_type=PointTransaction.TransactionType.SPENT,
                points=-points,
                description=description,
                metadata=metadata,
            )
            user_points.available_points -= points
            user_points.save()

        return True

    @staticmethod
    def get_user_stats(user) -> dict:
        """Get user's gamification statistics."""
        user_points = PointService.get_or_create_user_points(user)

        # Get points by category
        points_by_category = (
            PointTransaction.objects.filter(user=user, points__gt=0)
            .values("category__name", "category__slug")
            .annotate(total=Sum("points"))
            .order_by("-total")
        )

        # Get next level info
        next_level = None
        points_to_next = 0
        if user_points.level:
            next_level = (
                Level.objects.filter(number__gt=user_points.level.number).order_by("number").first()
            )
            if next_level:
                points_to_next = next_level.min_points - user_points.total_points

        return {
            "total_points": user_points.total_points,
            "available_points": user_points.available_points,
            "level": user_points.level,
            "next_level": next_level,
            "points_to_next_level": max(0, points_to_next),
            "current_streak": user_points.current_streak,
            "longest_streak": user_points.longest_streak,
            "weekly_points": user_points.weekly_points,
            "monthly_points": user_points.monthly_points,
            "points_by_category": list(points_by_category),
        }

    @staticmethod
    def get_transaction_history(user, limit: int = 50) -> list:
        """Get user's point transaction history."""
        return list(
            PointTransaction.objects.filter(user=user)
            .select_related("category")
            .order_by("-created_at")[:limit]
        )

    @staticmethod
    def reset_periodic_points():
        """Reset weekly and monthly points (run via Celery)."""
        today = timezone.now().date()

        # Reset weekly points on Monday
        if today.weekday() == 0:
            UserPoints.objects.update(weekly_points=0)

        # Reset monthly points on 1st
        if today.day == 1:
            UserPoints.objects.update(monthly_points=0)
