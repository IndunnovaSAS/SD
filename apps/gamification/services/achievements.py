"""
Achievement service for gamification.

Handles all achievement-related operations including checking criteria and awarding achievements.
"""

from django.db import transaction

from apps.gamification.models import (
    Achievement,
    UserAchievement,
    UserBadge,
    UserChallenge,
)


class AchievementService:
    """Service for managing achievements."""

    @staticmethod
    def check_achievements(user) -> list[UserAchievement]:
        """Check and award any earned achievements."""
        unlocked = []
        achievements = Achievement.objects.filter(is_active=True)

        for achievement in achievements:
            if AchievementService._check_achievement_criteria(user, achievement):
                user_achievement = AchievementService._award_achievement(user, achievement)
                if user_achievement:
                    unlocked.append(user_achievement)

        return unlocked

    @staticmethod
    def _check_achievement_criteria(user, achievement: Achievement) -> bool:
        """Check if user meets achievement criteria."""
        from apps.gamification.services.points import PointService

        criteria = achievement.criteria
        if not criteria:
            return False

        # Check if already unlocked (unless repeatable)
        if not achievement.is_repeatable:
            if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
                return False

        # Common criteria checks
        user_points = PointService.get_or_create_user_points(user)

        # Points milestone
        if "min_points" in criteria:
            if user_points.total_points < criteria["min_points"]:
                return False

        # Level milestone
        if "min_level" in criteria:
            if not user_points.level or user_points.level.number < criteria["min_level"]:
                return False

        # Streak milestone
        if "min_streak" in criteria:
            if user_points.current_streak < criteria["min_streak"]:
                return False

        # Badge count
        if "min_badges" in criteria:
            badge_count = UserBadge.objects.filter(user=user).count()
            if badge_count < criteria["min_badges"]:
                return False

        # Completed courses
        if "min_courses" in criteria:
            from apps.courses.models import Enrollment

            course_count = Enrollment.objects.filter(
                user=user, status="completed"
            ).count()
            if course_count < criteria["min_courses"]:
                return False

        # Challenges completed
        if "min_challenges" in criteria:
            challenge_count = UserChallenge.objects.filter(
                user=user, status=UserChallenge.Status.COMPLETED
            ).count()
            if challenge_count < criteria["min_challenges"]:
                return False

        return True

    @staticmethod
    def _award_achievement(user, achievement: Achievement) -> UserAchievement | None:
        """Award achievement to user."""
        from apps.gamification.services.badges import BadgeService
        from apps.gamification.services.points import PointService

        with transaction.atomic():
            user_achievement, created = UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={"times_unlocked": 1},
            )

            if not created:
                if achievement.is_repeatable:
                    user_achievement.times_unlocked += 1
                    user_achievement.save()
                else:
                    return None

            # Award points (skip achievement check to prevent infinite recursion)
            if achievement.points_reward > 0:
                PointService.award_points(
                    user=user,
                    points=achievement.points_reward,
                    category_slug="achievements",
                    description=f"Achievement unlocked: {achievement.name}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                    skip_achievement_check=True,
                )

            # Award badge (skip achievement check to prevent infinite recursion)
            if achievement.badge:
                BadgeService.award_badge(
                    user=user,
                    badge_slug=achievement.badge.slug,
                    reference_type="achievement",
                    reference_id=achievement.id,
                    skip_achievement_check=True,
                )

        return user_achievement

    @staticmethod
    def get_user_achievements(user) -> dict:
        """Get user's achievements."""
        unlocked = (
            UserAchievement.objects.filter(user=user)
            .select_related("achievement")
            .order_by("-unlocked_at")
        )

        all_achievements = Achievement.objects.filter(is_active=True).count()
        unlocked_count = unlocked.count()

        return {
            "unlocked": list(unlocked),
            "total_unlocked": unlocked_count,
            "total_available": all_achievements,
            "progress_percentage": (
                int((unlocked_count / all_achievements) * 100)
                if all_achievements > 0
                else 0
            ),
        }
