"""
Tests for gamification services.

Comprehensive tests for PointService, BadgeService, AchievementService,
ChallengeService, LeaderboardService, and RewardService.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.gamification.models import (
    Leaderboard,
    LeaderboardEntry,
    PointTransaction,
    RewardRedemption,
    UserAchievement,
    UserChallenge,
    UserPoints,
)
from apps.gamification.services import (
    AchievementService,
    BadgeService,
    ChallengeService,
    GamificationDashboardService,
    LeaderboardService,
    PointService,
    RewardService,
)
from apps.gamification.tests.factories import (
    AchievementFactory,
    AdminUserFactory,
    BadgeCategoryFactory,
    BadgeFactory,
    ChallengeFactory,
    ExpiredChallengeFactory,
    ExpiredRewardFactory,
    FutureRewardFactory,
    LeaderboardEntryFactory,
    LeaderboardFactory,
    LevelFactory,
    LimitedRewardFactory,
    PointCategoryFactory,
    PointTransactionFactory,
    RewardFactory,
    UserAchievementFactory,
    UserBadgeFactory,
    UserChallengeFactory,
    UserFactory,
    UserPointsFactory,
)

# ============================================================================
# PointService Tests
# ============================================================================


class TestPointServiceGetOrCreateUserPoints(TestCase):
    """Tests for PointService.get_or_create_user_points."""

    def test_creates_user_points_if_not_exists(self):
        """Test that UserPoints is created if it doesn't exist."""
        user = UserFactory()

        user_points = PointService.get_or_create_user_points(user)

        self.assertIsNotNone(user_points)
        self.assertEqual(user_points.user, user)
        self.assertEqual(user_points.total_points, 0)

    def test_returns_existing_user_points(self):
        """Test that existing UserPoints is returned."""
        user = UserFactory()
        existing = UserPointsFactory(user=user)
        # Update points after creation to ensure values persist
        existing.total_points = 500
        existing.save()

        user_points = PointService.get_or_create_user_points(user)

        self.assertEqual(user_points.id, existing.id)
        self.assertEqual(user_points.total_points, 500)


class TestPointServiceAwardPoints(TestCase):
    """Tests for PointService.award_points."""

    def setUp(self):
        self.user = UserFactory()
        self.category = PointCategoryFactory(slug="test-category", multiplier=Decimal("1.0"))

    def test_award_points_success(self):
        """Test awarding points successfully."""
        points, leveled_up = PointService.award_points(
            user=self.user,
            points=100,
            category_slug="test-category",
            description="Test award",
        )

        self.assertEqual(points, 100)
        self.assertFalse(leveled_up)

        user_points = UserPoints.objects.get(user=self.user)
        self.assertEqual(user_points.total_points, 100)
        self.assertEqual(user_points.available_points, 100)

    def test_award_points_with_multiplier(self):
        """Test that category multiplier is applied."""
        self.category.multiplier = Decimal("1.5")
        self.category.save()

        points, _ = PointService.award_points(
            user=self.user,
            points=100,
            category_slug="test-category",
            description="Multiplied award",
        )

        self.assertEqual(points, 150)

    def test_award_points_invalid_category_returns_zero(self):
        """Test that invalid category returns 0 points."""
        points, leveled_up = PointService.award_points(
            user=self.user,
            points=100,
            category_slug="non-existent-category",
            description="Should fail",
        )

        self.assertEqual(points, 0)
        self.assertFalse(leveled_up)

    def test_award_points_inactive_category_returns_zero(self):
        """Test that inactive category returns 0 points."""
        self.category.is_active = False
        self.category.save()

        points, leveled_up = PointService.award_points(
            user=self.user,
            points=100,
            category_slug="test-category",
            description="Should fail",
        )

        self.assertEqual(points, 0)

    def test_award_points_creates_transaction(self):
        """Test that a transaction is created."""
        PointService.award_points(
            user=self.user,
            points=100,
            category_slug="test-category",
            description="Test transaction",
            reference_type="test",
            reference_id=1,
        )

        transaction = PointTransaction.objects.get(user=self.user)
        self.assertEqual(transaction.points, 100)
        self.assertEqual(transaction.description, "Test transaction")
        self.assertEqual(transaction.reference_type, "test")
        self.assertEqual(transaction.reference_id, 1)

    def test_award_points_level_up(self):
        """Test that leveling up is detected."""
        LevelFactory(number=1, min_points=0, max_points=99)
        LevelFactory(number=2, min_points=100, max_points=199)

        points, leveled_up = PointService.award_points(
            user=self.user,
            points=150,
            category_slug="test-category",
            description="Level up!",
        )

        self.assertTrue(leveled_up)
        user_points = UserPoints.objects.get(user=self.user)
        self.assertEqual(user_points.level.number, 2)

    def test_award_zero_points(self):
        """Test awarding zero points."""
        points, _ = PointService.award_points(
            user=self.user,
            points=0,
            category_slug="test-category",
            description="Zero points",
        )

        self.assertEqual(points, 0)

    def test_award_negative_points_converted_to_positive(self):
        """Test that negative points are converted to positive (use deduct_points for penalties)."""
        # award_points uses abs() to ensure points are always positive
        # For penalties, use deduct_points instead
        points, _ = PointService.award_points(
            user=self.user,
            points=-50,
            category_slug="test-category",
            description="Negative points converted to positive",
        )

        # Implementation uses abs(), so -50 becomes 50
        self.assertEqual(points, 50)

    def test_award_points_updates_weekly_monthly(self):
        """Test that weekly and monthly points are updated."""
        PointService.award_points(
            user=self.user,
            points=100,
            category_slug="test-category",
            description="Weekly/Monthly test",
        )

        user_points = UserPoints.objects.get(user=self.user)
        self.assertEqual(user_points.weekly_points, 100)
        self.assertEqual(user_points.monthly_points, 100)


