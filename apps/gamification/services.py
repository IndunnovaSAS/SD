"""
Services for gamification app.

Business logic for points, badges, levels, leaderboards, challenges, and rewards.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from apps.gamification.models import (
    Achievement,
    Badge,
    BadgeCategory,
    Challenge,
    Leaderboard,
    LeaderboardEntry,
    Level,
    PointCategory,
    PointTransaction,
    Reward,
    RewardRedemption,
    UserAchievement,
    UserBadge,
    UserChallenge,
    UserPoints,
)

User = get_user_model()


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
        **metadata,
    ) -> tuple[int, bool]:
        """
        Award points to a user.

        Returns tuple of (points_awarded, leveled_up).
        """
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

        # Check for achievements after awarding points
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
            next_level = Level.objects.filter(
                number__gt=user_points.level.number
            ).order_by("number").first()
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


class BadgeService:
    """Service for managing badges."""

    @staticmethod
    def award_badge(
        user,
        badge_slug: str,
        reference_type: str = "",
        reference_id: int | None = None,
        **metadata,
    ) -> UserBadge | None:
        """
        Award a badge to a user.

        Returns UserBadge if awarded, None if already has or badge doesn't exist.
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
                PointService.award_points(
                    user=user,
                    points=badge.points_reward,
                    category_slug="badges",
                    description=f"Badge earned: {badge.name}",
                    reference_type="badge",
                    reference_id=badge.id,
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


class LeaderboardService:
    """Service for managing leaderboards."""

    @staticmethod
    def get_leaderboard_entries(
        leaderboard_slug: str,
        limit: int = 10,
        user=None,
    ) -> dict:
        """Get leaderboard entries with optional user position."""
        leaderboard = Leaderboard.objects.filter(
            slug=leaderboard_slug, is_active=True
        ).first()

        if not leaderboard:
            return {"entries": [], "user_rank": None, "leaderboard": None}

        entries = (
            LeaderboardEntry.objects.filter(leaderboard=leaderboard)
            .select_related("user")
            .order_by("rank")[:limit]
        )

        user_rank = None
        if user:
            user_entry = LeaderboardEntry.objects.filter(
                leaderboard=leaderboard, user=user
            ).first()
            if user_entry:
                user_rank = {
                    "rank": user_entry.rank,
                    "points": user_entry.points,
                    "rank_change": user_entry.rank_change,
                }

        return {
            "leaderboard": leaderboard,
            "entries": list(entries),
            "user_rank": user_rank,
        }

    @staticmethod
    def update_leaderboard(leaderboard_slug: str) -> int:
        """
        Update leaderboard rankings.

        Returns number of entries updated.
        """
        leaderboard = Leaderboard.objects.filter(
            slug=leaderboard_slug, is_active=True
        ).first()

        if not leaderboard:
            return 0

        today = timezone.now().date()

        # Determine period dates
        if leaderboard.period == Leaderboard.Period.DAILY:
            period_start = today
            period_end = today
        elif leaderboard.period == Leaderboard.Period.WEEKLY:
            period_start = today - timedelta(days=today.weekday())
            period_end = period_start + timedelta(days=6)
        elif leaderboard.period == Leaderboard.Period.MONTHLY:
            period_start = today.replace(day=1)
            if today.month == 12:
                period_end = today.replace(year=today.year + 1, month=1, day=1)
            else:
                period_end = today.replace(month=today.month + 1, day=1)
            period_end -= timedelta(days=1)
        else:  # ALL_TIME
            period_start = today.replace(year=2020, month=1, day=1)
            period_end = today

        # Get user rankings based on points
        if leaderboard.point_category:
            user_points = (
                PointTransaction.objects.filter(
                    category=leaderboard.point_category,
                    created_at__date__gte=period_start,
                    created_at__date__lte=period_end,
                    points__gt=0,
                )
                .values("user")
                .annotate(total=Sum("points"))
                .order_by("-total")[: leaderboard.max_entries]
            )
        else:
            user_points = (
                UserPoints.objects.all()
                .values("user")
                .annotate(total=F("total_points"))
                .order_by("-total")[: leaderboard.max_entries]
            )

        # Store current ranks for comparison
        old_ranks = dict(
            LeaderboardEntry.objects.filter(
                leaderboard=leaderboard, period_start=period_start
            ).values_list("user_id", "rank")
        )

        # Update entries
        entries_updated = 0
        with transaction.atomic():
            # Clear old entries for this period
            LeaderboardEntry.objects.filter(
                leaderboard=leaderboard, period_start=period_start
            ).delete()

            for rank, up in enumerate(user_points, 1):
                LeaderboardEntry.objects.create(
                    leaderboard=leaderboard,
                    user_id=up["user"],
                    rank=rank,
                    points=up["total"],
                    previous_rank=old_ranks.get(up["user"]),
                    period_start=period_start,
                    period_end=period_end,
                )
                entries_updated += 1

        return entries_updated

    @staticmethod
    def get_all_leaderboards() -> list:
        """Get all active leaderboards with top 3 entries."""
        leaderboards = Leaderboard.objects.filter(is_active=True)
        result = []

        for lb in leaderboards:
            top_entries = (
                LeaderboardEntry.objects.filter(leaderboard=lb)
                .select_related("user")
                .order_by("rank")[:3]
            )
            result.append({"leaderboard": lb, "top_3": list(top_entries)})

        return result


class ChallengeService:
    """Service for managing challenges."""

    @staticmethod
    def get_active_challenges(user=None) -> list:
        """Get all active challenges with optional user participation status."""
        now = timezone.now()
        challenges = Challenge.objects.filter(
            status=Challenge.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        )

        result = []
        for challenge in challenges:
            data = {"challenge": challenge, "user_participation": None}

            if user:
                participation = UserChallenge.objects.filter(
                    user=user, challenge=challenge
                ).first()
                data["user_participation"] = participation

            result.append(data)

        return result

    @staticmethod
    def join_challenge(user, challenge_id: int) -> UserChallenge | None:
        """Join a challenge."""
        challenge = Challenge.objects.filter(
            id=challenge_id,
            status=Challenge.Status.ACTIVE,
        ).first()

        if not challenge or not challenge.is_active:
            return None

        # Check max participants
        if challenge.max_participants:
            current = UserChallenge.objects.filter(challenge=challenge).count()
            if current >= challenge.max_participants:
                return None

        # Check if already joined
        existing = UserChallenge.objects.filter(user=user, challenge=challenge).first()
        if existing:
            return existing

        return UserChallenge.objects.create(user=user, challenge=challenge)

    @staticmethod
    def update_challenge_progress(
        user,
        challenge_id: int,
        value: int,
    ) -> UserChallenge | None:
        """Update user's progress in a challenge."""
        user_challenge = UserChallenge.objects.filter(
            user=user,
            challenge_id=challenge_id,
            status__in=[UserChallenge.Status.ENROLLED, UserChallenge.Status.IN_PROGRESS],
        ).select_related("challenge").first()

        if not user_challenge:
            return None

        user_challenge.update_progress(value)

        # If completed, award rewards
        if user_challenge.status == UserChallenge.Status.COMPLETED:
            ChallengeService._award_challenge_rewards(user_challenge)

        return user_challenge

    @staticmethod
    def _award_challenge_rewards(user_challenge: UserChallenge):
        """Award rewards for completing a challenge."""
        challenge = user_challenge.challenge

        # Award points
        if challenge.points_reward > 0:
            points, _ = PointService.award_points(
                user=user_challenge.user,
                points=challenge.points_reward,
                category_slug="challenges",
                description=f"Challenge completed: {challenge.name}",
                reference_type="challenge",
                reference_id=challenge.id,
            )
            user_challenge.points_earned = points

        # Award badge
        if challenge.badge_reward:
            badge = BadgeService.award_badge(
                user=user_challenge.user,
                badge_slug=challenge.badge_reward.slug,
                reference_type="challenge",
                reference_id=challenge.id,
            )
            user_challenge.badge_earned = badge is not None

        user_challenge.save()

    @staticmethod
    def get_user_challenges(user) -> dict:
        """Get user's challenge history."""
        challenges = (
            UserChallenge.objects.filter(user=user)
            .select_related("challenge")
            .order_by("-enrolled_at")
        )

        active = [c for c in challenges if c.challenge.is_active]
        completed = [c for c in challenges if c.status == UserChallenge.Status.COMPLETED]
        failed = [c for c in challenges if c.status == UserChallenge.Status.FAILED]

        return {
            "active": active,
            "completed": completed,
            "failed": failed,
            "total_completed": len(completed),
            "total_points_earned": sum(c.points_earned for c in completed),
        }


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

            # Award points
            if achievement.points_reward > 0:
                PointService.award_points(
                    user=user,
                    points=achievement.points_reward,
                    category_slug="achievements",
                    description=f"Achievement unlocked: {achievement.name}",
                    reference_type="achievement",
                    reference_id=achievement.id,
                )

            # Award badge
            if achievement.badge:
                BadgeService.award_badge(
                    user=user,
                    badge_slug=achievement.badge.slug,
                    reference_type="achievement",
                    reference_id=achievement.id,
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


class RewardService:
    """Service for managing rewards."""

    @staticmethod
    def get_available_rewards(user) -> list:
        """Get rewards available to user."""
        user_points = PointService.get_or_create_user_points(user)

        rewards = Reward.objects.filter(is_active=True)
        result = []

        for reward in rewards:
            if not reward.is_available:
                continue

            # Check level requirement
            if reward.min_level:
                if not user_points.level or user_points.level.number < reward.min_level.number:
                    continue

            can_afford = user_points.available_points >= reward.points_cost
            result.append({"reward": reward, "can_afford": can_afford})

        return result

    @staticmethod
    def redeem_reward(user, reward_id: int, notes: str = "") -> RewardRedemption | None:
        """Redeem a reward."""
        reward = Reward.objects.filter(id=reward_id, is_active=True).first()
        if not reward or not reward.is_available:
            return None

        user_points = PointService.get_or_create_user_points(user)

        # Check level
        if reward.min_level:
            if not user_points.level or user_points.level.number < reward.min_level.number:
                return None

        # Check points
        if user_points.available_points < reward.points_cost:
            return None

        with transaction.atomic():
            # Deduct points
            success = PointService.deduct_points(
                user=user,
                points=reward.points_cost,
                category_slug="rewards",
                description=f"Redeemed reward: {reward.name}",
            )

            if not success:
                return None

            # Create redemption
            redemption = RewardRedemption.objects.create(
                user=user,
                reward=reward,
                points_spent=reward.points_cost,
                notes=notes,
            )

            # Update quantity
            reward.quantity_redeemed = F("quantity_redeemed") + 1
            reward.save(update_fields=["quantity_redeemed"])

        return redemption

    @staticmethod
    def get_user_redemptions(user) -> list:
        """Get user's reward redemption history."""
        return list(
            RewardRedemption.objects.filter(user=user)
            .select_related("reward")
            .order_by("-redeemed_at")
        )

    @staticmethod
    def fulfill_redemption(redemption_id: int, fulfilled_by, notes: str = "") -> bool:
        """Mark a redemption as fulfilled."""
        redemption = RewardRedemption.objects.filter(
            id=redemption_id,
            status=RewardRedemption.Status.APPROVED,
        ).first()

        if not redemption:
            return False

        redemption.status = RewardRedemption.Status.FULFILLED
        redemption.fulfilled_at = timezone.now()
        redemption.fulfilled_by = fulfilled_by
        if notes:
            redemption.notes = f"{redemption.notes}\n{notes}".strip()
        redemption.save()

        return True


class GamificationDashboardService:
    """Service for gamification dashboard and analytics."""

    @staticmethod
    def get_user_dashboard(user) -> dict:
        """Get comprehensive gamification dashboard for user."""
        return {
            "stats": PointService.get_user_stats(user),
            "badges": BadgeService.get_user_badges(user),
            "featured_badges": BadgeService.get_featured_badges(user),
            "achievements": AchievementService.get_user_achievements(user),
            "challenges": ChallengeService.get_user_challenges(user),
            "recent_transactions": PointService.get_transaction_history(user, limit=10),
        }

    @staticmethod
    def get_admin_analytics() -> dict:
        """Get gamification analytics for admins."""
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Point statistics
        total_points = PointTransaction.objects.filter(points__gt=0).aggregate(
            total=Sum("points")
        )["total"] or 0

        points_today = PointTransaction.objects.filter(
            created_at__date=today, points__gt=0
        ).aggregate(total=Sum("points"))["total"] or 0

        points_this_week = PointTransaction.objects.filter(
            created_at__date__gte=week_start, points__gt=0
        ).aggregate(total=Sum("points"))["total"] or 0

        # Badge statistics
        total_badges_awarded = UserBadge.objects.count()

        # Active users (with points this week)
        active_users = (
            PointTransaction.objects.filter(created_at__date__gte=week_start)
            .values("user")
            .distinct()
            .count()
        )

        # Top earners this week
        top_earners = (
            PointTransaction.objects.filter(
                created_at__date__gte=week_start, points__gt=0
            )
            .values("user", "user__email", "user__first_name", "user__last_name")
            .annotate(total=Sum("points"))
            .order_by("-total")[:10]
        )

        # Challenge statistics
        active_challenges = Challenge.objects.filter(
            status=Challenge.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        ).count()

        completed_challenges = UserChallenge.objects.filter(
            status=UserChallenge.Status.COMPLETED
        ).count()

        return {
            "points": {
                "total": total_points,
                "today": points_today,
                "this_week": points_this_week,
            },
            "badges": {
                "total_awarded": total_badges_awarded,
            },
            "users": {
                "active_this_week": active_users,
                "top_earners": list(top_earners),
            },
            "challenges": {
                "active": active_challenges,
                "completed": completed_challenges,
            },
        }
