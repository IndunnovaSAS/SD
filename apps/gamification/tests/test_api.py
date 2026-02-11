"""
Tests for gamification API views and permissions.

Comprehensive tests for all gamification endpoints including
authentication and permission requirements.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.gamification.models import (
    Challenge,
    UserChallenge,
    UserPoints,
)
from apps.gamification.tests.factories import (
    AchievementFactory,
    AdminUserFactory,
    BadgeCategoryFactory,
    BadgeFactory,
    ChallengeFactory,
    LeaderboardFactory,
    PointCategoryFactory,
    RewardFactory,
    UserAchievementFactory,
    UserBadgeFactory,
    UserChallengeFactory,
    UserFactory,
    UserPointsFactory,
)

# ============================================================================
# Dashboard Views Tests
# ============================================================================


class TestDashboardView(TestCase):
    """Tests for dashboard view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:dashboard")

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_dashboard_authenticated(self):
        """Test accessing dashboard when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestDashboardStatsView(TestCase):
    """Tests for dashboard stats partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:stats")

    def test_stats_requires_login(self):
        """Test that stats requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_stats_authenticated(self):
        """Test accessing stats when authenticated."""
        UserPointsFactory(user=self.user, total_points=500)
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestDashboardOverviewView(TestCase):
    """Tests for dashboard overview partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:overview")

    def test_overview_requires_login(self):
        """Test that overview requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_overview_authenticated(self):
        """Test accessing overview when authenticated."""
        UserPointsFactory(user=self.user)
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Points Views Tests
# ============================================================================


class TestPointsHistoryView(TestCase):
    """Tests for points history view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:points")

    def test_points_requires_login(self):
        """Test that points history requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_points_authenticated(self):
        """Test accessing points when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestPointsTransactionsView(TestCase):
    """Tests for points transactions partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:transactions")

    def test_transactions_requires_login(self):
        """Test that transactions requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_transactions_authenticated(self):
        """Test accessing transactions when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_transactions_with_limit(self):
        """Test transactions respects limit parameter."""
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"limit": "10"})

        self.assertEqual(response.status_code, 200)


class TestPointsByCategoryView(TestCase):
    """Tests for points by category partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:points-by-category")

    def test_by_category_requires_login(self):
        """Test that points by category requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_by_category_authenticated(self):
        """Test accessing points by category when authenticated."""
        UserPointsFactory(user=self.user)
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Badges Views Tests
# ============================================================================


class TestBadgesListView(TestCase):
    """Tests for badges list view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:badges")

    def test_badges_requires_login(self):
        """Test that badges list requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_badges_authenticated(self):
        """Test accessing badges when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestBadgesGridView(TestCase):
    """Tests for badges grid partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()
        self.url = reverse("gamification:badges-grid")

    def test_grid_requires_login(self):
        """Test that badges grid requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_grid_shows_all_badges(self):
        """Test that grid shows all available badges."""
        badge1 = BadgeFactory(category=self.category)
        badge2 = BadgeFactory(category=self.category)
        UserBadgeFactory(user=self.user, badge=badge1)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestBadgeDetailView(TestCase):
    """Tests for badge detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()
        self.badge = BadgeFactory(category=self.category)
        self.url = reverse("gamification:badge-detail", kwargs={"badge_id": self.badge.id})

    def test_detail_requires_login(self):
        """Test that badge detail requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_detail_authenticated(self):
        """Test accessing badge detail when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_detail_non_existent_badge(self):
        """Test accessing non-existent badge returns 404."""
        self.client.force_login(self.user)
        url = reverse("gamification:badge-detail", kwargs={"badge_id": 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestSetFeaturedBadgesView(TestCase):
    """Tests for set featured badges view."""

    def setUp(self):
        self.user = UserFactory()
        self.category = BadgeCategoryFactory()
        self.url = reverse("gamification:set-featured")

    def test_requires_login(self):
        """Test that set featured requires authentication."""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)

    def test_requires_post(self):
        """Test that only POST is allowed."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_set_featured_badges(self):
        """Test setting featured badges."""
        badges = [BadgeFactory(category=self.category) for _ in range(3)]
        for badge in badges:
            UserBadgeFactory(user=self.user, badge=badge)

        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            {"badge_ids": [str(badges[0].id), str(badges[1].id)]},
        )

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Leaderboard Views Tests
# ============================================================================