class TestPointServiceDeductPoints(TestCase):
    """Tests for PointService.deduct_points."""

    def setUp(self):
        self.user = UserFactory()
        self.category = PointCategoryFactory(slug="rewards")
        self.user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        self.user_points.total_points = 500
        self.user_points.available_points = 500
        self.user_points.save()

    def test_deduct_points_success(self):
        """Test deducting points successfully."""
        result = PointService.deduct_points(
            user=self.user,
            points=100,
            category_slug="rewards",
            description="Test deduction",
        )

        self.assertTrue(result)
        self.user_points.refresh_from_db()
        self.assertEqual(self.user_points.available_points, 400)

    def test_deduct_points_insufficient_balance(self):
        """Test that deduction fails with insufficient points."""
        result = PointService.deduct_points(
            user=self.user,
            points=600,
            category_slug="rewards",
            description="Too much",
        )

        self.assertFalse(result)
        self.user_points.refresh_from_db()
        self.assertEqual(self.user_points.available_points, 500)

    def test_deduct_points_invalid_category(self):
        """Test that deduction fails with invalid category."""
        result = PointService.deduct_points(
            user=self.user,
            points=100,
            category_slug="non-existent",
            description="Invalid category",
        )

        self.assertFalse(result)

    def test_deduct_points_creates_negative_transaction(self):
        """Test that a negative transaction is created."""
        PointService.deduct_points(
            user=self.user,
            points=100,
            category_slug="rewards",
            description="Test deduction",
        )

        transaction = PointTransaction.objects.get(user=self.user)
        self.assertEqual(transaction.points, -100)
        self.assertEqual(transaction.transaction_type, PointTransaction.TransactionType.SPENT)

    def test_deduct_exact_balance(self):
        """Test deducting exact available balance."""
        result = PointService.deduct_points(
            user=self.user,
            points=500,
            category_slug="rewards",
            description="Exact balance",
        )

        self.assertTrue(result)
        self.user_points.refresh_from_db()
        self.assertEqual(self.user_points.available_points, 0)


class TestPointServiceGetUserStats(TestCase):
    """Tests for PointService.get_user_stats."""

    def setUp(self):
        self.user = UserFactory()
        self.level1 = LevelFactory(number=1, min_points=0, max_points=99)
        self.level2 = LevelFactory(number=2, min_points=100, max_points=199)
        self.category = PointCategoryFactory(slug="test-cat")

    def test_get_user_stats_basic(self):
        """Test getting basic user stats."""
        user_points = UserPointsFactory(user=self.user)
        # Update values after creation to ensure they persist
        user_points.total_points = 150
        user_points.available_points = 100
        user_points.level = self.level2
        user_points.current_streak = 5
        user_points.longest_streak = 10
        user_points.save()

        stats = PointService.get_user_stats(self.user)

        self.assertEqual(stats["total_points"], 150)
        self.assertEqual(stats["available_points"], 100)
        self.assertEqual(stats["level"], self.level2)
        self.assertEqual(stats["current_streak"], 5)
        self.assertEqual(stats["longest_streak"], 10)

    def test_get_user_stats_with_next_level(self):
        """Test that next level info is included."""
        LevelFactory(number=3, min_points=200, max_points=299)
        user_points = UserPointsFactory(user=self.user)
        # Update values after creation to ensure they persist
        user_points.total_points = 150
        user_points.level = self.level2
        user_points.save()

        stats = PointService.get_user_stats(self.user)

        self.assertIsNotNone(stats["next_level"])
        self.assertEqual(stats["next_level"].number, 3)
        self.assertEqual(stats["points_to_next_level"], 50)

    def test_get_user_stats_points_by_category(self):
        """Test that points by category are included."""
        PointTransactionFactory(user=self.user, category=self.category, points=50)
        PointTransactionFactory(user=self.user, category=self.category, points=30)

        stats = PointService.get_user_stats(self.user)

        self.assertIn("points_by_category", stats)
        self.assertEqual(len(stats["points_by_category"]), 1)
        self.assertEqual(stats["points_by_category"][0]["total"], 80)


class TestPointServiceGetTransactionHistory(TestCase):
    """Tests for PointService.get_transaction_history."""

    def setUp(self):
        self.user = UserFactory()
        self.category = PointCategoryFactory()

    def test_get_transaction_history(self):
        """Test getting transaction history."""
        for i in range(5):
            PointTransactionFactory(user=self.user, category=self.category, points=10 * i)

        history = PointService.get_transaction_history(self.user, limit=10)

        self.assertEqual(len(history), 5)

    def test_get_transaction_history_respects_limit(self):
        """Test that limit is respected."""
        for i in range(10):
            PointTransactionFactory(user=self.user, category=self.category)

        history = PointService.get_transaction_history(self.user, limit=5)

        self.assertEqual(len(history), 5)

    def test_get_transaction_history_ordered_by_date(self):
        """Test that transactions are ordered by date descending."""
        old_tx = PointTransactionFactory(user=self.user, category=self.category)
        old_tx.created_at = timezone.now() - timedelta(days=1)
        old_tx.save()
        new_tx = PointTransactionFactory(user=self.user, category=self.category)

        history = PointService.get_transaction_history(self.user)

        self.assertEqual(history[0].id, new_tx.id)


