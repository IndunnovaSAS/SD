"""
Gamification services package.

Re-exports all service classes for backward compatibility.
Allows imports like: from apps.gamification.services import PointService
"""

from apps.gamification.services.achievements import AchievementService
from apps.gamification.services.badges import BadgeService
from apps.gamification.services.challenges import ChallengeService
from apps.gamification.services.dashboard import GamificationDashboardService
from apps.gamification.services.leaderboards import LeaderboardService
from apps.gamification.services.points import PointService
from apps.gamification.services.rewards import RewardService

__all__ = [
    "PointService",
    "BadgeService",
    "LeaderboardService",
    "ChallengeService",
    "AchievementService",
    "RewardService",
    "GamificationDashboardService",
]