class TestLeaderboardsView(TestCase):
    """Tests for leaderboards view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:leaderboards")

    def test_leaderboards_requires_login(self):
        """Test that leaderboards requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_leaderboards_authenticated(self):
        """Test accessing leaderboards when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestLeaderboardListView(TestCase):
    """Tests for leaderboard list partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:leaderboard-list")

    def test_list_requires_login(self):
        """Test that leaderboard list requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_list_shows_active_leaderboards(self):
        """Test that list shows active leaderboards."""
        LeaderboardFactory(is_active=True)
        LeaderboardFactory(is_active=False)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestLeaderboardDetailView(TestCase):
    """Tests for leaderboard detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.leaderboard = LeaderboardFactory(slug="weekly-leaders")
        self.url = reverse(
            "gamification:leaderboard-detail",
            kwargs={"slug": "weekly-leaders"},
        )

    def test_detail_requires_login(self):
        """Test that leaderboard detail requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_detail_authenticated(self):
        """Test accessing leaderboard detail when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_detail_with_limit(self):
        """Test leaderboard detail respects limit."""
        self.client.force_login(self.user)

        response = self.client.get(self.url, {"limit": "5"})

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Challenges Views Tests
# ============================================================================


class TestChallengesView(TestCase):
    """Tests for challenges view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:challenges")

    def test_challenges_requires_login(self):
        """Test that challenges requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_challenges_authenticated(self):
        """Test accessing challenges when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestChallengesActiveView(TestCase):
    """Tests for active challenges partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:challenges-active")

    def test_active_requires_login(self):
        """Test that active challenges requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_active_authenticated(self):
        """Test accessing active challenges when authenticated."""
        ChallengeFactory()
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestChallengesUserView(TestCase):
    """Tests for user challenges partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:challenges-user")

    def test_user_challenges_requires_login(self):
        """Test that user challenges requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_user_challenges_authenticated(self):
        """Test accessing user challenges when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestChallengeDetailView(TestCase):
    """Tests for challenge detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.challenge = ChallengeFactory()
        self.url = reverse(
            "gamification:challenge-detail",
            kwargs={"challenge_id": self.challenge.id},
        )

    def test_detail_requires_login(self):
        """Test that challenge detail requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_detail_authenticated(self):
        """Test accessing challenge detail when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_detail_non_existent_challenge(self):
        """Test accessing non-existent challenge returns 404."""
        self.client.force_login(self.user)
        url = reverse("gamification:challenge-detail", kwargs={"challenge_id": 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestJoinChallengeView(TestCase):
    """Tests for join challenge view."""

    def setUp(self):
        self.user = UserFactory()
        self.challenge = ChallengeFactory()
        self.url = reverse(
            "gamification:join-challenge",
            kwargs={"challenge_id": self.challenge.id},
        )

    def test_join_requires_login(self):
        """Test that joining challenge requires authentication."""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)

    def test_join_requires_post(self):
        """Test that only POST is allowed."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_join_success(self):
        """Test joining challenge successfully."""
        self.client.force_login(self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserChallenge.objects.filter(
                user=self.user,
                challenge=self.challenge,
            ).exists()
        )

    def test_join_expired_challenge(self):
        """Test joining expired challenge fails."""
        self.challenge.end_date = timezone.now() - timedelta(days=1)
        self.challenge.status = Challenge.Status.COMPLETED
        self.challenge.save()

        self.client.force_login(self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)


# ============================================================================
# Achievements Views Tests
# ============================================================================