class TestPointServiceResetPeriodicPoints(TestCase):
    """Tests for PointService.reset_periodic_points."""

    def test_reset_weekly_points_on_monday(self):
        """Test that weekly points are reset on Monday."""
        user = UserFactory()
        user_points = UserPointsFactory(user=user)
        # Update values after creation to ensure they persist
        user_points.weekly_points = 100
        user_points.monthly_points = 200
        user_points.save()

        # Mock today as Monday
        with patch("apps.gamification.services.points.timezone") as mock_tz:
            mock_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # Make it a Monday
            days_to_monday = mock_date.weekday()
            mock_date = mock_date - timedelta(days=days_to_monday)
            mock_tz.now.return_value = mock_date

            PointService.reset_periodic_points()

        user_points = UserPoints.objects.get(user=user)
        self.assertEqual(user_points.weekly_points, 0)
        # Monthly not reset unless it's the 1st
        if mock_date.day != 1:
            self.assertEqual(user_points.monthly_points, 200)

    def test_reset_monthly_points_on_first(self):
        """Test that monthly points are reset on the 1st."""
        user = UserFactory()
        user_points = UserPointsFactory(user=user)
        # Update values after creation to ensure they persist
        user_points.weekly_points = 100
        user_points.monthly_points = 200
        user_points.save()

        with patch("apps.gamification.services.points.timezone") as mock_tz:
            # Make it the 1st of the month
            mock_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            mock_tz.now.return_value = mock_date

            PointService.reset_periodic_points()

        user_points = UserPoints.objects.get(user=user)
        self.assertEqual(user_points.monthly_points, 0)


# ============================================================================
# BadgeService Tests
# ============================================================================


class TestBadgeServiceAwardBadge(TestCase):
    """Tests for BadgeService.award_badge."""

    def setUp(self):
        self.user = UserFactory()
        self.badge_category = BadgeCategoryFactory()
        self.badge = BadgeFactory(
            slug="test-badge",
            category=self.badge_category,
            points_reward=50,
        )
        # Create badges category for points
        PointCategoryFactory(slug="badges")

    def test_award_badge_success(self):
        """Test awarding a badge successfully."""
        user_badge = BadgeService.award_badge(
            user=self.user,
            badge_slug="test-badge",
        )

        self.assertIsNotNone(user_badge)
        self.assertEqual(user_badge.user, self.user)
        self.assertEqual(user_badge.badge, self.badge)

    def test_award_badge_increments_times_awarded(self):
        """Test that times_awarded is incremented."""
        initial_count = self.badge.times_awarded

        BadgeService.award_badge(user=self.user, badge_slug="test-badge")

        self.badge.refresh_from_db()
        self.assertEqual(self.badge.times_awarded, initial_count + 1)

    def test_award_badge_awards_points(self):
        """Test that points are awarded with the badge."""
        BadgeService.award_badge(user=self.user, badge_slug="test-badge")

        user_points = UserPoints.objects.get(user=self.user)
        self.assertEqual(user_points.total_points, 50)

    def test_award_badge_duplicate_returns_none(self):
        """Test that awarding duplicate badge returns None."""
        BadgeService.award_badge(user=self.user, badge_slug="test-badge")
        result = BadgeService.award_badge(user=self.user, badge_slug="test-badge")

        self.assertIsNone(result)

    def test_award_badge_non_existent_returns_none(self):
        """Test that awarding non-existent badge returns None."""
        result = BadgeService.award_badge(
            user=self.user,
            badge_slug="non-existent-badge",
        )

        self.assertIsNone(result)

    def test_award_badge_inactive_returns_none(self):
        """Test that awarding inactive badge returns None."""
        self.badge.is_active = False
        self.badge.save()

        result = BadgeService.award_badge(user=self.user, badge_slug="test-badge")

        self.assertIsNone(result)

    def test_award_badge_max_awards_reached(self):
        """Test that badge with max awards reached returns None."""
        self.badge.max_awards = 1
        self.badge.times_awarded = 1
        self.badge.save()

        result = BadgeService.award_badge(user=self.user, badge_slug="test-badge")

        self.assertIsNone(result)

    def test_award_badge_with_reference(self):
        """Test awarding badge with reference info."""
        user_badge = BadgeService.award_badge(
            user=self.user,
            badge_slug="test-badge",
            reference_type="course",
            reference_id=123,
        )

        self.assertEqual(user_badge.reference_type, "course")
        self.assertEqual(user_badge.reference_id, 123)


