"""
Reward service for gamification.

Handles all reward-related operations including redemption and fulfillment.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.gamification.models import (
    Reward,
    RewardRedemption,
)


class RewardService:
    """Service for managing rewards."""

    @staticmethod
    def get_available_rewards(user) -> list:
        """Get rewards available to user."""
        from apps.gamification.services.points import PointService

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
        from apps.gamification.services.points import PointService

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
