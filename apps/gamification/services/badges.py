"""
Badge service for gamification.

Handles all badge-related operations including awarding and managing user badges.
"""

from django.db import transaction
from django.db.models import F

from apps.gamification.models import (
    Badge,
    UserBadge,
)


class BadgeService:
    """Service for managing badges."""

    @staticmethod
    def award_badge(
        user,
        badge_slug: str,
        reference_type: str = "",
        reference_id: int | None = None,
        skip_achievement_check: bool = False,
        **metadata,
    ) -> UserBadge | None:
        """
        Award a badge to a user.

        Returns UserBadge if awarded, None if already has or badge doesn't exist.

        Args:
            skip_achievement_check: If True, skip checking achievements after awarding points.
                                   Used to prevent infinite recursion when awarding badges
                                   from achievement rewards.
        """
        badge = Badge.objects.filter(slug=badge_slug, is_active=True).first()
        if not badge:
            return None

        # Check max awards
        if badge.max_awards and badge.times_awarded >= badge.max_awards:
            return None

        # Check if user already has this badge
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            return None

        with transaction.atomic():
            user_badge = UserBadge.objects.create(
                user=user,
                badge=badge,
                reference_type=reference_type,
                reference_id=reference_id,
                metadata=metadata,
            )

            # Update badge count
            badge.times_awarded = F("times_awarded") + 1
            badge.save(update_fields=["times_awarded"])

            # Award points if badge has point reward
            if badge.points_reward > 0:
                from apps.gamification.services.points import PointService

                PointService.award_points(
                    user=user,
                    points=badge.points_reward,
                    category_slug="badges",
                    description=f"Badge earned: {badge.name}",
                    reference_type="badge",
                    reference_id=badge.id,
                    skip_achievement_check=skip_achievement_check,
                )

        return user_badge

    @staticmethod
    def get_user_badges(user) -> dict:
        """Get user's badges organized by category."""
        user_badges = (
            UserBadge.objects.filter(user=user)
            .select_related("badge", "badge__category")
            .order_by("-earned_at")
        )

        # Organize by category
        by_category = {}
        for ub in user_badges:
            cat_name = ub.badge.category.name
            if cat_name not in by_category:
                by_category[cat_name] = []
            by_category[cat_name].append(ub)

        # Get all available badges for progress
        all_badges = Badge.objects.filter(is_active=True, is_secret=False).count()
        earned_badges = user_badges.count()

        return {
            "badges": list(user_badges),
            "by_category": by_category,
            "total_earned": earned_badges,
            "total_available": all_badges,
            "progress_percentage": (
                int((earned_badges / all_badges) * 100) if all_badges > 0 else 0
            ),
        }

    @staticmethod
    def get_featured_badges(user, limit: int = 3) -> list:
        """Get user's featured badges or most recent."""
        featured = UserBadge.objects.filter(
            user=user, is_featured=True
        ).select_related("badge")[:limit]

        if featured.count() < limit:
            # Fill with recent badges
            recent = (
                UserBadge.objects.filter(user=user, is_featured=False)
                .select_related("badge")
                .order_by("-earned_at")[: limit - featured.count()]
            )
            return list(featured) + list(recent)

        return list(featured)

    @staticmethod
    def set_featured_badges(user, badge_ids: list[int]) -> int:
        """Set featured badges for user (max 3)."""
        # Unfeature all
        UserBadge.objects.filter(user=user).update(is_featured=False)

        # Feature selected (max 3)
        return UserBadge.objects.filter(
            user=user, badge_id__in=badge_ids[:3]
        ).update(is_featured=True)