class TestBadgeServiceGetUserBadges(TestCase):
    """Tests for BadgeService.get_user_badges."""

    def setUp(self):
        self.user = UserFactory()
        self.category1 = BadgeCategoryFactory(name="Category 1")
        self.category2 = BadgeCategoryFactory(name="Category 2")

    def test_get_user_badges_empty(self):
        """Test getting badges for user with no badges."""
        result = BadgeService.get_user_badges(self.user)

        self.assertEqual(result["badges"], [])
        self.assertEqual(result["total_earned"], 0)

    def test_get_user_badges_with_badges(self):
        """Test getting badges for user with earned badges."""
        badge1 = BadgeFactory(category=self.category1)
        badge2 = BadgeFactory(category=self.category2)
        UserBadgeFactory(user=self.user, badge=badge1)
        UserBadgeFactory(user=self.user, badge=badge2)

        result = BadgeService.get_user_badges(self.user)

        self.assertEqual(result["total_earned"], 2)
        self.assertEqual(len(result["badges"]), 2)

    def test_get_user_badges_organized_by_category(self):
        """Test that badges are organized by category."""
        badge1 = BadgeFactory(category=self.category1)
        badge2 = BadgeFactory(category=self.category1)
        badge3 = BadgeFactory(category=self.category2)
        UserBadgeFactory(user=self.user, badge=badge1)
        UserBadgeFactory(user=self.user, badge=badge2)
        UserBadgeFactory(user=self.user, badge=badge3)

        result = BadgeService.get_user_badges(self.user)

        self.assertIn("Category 1", result["by_category"])
        self.assertIn("Category 2", result["by_category"])
        self.assertEqual(len(result["by_category"]["Category 1"]), 2)
        self.assertEqual(len(result["by_category"]["Category 2"]), 1)

    def test_get_user_badges_progress_percentage(self):
        """Test that progress percentage is calculated correctly."""
        # Create 4 available badges
        for i in range(4):
            badge = BadgeFactory(category=self.category1, is_secret=False)
            if i < 2:  # User earned 2
                UserBadgeFactory(user=self.user, badge=badge)

        result = BadgeService.get_user_badges(self.user)

        self.assertEqual(result["progress_percentage"], 50)


class TestBadgeServiceGetFeaturedBadges(TestCase):
    """Tests for BadgeService.get_featured_badges."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()

    def test_get_featured_badges_returns_featured(self):
        """Test that featured badges are returned."""
        badge1 = BadgeFactory(category=self.category)
        badge2 = BadgeFactory(category=self.category)
        UserBadgeFactory(user=self.user, badge=badge1, is_featured=True)
        UserBadgeFactory(user=self.user, badge=badge2, is_featured=False)

        result = BadgeService.get_featured_badges(self.user, limit=3)

        # Should include featured + recent
        self.assertEqual(len(result), 2)

    def test_get_featured_badges_fills_with_recent(self):
        """Test that recent badges fill in when not enough featured."""
        badges = [BadgeFactory(category=self.category) for _ in range(3)]
        for badge in badges:
            UserBadgeFactory(user=self.user, badge=badge, is_featured=False)

        result = BadgeService.get_featured_badges(self.user, limit=3)

        self.assertEqual(len(result), 3)


class TestBadgeServiceSetFeaturedBadges(TestCase):
    """Tests for BadgeService.set_featured_badges."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()

    def test_set_featured_badges(self):
        """Test setting featured badges."""
        badges = [BadgeFactory(category=self.category) for _ in range(3)]
        user_badges = [UserBadgeFactory(user=self.user, badge=b) for b in badges]

        count = BadgeService.set_featured_badges(self.user, [badges[0].id, badges[1].id])

        self.assertEqual(count, 2)
        user_badges[0].refresh_from_db()
        user_badges[1].refresh_from_db()
        self.assertTrue(user_badges[0].is_featured)
        self.assertTrue(user_badges[1].is_featured)

    def test_set_featured_badges_max_three(self):
        """Test that only 3 badges can be featured."""
        badges = [BadgeFactory(category=self.category) for _ in range(5)]
        for badge in badges:
            UserBadgeFactory(user=self.user, badge=badge)

        count = BadgeService.set_featured_badges(self.user, [b.id for b in badges])

        self.assertEqual(count, 3)

    def test_set_featured_clears_previous(self):
        """Test that previous featured badges are cleared."""
        badge1 = BadgeFactory(category=self.category)
        badge2 = BadgeFactory(category=self.category)
        ub1 = UserBadgeFactory(user=self.user, badge=badge1, is_featured=True)
        ub2 = UserBadgeFactory(user=self.user, badge=badge2, is_featured=False)

        BadgeService.set_featured_badges(self.user, [badge2.id])

        ub1.refresh_from_db()
        ub2.refresh_from_db()
        self.assertFalse(ub1.is_featured)
        self.assertTrue(ub2.is_featured)


# ============================================================================
# LeaderboardService Tests
# ============================================================================