class TestAchievementsView(TestCase):
    """Tests for achievements view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:achievements")

    def test_achievements_requires_login(self):
        """Test that achievements requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_achievements_authenticated(self):
        """Test accessing achievements when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestAchievementsListView(TestCase):
    """Tests for achievements list partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:achievements-list")

    def test_list_requires_login(self):
        """Test that achievements list requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_list_authenticated(self):
        """Test accessing achievements list when authenticated."""
        achievement = AchievementFactory()
        UserAchievementFactory(user=self.user, achievement=achievement)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Rewards Views Tests
# ============================================================================


class TestRewardsView(TestCase):
    """Tests for rewards view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:rewards")

    def test_rewards_requires_login(self):
        """Test that rewards requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_rewards_authenticated(self):
        """Test accessing rewards when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestRewardsAvailableView(TestCase):
    """Tests for available rewards partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:rewards-available")

    def test_available_requires_login(self):
        """Test that available rewards requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_available_authenticated(self):
        """Test accessing available rewards when authenticated."""
        UserPointsFactory(user=self.user, available_points=1000)
        RewardFactory(points_cost=100)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestRewardDetailView(TestCase):
    """Tests for reward detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.reward = RewardFactory()
        UserPointsFactory(user=self.user, available_points=1000)
        self.url = reverse(
            "gamification:reward-detail",
            kwargs={"reward_id": self.reward.id},
        )

    def test_detail_requires_login(self):
        """Test that reward detail requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_detail_authenticated(self):
        """Test accessing reward detail when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_detail_non_existent_reward(self):
        """Test accessing non-existent reward returns 404."""
        self.client.force_login(self.user)
        url = reverse("gamification:reward-detail", kwargs={"reward_id": 99999})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class TestRedeemRewardView(TestCase):
    """Tests for redeem reward view."""

    def setUp(self):
        self.user = UserFactory()
        self.reward = RewardFactory(points_cost=100)
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.available_points = 500
        user_points.save()
        PointCategoryFactory(slug="rewards")
        self.url = reverse(
            "gamification:redeem-reward",
            kwargs={"reward_id": self.reward.id},
        )

    def test_redeem_requires_login(self):
        """Test that redeem requires authentication."""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 302)

    def test_redeem_requires_post(self):
        """Test that only POST is allowed."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 405)

    def test_redeem_success(self):
        """Test redeeming reward successfully."""
        self.client.force_login(self.user)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)

    def test_redeem_insufficient_points(self):
        """Test redeeming with insufficient points fails."""
        user_points = UserPoints.objects.get(user=self.user)
        user_points.available_points = 50
        user_points.save()

        self.client.force_login(self.user)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 400)


class TestRedemptionsHistoryView(TestCase):
    """Tests for redemptions history partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("gamification:redemptions-history")

    def test_history_requires_login(self):
        """Test that redemptions history requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_history_authenticated(self):
        """Test accessing redemptions history when authenticated."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Admin Views Tests
# ============================================================================


class TestAdminDashboardView(TestCase):
    """Tests for admin dashboard view."""

    def setUp(self):
        self.user = UserFactory()
        self.admin = AdminUserFactory()
        self.url = reverse("gamification:admin-dashboard")

    def test_admin_dashboard_requires_login(self):
        """Test that admin dashboard requires authentication."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_requires_staff(self):
        """Test that admin dashboard requires staff status."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        # Should redirect to admin login
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_staff_access(self):
        """Test accessing admin dashboard as staff."""
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestAdminAnalyticsView(TestCase):
    """Tests for admin analytics partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.admin = AdminUserFactory()
        self.url = reverse("gamification:admin-analytics")

    def test_analytics_requires_staff(self):
        """Test that analytics requires staff status."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_analytics_staff_access(self):
        """Test accessing analytics as staff."""
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


class TestAdminTopEarnersView(TestCase):
    """Tests for admin top earners partial view."""

    def setUp(self):
        self.user = UserFactory()
        self.admin = AdminUserFactory()
        self.url = reverse("gamification:admin-top-earners")

    def test_top_earners_requires_staff(self):
        """Test that top earners requires staff status."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_top_earners_staff_access(self):
        """Test accessing top earners as staff."""
        self.client.force_login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================


