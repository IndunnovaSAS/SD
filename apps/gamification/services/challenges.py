"""
Challenge service for gamification.

Handles all challenge-related operations including joining, progress tracking, and rewards.
"""

from django.utils import timezone

from apps.gamification.models import (
    Challenge,
    UserChallenge,
)


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
                participation = UserChallenge.objects.filter(user=user, challenge=challenge).first()
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
        user_challenge = (
            UserChallenge.objects.filter(
                user=user,
                challenge_id=challenge_id,
                status__in=[UserChallenge.Status.ENROLLED, UserChallenge.Status.IN_PROGRESS],
            )
            .select_related("challenge")
            .first()
        )

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
        from apps.gamification.services.badges import BadgeService
        from apps.gamification.services.points import PointService

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

        # Active = Challenge is active AND UserChallenge is not completed/failed
        active = [
            c
            for c in challenges
            if c.challenge.is_active
            and c.status not in [UserChallenge.Status.COMPLETED, UserChallenge.Status.FAILED]
        ]
        completed = [c for c in challenges if c.status == UserChallenge.Status.COMPLETED]
        failed = [c for c in challenges if c.status == UserChallenge.Status.FAILED]

        return {
            "active": active,
            "completed": completed,
            "failed": failed,
            "total_completed": len(completed),
            "total_points_earned": sum(c.points_earned for c in completed),
        }