class TestLeaderboardServiceGetEntries(TestCase):
    """Tests for LeaderboardService.get_leaderboard_entries."""

    def setUp(self):
        self.leaderboard = LeaderboardFactory(slug="weekly-leaders")
        self.users = [UserFactory() for _ in range(5)]

    def test_get_entries_non_existent_leaderboard(self):
        """Test getting entries for non-existent leaderboard."""
        result = LeaderboardService.get_leaderboard_entries("non-existent")

        self.assertEqual(result["entries"], [])
        self.assertIsNone(result["leaderboard"])

    def test_get_entries_with_entries(self):
        """Test getting leaderboard entries."""
        for i, user in enumerate(self.users):
            LeaderboardEntryFactory(
                leaderboard=self.leaderboard,
                user=user,
                rank=i + 1,
                points=1000 - i * 100,
            )

        result = LeaderboardService.get_leaderboard_entries("weekly-leaders")

        self.assertEqual(len(result["entries"]), 5)
        self.assertEqual(result["leaderboard"], self.leaderboard)

    def test_get_entries_respects_limit(self):
        """Test that limit is respected."""
        for i, user in enumerate(self.users):
            LeaderboardEntryFactory(
                leaderboard=self.leaderboard,
                user=user,
                rank=i + 1,
            )

        result = LeaderboardService.get_leaderboard_entries("weekly-leaders", limit=3)

        self.assertEqual(len(result["entries"]), 3)

    def test_get_entries_includes_user_rank(self):
        """Test that user's rank is included."""
        for i, user in enumerate(self.users):
            LeaderboardEntryFactory(
                leaderboard=self.leaderboard,
                user=user,
                rank=i + 1,
                points=1000 - i * 100,
            )

        result = LeaderboardService.get_leaderboard_entries(
            "weekly-leaders",
            user=self.users[2],
        )

        self.assertIsNotNone(result["user_rank"])
        self.assertEqual(result["user_rank"]["rank"], 3)

    def test_get_entries_inactive_leaderboard(self):
        """Test getting entries for inactive leaderboard."""
        self.leaderboard.is_active = False
        self.leaderboard.save()

        result = LeaderboardService.get_leaderboard_entries("weekly-leaders")

        self.assertEqual(result["entries"], [])


class TestLeaderboardServiceUpdateLeaderboard(TestCase):
    """Tests for LeaderboardService.update_leaderboard."""

    def setUp(self):
        self.category = PointCategoryFactory()
        self.leaderboard = LeaderboardFactory(
            slug="test-board",
            period=Leaderboard.Period.WEEKLY,
            point_category=self.category,
        )

    def test_update_leaderboard_non_existent(self):
        """Test updating non-existent leaderboard returns 0."""
        result = LeaderboardService.update_leaderboard("non-existent")

        self.assertEqual(result, 0)

    def test_update_leaderboard_creates_entries(self):
        """Test that leaderboard entries are created."""
        users = [UserFactory() for _ in range(3)]
        for i, user in enumerate(users):
            PointTransactionFactory(
                user=user,
                category=self.category,
                points=100 * (i + 1),
            )

        result = LeaderboardService.update_leaderboard("test-board")

        self.assertEqual(result, 3)
        entries = LeaderboardEntry.objects.filter(leaderboard=self.leaderboard)
        self.assertEqual(entries.count(), 3)

    def test_update_leaderboard_orders_by_points(self):
        """Test that entries are ordered by points."""
        user1 = UserFactory()
        user2 = UserFactory()
        PointTransactionFactory(user=user1, category=self.category, points=100)
        PointTransactionFactory(user=user2, category=self.category, points=200)

        LeaderboardService.update_leaderboard("test-board")

        entries = LeaderboardEntry.objects.filter(leaderboard=self.leaderboard).order_by("rank")
        self.assertEqual(entries[0].user, user2)
        self.assertEqual(entries[0].rank, 1)

    def test_update_leaderboard_inactive(self):
        """Test updating inactive leaderboard returns 0."""
        self.leaderboard.is_active = False
        self.leaderboard.save()

        result = LeaderboardService.update_leaderboard("test-board")

        self.assertEqual(result, 0)


class TestLeaderboardServiceGetAllLeaderboards(TestCase):
    """Tests for LeaderboardService.get_all_leaderboards."""

    def test_get_all_leaderboards(self):
        """Test getting all active leaderboards."""
        lb1 = LeaderboardFactory(is_active=True)
        lb2 = LeaderboardFactory(is_active=True)
        lb3 = LeaderboardFactory(is_active=False)

        result = LeaderboardService.get_all_leaderboards()

        self.assertEqual(len(result), 2)

    def test_get_all_leaderboards_with_top_entries(self):
        """Test that top 3 entries are included."""
        leaderboard = LeaderboardFactory()
        users = [UserFactory() for _ in range(5)]
        for i, user in enumerate(users):
            LeaderboardEntryFactory(
                leaderboard=leaderboard,
                user=user,
                rank=i + 1,
            )

        result = LeaderboardService.get_all_leaderboards()

        self.assertEqual(len(result[0]["top_3"]), 3)


# ============================================================================
# ChallengeService Tests
# ============================================================================


class TestChallengeServiceGetActiveChallenges(TestCase):
    """Tests for ChallengeService.get_active_challenges."""

    def test_get_active_challenges(self):
        """Test getting active challenges."""
        ChallengeFactory()
        ChallengeFactory()
        ExpiredChallengeFactory()

        result = ChallengeService.get_active_challenges()

        self.assertEqual(len(result), 2)

    def test_get_active_challenges_with_user_participation(self):
        """Test that user participation is included."""
        challenge = ChallengeFactory()
        user = UserFactory()
        UserChallengeFactory(user=user, challenge=challenge)

        result = ChallengeService.get_active_challenges(user=user)

        self.assertIsNotNone(result[0]["user_participation"])