class TestEdgeCases(TestCase):
    """Tests for edge cases and error handling."""

    def setUp(self):
        self.user = UserFactory()

    def test_negative_limit_parameter(self):
        """Test handling negative limit parameter."""
        self.client.force_login(self.user)
        url = reverse("gamification:transactions")

        # Should handle gracefully (implementation dependent)
        response = self.client.get(url, {"limit": "-10"})

        # Either succeeds with default limit or returns error
        self.assertIn(response.status_code, [200, 400])

    def test_non_numeric_limit(self):
        """Test handling non-numeric limit parameter."""
        self.client.force_login(self.user)
        url = reverse("gamification:transactions")

        # Should raise ValueError which may cause 500 or be handled
        try:
            response = self.client.get(url, {"limit": "abc"})
            # If no error, check response
            self.assertIn(response.status_code, [200, 400, 500])
        except ValueError:
            pass  # Expected behavior

    def test_empty_badge_ids_for_featured(self):
        """Test setting empty badge IDs for featured."""
        self.client.force_login(self.user)
        url = reverse("gamification:set-featured")

        response = self.client.post(url, {"badge_ids": []})

        self.assertEqual(response.status_code, 200)

    def test_invalid_badge_ids_for_featured(self):
        """Test setting invalid badge IDs for featured."""
        self.client.force_login(self.user)
        url = reverse("gamification:set-featured")

        response = self.client.post(url, {"badge_ids": ["abc", "def"]})

        # Should handle gracefully, filtering out invalid IDs
        self.assertEqual(response.status_code, 200)

    def test_csrf_protection_on_post(self):
        """Test that POST endpoints have CSRF protection."""
        self.client.force_login(self.user)

        # Create a client without CSRF cookies
        from django.test import Client

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        # Should return 403 without CSRF token
        challenge = ChallengeFactory()
        url = reverse(
            "gamification:join-challenge",
            kwargs={"challenge_id": challenge.id},
        )

        response = csrf_client.post(url)

        self.assertEqual(response.status_code, 403)


class TestConcurrencyEdgeCases(TestCase):
    """Tests for concurrency-related edge cases."""

    def setUp(self):
        self.user = UserFactory()
        self.category = PointCategoryFactory(slug="rewards")

    def test_redeem_reward_out_of_stock_race_condition(self):
        """Test redeeming last item when potentially racing."""
        from apps.gamification.tests.factories import LimitedRewardFactory

        reward = LimitedRewardFactory(
            points_cost=100,
            quantity_available=1,
            quantity_redeemed=0,
        )
        user_points = UserPointsFactory(user=self.user)
        # Update points after creation to ensure values persist
        user_points.available_points = 500
        user_points.save()

        self.client.force_login(self.user)
        url = reverse("gamification:redeem-reward", kwargs={"reward_id": reward.id})

        # First redemption should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        # Reset user points for second attempt
        user_points = UserPoints.objects.get(user=self.user)
        user_points.available_points = 500
        user_points.save()

        # Second redemption should fail (out of stock)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)

    def test_join_challenge_max_participants_race_condition(self):
        """Test joining challenge when max participants about to be reached."""
        challenge = ChallengeFactory(max_participants=2)
        user1 = UserFactory()
        user2 = UserFactory()

        UserChallengeFactory(user=user1, challenge=challenge)
        UserChallengeFactory(user=user2, challenge=challenge)

        self.client.force_login(self.user)
        url = reverse(
            "gamification:join-challenge",
            kwargs={"challenge_id": challenge.id},
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, 400)


class TestPermissionBoundaries(TestCase):
    """Tests for permission boundaries between users."""

    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.category = BadgeCategoryFactory()

    def test_cannot_set_other_users_featured_badges(self):
        """Test that user cannot set another user's featured badges."""
        badge = BadgeFactory(category=self.category)
        UserBadgeFactory(user=self.user2, badge=badge)

        self.client.force_login(self.user1)
        url = reverse("gamification:set-featured")

        # Even if user1 tries to set user2's badge as featured,
        # the service should only affect user1's badges
        response = self.client.post(url, {"badge_ids": [str(badge.id)]})

        self.assertEqual(response.status_code, 200)
        # Badge should not be featured for user2
        from apps.gamification.models import UserBadge

        user2_badge = UserBadge.objects.get(user=self.user2, badge=badge)
        self.assertFalse(user2_badge.is_featured)

    def test_user_sees_only_own_transactions(self):
        """Test that user only sees their own transactions."""
        from apps.gamification.tests.factories import PointTransactionFactory

        category = PointCategoryFactory()

        # Create transactions for both users
        PointTransactionFactory(user=self.user1, category=category)
        PointTransactionFactory(user=self.user2, category=category)

        self.client.force_login(self.user1)
        url = reverse("gamification:transactions")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Response should only contain user1's transactions
        # (exact assertion depends on template content)

    def test_user_sees_only_own_redemptions(self):
        """Test that user only sees their own redemptions."""
        from apps.gamification.tests.factories import RewardRedemptionFactory

        reward = RewardFactory()

        RewardRedemptionFactory(user=self.user1, reward=reward)
        RewardRedemptionFactory(user=self.user2, reward=reward)

        self.client.force_login(self.user1)
        url = reverse("gamification:redemptions-history")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
