"""
Leaderboard service for gamification.

Handles all leaderboard-related operations including rankings and updates.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.gamification.models import (
    Leaderboard,
    LeaderboardEntry,
    PointTransaction,
    UserPoints,
)


class LeaderboardService:
    """Service for managing leaderboards."""

    @staticmethod
    def get_leaderboard_entries(
        leaderboard_slug: str,
        limit: int = 10,
        user=None,
    ) -> dict:
        """Get leaderboard entries with optional user position."""
        leaderboard = Leaderboard.objects.filter(slug=leaderboard_slug, is_active=True).first()

        if not leaderboard:
            return {"entries": [], "user_rank": None, "leaderboard": None}

        entries = (
            LeaderboardEntry.objects.filter(leaderboard=leaderboard)
            .select_related("user")
            .order_by("rank")[:limit]
        )

        user_rank = None
        if user:
            user_entry = LeaderboardEntry.objects.filter(leaderboard=leaderboard, user=user).first()
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
        leaderboard = Leaderboard.objects.filter(slug=leaderboard_slug, is_active=True).first()

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