class TestChallengeServiceJoinChallenge(TestCase):
    """Tests for ChallengeService.join_challenge."""

    def setUp(self):
        self.user = UserFactory()
        self.challenge = ChallengeFactory()

    def test_join_challenge_success(self):
        """Test joining a challenge successfully."""
        result = ChallengeService.join_challenge(self.user, self.challenge.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.user, self.user)
        self.assertEqual(result.challenge, self.challenge)

    def test_join_challenge_already_joined(self):
        """Test joining already joined challenge returns existing."""
        existing = UserChallengeFactory(user=self.user, challenge=self.challenge)

        result = ChallengeService.join_challenge(self.user, self.challenge.id)

        self.assertEqual(result.id, existing.id)

    def test_join_challenge_expired(self):
        """Test joining expired challenge returns None."""
        expired = ExpiredChallengeFactory()

        result = ChallengeService.join_challenge(self.user, expired.id)

        self.assertIsNone(result)

    def test_join_challenge_max_participants_reached(self):
        """Test joining when max participants reached."""
        self.challenge.max_participants = 2
        self.challenge.save()

        UserChallengeFactory(challenge=self.challenge)
        UserChallengeFactory(challenge=self.challenge)

        result = ChallengeService.join_challenge(self.user, self.challenge.id)

        self.assertIsNone(result)

    def test_join_challenge_non_existent(self):
        """Test joining non-existent challenge."""
        result = ChallengeService.join_challenge(self.user, 99999)

        self.assertIsNone(result)


class TestChallengeServiceUpdateProgress(TestCase):
    """Tests for ChallengeService.update_challenge_progress."""

    def setUp(self):
        self.user = UserFactory()
        self.challenge = ChallengeFactory(
            target_value=100,
            points_reward=50,
        )
        PointCategoryFactory(slug="challenges")

    def test_update_progress(self):
        """Test updating challenge progress."""
        user_challenge = UserChallengeFactory(
            user=self.user,
            challenge=self.challenge,
            status=UserChallenge.Status.ENROLLED,
        )

        result = ChallengeService.update_challenge_progress(
            self.user,
            self.challenge.id,
            30,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.current_value, 30)
        self.assertEqual(result.status, UserChallenge.Status.IN_PROGRESS)

    def test_update_progress_completes_challenge(self):
        """Test that completing target completes challenge."""
        user_challenge = UserChallengeFactory(
            user=self.user,
            challenge=self.challenge,
            current_value=80,
            status=UserChallenge.Status.IN_PROGRESS,
        )

        result = ChallengeService.update_challenge_progress(
            self.user,
            self.challenge.id,
            30,
        )

        self.assertEqual(result.status, UserChallenge.Status.COMPLETED)
        self.assertIsNotNone(result.completed_at)

    def test_update_progress_not_enrolled(self):
        """Test updating progress when not enrolled returns None."""
        result = ChallengeService.update_challenge_progress(
            self.user,
            self.challenge.id,
            50,
        )

        self.assertIsNone(result)

    def test_update_progress_already_completed(self):
        """Test updating completed challenge returns None."""
        UserChallengeFactory(
            user=self.user,
            challenge=self.challenge,
            status=UserChallenge.Status.COMPLETED,
        )

        result = ChallengeService.update_challenge_progress(
            self.user,
            self.challenge.id,
            50,
        )

        self.assertIsNone(result)


class TestChallengeServiceGetUserChallenges(TestCase):
    """Tests for ChallengeService.get_user_challenges."""

    def setUp(self):
        self.user = UserFactory()

    def test_get_user_challenges(self):
        """Test getting user's challenges."""
        active = ChallengeFactory()
        UserChallengeFactory(user=self.user, challenge=active)
        completed = ChallengeFactory()
        UserChallengeFactory(
            user=self.user,
            challenge=completed,
            status=UserChallenge.Status.COMPLETED,
            points_earned=50,
        )

        result = ChallengeService.get_user_challenges(self.user)

        self.assertEqual(len(result["active"]), 1)
        self.assertEqual(len(result["completed"]), 1)
        self.assertEqual(result["total_completed"], 1)
        self.assertEqual(result["total_points_earned"], 50)


# ============================================================================
# AchievementService Tests
# ============================================================================


class TestAchievementServiceCheckAchievements(TestCase):
    """Tests for AchievementService.check_achievements."""

    def setUp(self):
        self.user = UserFactory()
        PointCategoryFactory(slug="achievements")

    def test_check_achievements_points_milestone(self):
        """Test checking points milestone achievement."""
        achievement = AchievementFactory(
            criteria={"min_points": 100},
            points_reward=50,
        )
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.total_points = 150
        user_points.save()

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 1)
        self.assertTrue(
            UserAchievement.objects.filter(
                user=self.user,
                achievement=achievement,
            ).exists()
        )

    def test_check_achievements_not_met(self):
        """Test that unmet criteria don't unlock achievement."""
        AchievementFactory(criteria={"min_points": 1000})
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.total_points = 50
        user_points.save()

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 0)

    def test_check_achievements_already_unlocked(self):
        """Test that already unlocked achievements aren't duplicated."""
        achievement = AchievementFactory(criteria={"min_points": 100})
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.total_points = 150
        user_points.save()
        UserAchievementFactory(user=self.user, achievement=achievement)

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 0)

    def test_check_achievements_streak_milestone(self):
        """Test checking streak milestone achievement."""
        achievement = AchievementFactory(criteria={"min_streak": 7})
        user_points = UserPointsFactory(user=self.user)
        # Update streak after creation to ensure value persists
        user_points.current_streak = 10
        user_points.save()

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 1)

    def test_check_achievements_badge_count(self):
        """Test checking badge count achievement."""
        achievement = AchievementFactory(criteria={"min_badges": 5})
        UserPointsFactory(user=self.user)
        category = BadgeCategoryFactory()
        for _ in range(6):
            badge = BadgeFactory(category=category)
            UserBadgeFactory(user=self.user, badge=badge)

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 1)

    def test_check_achievements_repeatable(self):
        """Test that repeatable achievements can unlock multiple times."""
        achievement = AchievementFactory(
            criteria={"min_points": 100},
            is_repeatable=True,
        )
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.total_points = 150
        user_points.save()
        existing = UserAchievementFactory(user=self.user, achievement=achievement)

        result = AchievementService.check_achievements(self.user)

        self.assertEqual(len(result), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.times_unlocked, 2)


class TestAchievementServiceGetUserAchievements(TestCase):
    """Tests for AchievementService.get_user_achievements."""

    def setUp(self):
        self.user = UserFactory()

    def test_get_user_achievements_empty(self):
        """Test getting achievements for user with none."""
        result = AchievementService.get_user_achievements(self.user)

        self.assertEqual(result["total_unlocked"], 0)
        self.assertEqual(result["unlocked"], [])

    def test_get_user_achievements_with_achievements(self):
        """Test getting achievements for user with unlocked ones."""
        for _ in range(3):
            achievement = AchievementFactory()
            UserAchievementFactory(user=self.user, achievement=achievement)

        result = AchievementService.get_user_achievements(self.user)

        self.assertEqual(result["total_unlocked"], 3)

    def test_get_user_achievements_progress_percentage(self):
        """Test that progress percentage is correct."""
        # Create 4 achievements, unlock 2
        achievements = [AchievementFactory() for _ in range(4)]
        for i in range(2):
            UserAchievementFactory(user=self.user, achievement=achievements[i])

        result = AchievementService.get_user_achievements(self.user)

        self.assertEqual(result["progress_percentage"], 50)


# ============================================================================
# RewardService Tests
# ============================================================================


class TestRewardServiceGetAvailableRewards(TestCase):
    """Tests for RewardService.get_available_rewards."""

    def setUp(self):
        self.user = UserFactory()
        self.user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        self.user_points.available_points = 500
        self.user_points.save()

    def test_get_available_rewards(self):
        """Test getting available rewards."""
        RewardFactory(points_cost=100)
        RewardFactory(points_cost=200)
        RewardFactory(is_active=False)

        result = RewardService.get_available_rewards(self.user)

        self.assertEqual(len(result), 2)

    def test_get_available_rewards_shows_can_afford(self):
        """Test that can_afford is correctly set."""
        RewardFactory(points_cost=100)
        RewardFactory(points_cost=1000)

        result = RewardService.get_available_rewards(self.user)

        affordable = [r for r in result if r["can_afford"]]
        not_affordable = [r for r in result if not r["can_afford"]]

        self.assertEqual(len(affordable), 1)
        self.assertEqual(len(not_affordable), 1)

    def test_get_available_rewards_excludes_expired(self):
        """Test that expired rewards are excluded."""
        RewardFactory(points_cost=100)
        ExpiredRewardFactory(points_cost=100)

        result = RewardService.get_available_rewards(self.user)

        self.assertEqual(len(result), 1)

    def test_get_available_rewards_excludes_future(self):
        """Test that future rewards are excluded."""
        RewardFactory(points_cost=100)
        FutureRewardFactory(points_cost=100)

        result = RewardService.get_available_rewards(self.user)

        self.assertEqual(len(result), 1)

    def test_get_available_rewards_excludes_out_of_stock(self):
        """Test that out of stock rewards are excluded."""
        RewardFactory(points_cost=100)
        out_of_stock = LimitedRewardFactory(points_cost=100)
        out_of_stock.quantity_redeemed = out_of_stock.quantity_available
        out_of_stock.save()

        result = RewardService.get_available_rewards(self.user)

        self.assertEqual(len(result), 1)

    def test_get_available_rewards_level_requirement(self):
        """Test that level requirement is checked."""
        level = LevelFactory(number=5, min_points=500)
        RewardFactory(points_cost=100, min_level=level)

        # User has no level
        result = RewardService.get_available_rewards(self.user)

        self.assertEqual(len(result), 0)


class TestRewardServiceRedeemReward(TestCase):
    """Tests for RewardService.redeem_reward."""

    def setUp(self):
        self.user = UserFactory()
        self.user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        self.user_points.available_points = 500
        self.user_points.save()
        self.reward = RewardFactory(points_cost=100)
        PointCategoryFactory(slug="rewards")

    def test_redeem_reward_success(self):
        """Test redeeming a reward successfully."""
        redemption = RewardService.redeem_reward(self.user, self.reward.id)

        self.assertIsNotNone(redemption)
        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.reward, self.reward)
        self.assertEqual(redemption.points_spent, 100)

    def test_redeem_reward_deducts_points(self):
        """Test that points are deducted."""
        RewardService.redeem_reward(self.user, self.reward.id)

        self.user_points.refresh_from_db()
        self.assertEqual(self.user_points.available_points, 400)

    def test_redeem_reward_increments_quantity_redeemed(self):
        """Test that quantity_redeemed is incremented."""
        initial = self.reward.quantity_redeemed

        RewardService.redeem_reward(self.user, self.reward.id)

        self.reward.refresh_from_db()
        self.assertEqual(self.reward.quantity_redeemed, initial + 1)

    def test_redeem_reward_insufficient_points(self):
        """Test that insufficient points returns None."""
        self.user_points.available_points = 50
        self.user_points.save()

        result = RewardService.redeem_reward(self.user, self.reward.id)

        self.assertIsNone(result)

    def test_redeem_reward_non_existent(self):
        """Test redeeming non-existent reward."""
        result = RewardService.redeem_reward(self.user, 99999)

        self.assertIsNone(result)

    def test_redeem_reward_inactive(self):
        """Test redeeming inactive reward."""
        self.reward.is_active = False
        self.reward.save()

        result = RewardService.redeem_reward(self.user, self.reward.id)

        self.assertIsNone(result)

    def test_redeem_reward_out_of_stock(self):
        """Test redeeming out of stock reward."""
        limited = LimitedRewardFactory(quantity_available=1, quantity_redeemed=1)

        result = RewardService.redeem_reward(self.user, limited.id)

        self.assertIsNone(result)

    def test_redeem_reward_level_requirement_not_met(self):
        """Test redeeming with unmet level requirement."""
        level = LevelFactory(number=10, min_points=1000)
        self.reward.min_level = level
        self.reward.save()

        result = RewardService.redeem_reward(self.user, self.reward.id)

        self.assertIsNone(result)

    def test_redeem_reward_with_notes(self):
        """Test redeeming with notes."""
        redemption = RewardService.redeem_reward(
            self.user,
            self.reward.id,
            notes="Please deliver to office",
        )

        self.assertEqual(redemption.notes, "Please deliver to office")


class TestRewardServiceGetUserRedemptions(TestCase):
    """Tests for RewardService.get_user_redemptions."""

    def setUp(self):
        self.user = UserFactory()
        self.reward = RewardFactory()

    def test_get_user_redemptions_empty(self):
        """Test getting redemptions for user with none."""
        result = RewardService.get_user_redemptions(self.user)

        self.assertEqual(len(result), 0)

    def test_get_user_redemptions_with_redemptions(self):
        """Test getting redemptions for user with some."""
        from apps.gamification.tests.factories import RewardRedemptionFactory

        for _ in range(3):
            RewardRedemptionFactory(user=self.user, reward=self.reward)

        result = RewardService.get_user_redemptions(self.user)

        self.assertEqual(len(result), 3)


class TestRewardServiceFulfillRedemption(TestCase):
    """Tests for RewardService.fulfill_redemption."""

    def setUp(self):
        self.admin = AdminUserFactory()
        self.user = UserFactory()
        self.reward = RewardFactory()

    def test_fulfill_redemption_success(self):
        """Test fulfilling a redemption."""
        from apps.gamification.tests.factories import RewardRedemptionFactory

        redemption = RewardRedemptionFactory(
            user=self.user,
            reward=self.reward,
            status=RewardRedemption.Status.APPROVED,
        )

        result = RewardService.fulfill_redemption(
            redemption.id,
            fulfilled_by=self.admin,
            notes="Delivered",
        )

        self.assertTrue(result)
        redemption.refresh_from_db()
        self.assertEqual(redemption.status, RewardRedemption.Status.FULFILLED)
        self.assertEqual(redemption.fulfilled_by, self.admin)

    def test_fulfill_redemption_wrong_status(self):
        """Test fulfilling redemption with wrong status."""
        from apps.gamification.tests.factories import RewardRedemptionFactory

        redemption = RewardRedemptionFactory(
            user=self.user,
            reward=self.reward,
            status=RewardRedemption.Status.PENDING,
        )

        result = RewardService.fulfill_redemption(redemption.id, self.admin)

        self.assertFalse(result)

    def test_fulfill_redemption_non_existent(self):
        """Test fulfilling non-existent redemption."""
        result = RewardService.fulfill_redemption(99999, self.admin)

        self.assertFalse(result)


# ============================================================================
# GamificationDashboardService Tests
# ============================================================================


class TestGamificationDashboardService(TestCase):
    """Tests for GamificationDashboardService."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()
        PointCategoryFactory(slug="badges")

    def test_get_user_dashboard(self):
        """Test getting user dashboard data."""
        UserPointsFactory(user=self.user, total_points=100)
        badge = BadgeFactory(category=self.category)
        UserBadgeFactory(user=self.user, badge=badge)

        result = GamificationDashboardService.get_user_dashboard(self.user)

        self.assertIn("stats", result)
        self.assertIn("badges", result)
        self.assertIn("achievements", result)
        self.assertIn("challenges", result)
        self.assertIn("recent_transactions", result)

    def test_get_admin_analytics(self):
        """Test getting admin analytics."""
        # Create some test data
        category = PointCategoryFactory()
        for _ in range(3):
            user = UserFactory()
            PointTransactionFactory(user=user, category=category, points=100)

        result = GamificationDashboardService.get_admin_analytics()

        self.assertIn("points", result)
        self.assertIn("badges", result)
        self.assertIn("users", result)
        self.assertIn("challenges", result)
        self.assertEqual(result["users"]["active_this_week"], 3)
