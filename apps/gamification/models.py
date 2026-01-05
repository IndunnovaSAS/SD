"""
Gamification models for SD LMS.

Includes points, badges, levels, streaks, leaderboards, and challenges.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class PointCategory(BaseModel):
    """Category for different types of points."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="star")
    color = models.CharField(max_length=20, default="primary")
    multiplier = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "gamification_point_categories"
        verbose_name = "Point Category"
        verbose_name_plural = "Point Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PointTransaction(BaseModel):
    """Individual point transaction record."""

    class TransactionType(models.TextChoices):
        EARNED = "earned", "Earned"
        SPENT = "spent", "Spent"
        BONUS = "bonus", "Bonus"
        PENALTY = "penalty", "Penalty"
        ADJUSTMENT = "adjustment", "Adjustment"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
    )
    category = models.ForeignKey(
        PointCategory,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.EARNED,
    )
    points = models.IntegerField()
    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_point_transactions"
        verbose_name = "Point Transaction"
        verbose_name_plural = "Point Transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self):
        sign = "+" if self.points >= 0 else ""
        return f"{self.user.email}: {sign}{self.points} ({self.category.name})"


class Level(BaseModel):
    """User level definitions."""

    number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    min_points = models.PositiveIntegerField()
    max_points = models.PositiveIntegerField(null=True, blank=True)
    icon = models.CharField(max_length=50, default="trophy")
    color = models.CharField(max_length=20, default="primary")
    benefits = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "gamification_levels"
        verbose_name = "Level"
        verbose_name_plural = "Levels"
        ordering = ["number"]

    def __str__(self):
        return f"Level {self.number}: {self.name}"


class UserPoints(BaseModel):
    """Aggregated user points and level tracking."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gamification_points",
    )
    total_points = models.PositiveIntegerField(default=0)
    available_points = models.PositiveIntegerField(default=0)
    level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    weekly_points = models.PositiveIntegerField(default=0)
    monthly_points = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gamification_user_points"
        verbose_name = "User Points"
        verbose_name_plural = "User Points"

    def __str__(self):
        return f"{self.user.email}: {self.total_points} points (Level {self.level.number if self.level else 0})"

    def add_points(self, points: int, category: PointCategory, description: str, **kwargs):
        """Add points to user and create transaction."""
        adjusted_points = int(points * float(category.multiplier))

        PointTransaction.objects.create(
            user=self.user,
            category=category,
            transaction_type=PointTransaction.TransactionType.EARNED,
            points=adjusted_points,
            description=description,
            **kwargs,
        )

        self.total_points += adjusted_points
        self.available_points += adjusted_points
        self.weekly_points += adjusted_points
        self.monthly_points += adjusted_points
        self._update_streak()
        self._check_level_up()
        self.save()

        return adjusted_points

    def _update_streak(self):
        """Update activity streak."""
        today = timezone.now().date()

        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days
            if days_diff == 1:
                self.current_streak += 1
            elif days_diff > 1:
                self.current_streak = 1
        else:
            self.current_streak = 1

        self.longest_streak = max(self.longest_streak, self.current_streak)
        self.last_activity_date = today

    def _check_level_up(self):
        """Check and update user level based on points."""
        new_level = Level.objects.filter(
            min_points__lte=self.total_points
        ).order_by("-number").first()

        if new_level and (not self.level or new_level.number > self.level.number):
            self.level = new_level
            return True
        return False


class BadgeCategory(BaseModel):
    """Category for organizing badges."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="award")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gamification_badge_categories"
        verbose_name = "Badge Category"
        verbose_name_plural = "Badge Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Badge(BaseModel):
    """Achievement badge definitions."""

    class Rarity(models.TextChoices):
        COMMON = "common", "Common"
        UNCOMMON = "uncommon", "Uncommon"
        RARE = "rare", "Rare"
        EPIC = "epic", "Epic"
        LEGENDARY = "legendary", "Legendary"

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    category = models.ForeignKey(
        BadgeCategory,
        on_delete=models.CASCADE,
        related_name="badges",
    )
    icon = models.CharField(max_length=50, default="medal")
    image = models.ImageField(upload_to="badges/", null=True, blank=True)
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        default=Rarity.COMMON,
    )
    points_reward = models.PositiveIntegerField(default=0)
    criteria = models.JSONField(default=dict)
    is_secret = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    max_awards = models.PositiveIntegerField(null=True, blank=True)
    times_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gamification_badges"
        verbose_name = "Badge"
        verbose_name_plural = "Badges"
        ordering = ["category", "rarity", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"

    @property
    def rarity_color(self):
        """Get color for rarity level."""
        colors = {
            self.Rarity.COMMON: "gray",
            self.Rarity.UNCOMMON: "success",
            self.Rarity.RARE: "info",
            self.Rarity.EPIC: "secondary",
            self.Rarity.LEGENDARY: "warning",
        }
        return colors.get(self.rarity, "gray")


class UserBadge(BaseModel):
    """Badges earned by users."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="user_badges",
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    reference_type = models.CharField(max_length=100, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_user_badges"
        verbose_name = "User Badge"
        verbose_name_plural = "User Badges"
        ordering = ["-earned_at"]
        unique_together = ["user", "badge"]

    def __str__(self):
        return f"{self.user.email} - {self.badge.name}"


class Leaderboard(BaseModel):
    """Leaderboard configuration."""

    class Period(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        ALL_TIME = "all_time", "All Time"

    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        DEPARTMENT = "department", "Department"
        TEAM = "team", "Team"
        POSITION = "position", "Position"

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    period = models.CharField(
        max_length=20,
        choices=Period.choices,
        default=Period.WEEKLY,
    )
    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.GLOBAL,
    )
    point_category = models.ForeignKey(
        PointCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leaderboards",
    )
    max_entries = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    reset_date = models.DateField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_leaderboards"
        verbose_name = "Leaderboard"
        verbose_name_plural = "Leaderboards"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_period_display()})"


class LeaderboardEntry(BaseModel):
    """Entry in a leaderboard."""

    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries",
    )
    rank = models.PositiveIntegerField()
    points = models.PositiveIntegerField(default=0)
    previous_rank = models.PositiveIntegerField(null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_leaderboard_entries"
        verbose_name = "Leaderboard Entry"
        verbose_name_plural = "Leaderboard Entries"
        ordering = ["rank"]
        unique_together = ["leaderboard", "user", "period_start"]

    def __str__(self):
        return f"{self.leaderboard.name} - #{self.rank}: {self.user.email}"

    @property
    def rank_change(self):
        """Calculate rank change from previous position."""
        if self.previous_rank is None:
            return None
        return self.previous_rank - self.rank


class Challenge(BaseModel):
    """Time-limited challenge definitions."""

    class ChallengeType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        TEAM = "team", "Team"
        DEPARTMENT = "department", "Department"
        GLOBAL = "global", "Global"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    challenge_type = models.CharField(
        max_length=20,
        choices=ChallengeType.choices,
        default=ChallengeType.INDIVIDUAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    target_value = models.PositiveIntegerField()
    target_metric = models.CharField(max_length=100)
    points_reward = models.PositiveIntegerField(default=0)
    badge_reward = models.ForeignKey(
        Badge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="challenges",
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    criteria = models.JSONField(default=dict, blank=True)
    rules = models.TextField(blank=True)
    image = models.ImageField(upload_to="challenges/", null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_challenges"
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        """Check if challenge is currently active."""
        now = timezone.now()
        return (
            self.status == self.Status.ACTIVE
            and self.start_date <= now <= self.end_date
        )

    @property
    def progress_percentage(self):
        """Calculate time progress of challenge."""
        now = timezone.now()
        if now < self.start_date:
            return 0
        if now > self.end_date:
            return 100
        total_duration = (self.end_date - self.start_date).total_seconds()
        elapsed = (now - self.start_date).total_seconds()
        return int((elapsed / total_duration) * 100)


class UserChallenge(BaseModel):
    """User participation in challenges."""

    class Status(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        WITHDRAWN = "withdrawn", "Withdrawn"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="challenges",
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ENROLLED,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_value = models.PositiveIntegerField(default=0)
    progress_data = models.JSONField(default=dict, blank=True)
    points_earned = models.PositiveIntegerField(default=0)
    badge_earned = models.BooleanField(default=False)

    class Meta:
        db_table = "gamification_user_challenges"
        verbose_name = "User Challenge"
        verbose_name_plural = "User Challenges"
        ordering = ["-enrolled_at"]
        unique_together = ["user", "challenge"]

    def __str__(self):
        return f"{self.user.email} - {self.challenge.name}"

    @property
    def progress_percentage(self):
        """Calculate user's progress towards challenge goal."""
        if self.challenge.target_value == 0:
            return 100
        return min(100, int((self.current_value / self.challenge.target_value) * 100))

    def update_progress(self, value: int):
        """Update progress and check completion."""
        self.current_value += value

        if self.status == self.Status.ENROLLED:
            self.status = self.Status.IN_PROGRESS

        if self.current_value >= self.challenge.target_value:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()

        self.save()


class Achievement(BaseModel):
    """Predefined achievements that users can unlock."""

    class AchievementType(models.TextChoices):
        MILESTONE = "milestone", "Milestone"
        STREAK = "streak", "Streak"
        COMPLETION = "completion", "Completion"
        SOCIAL = "social", "Social"
        SPECIAL = "special", "Special"

    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    achievement_type = models.CharField(
        max_length=20,
        choices=AchievementType.choices,
        default=AchievementType.MILESTONE,
    )
    icon = models.CharField(max_length=50, default="star")
    points_reward = models.PositiveIntegerField(default=0)
    badge = models.ForeignKey(
        Badge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="achievements",
    )
    criteria = models.JSONField(default=dict)
    is_repeatable = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "gamification_achievements"
        verbose_name = "Achievement"
        verbose_name_plural = "Achievements"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class UserAchievement(BaseModel):
    """Achievements unlocked by users."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="user_achievements",
    )
    unlocked_at = models.DateTimeField(auto_now_add=True)
    times_unlocked = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_user_achievements"
        verbose_name = "User Achievement"
        verbose_name_plural = "User Achievements"
        ordering = ["-unlocked_at"]
        unique_together = ["user", "achievement"]

    def __str__(self):
        return f"{self.user.email} - {self.achievement.name}"


class Reward(BaseModel):
    """Rewards that can be redeemed with points."""

    class RewardType(models.TextChoices):
        PHYSICAL = "physical", "Physical"
        DIGITAL = "digital", "Digital"
        EXPERIENCE = "experience", "Experience"
        RECOGNITION = "recognition", "Recognition"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    reward_type = models.CharField(
        max_length=20,
        choices=RewardType.choices,
        default=RewardType.DIGITAL,
    )
    points_cost = models.PositiveIntegerField()
    quantity_available = models.PositiveIntegerField(null=True, blank=True)
    quantity_redeemed = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="rewards/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    min_level = models.ForeignKey(
        Level,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewards",
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_rewards"
        verbose_name = "Reward"
        verbose_name_plural = "Rewards"
        ordering = ["points_cost", "name"]

    def __str__(self):
        return f"{self.name} ({self.points_cost} pts)"

    @property
    def is_available(self):
        """Check if reward is currently available."""
        if not self.is_active:
            return False
        if self.quantity_available is not None:
            if self.quantity_redeemed >= self.quantity_available:
                return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True


class RewardRedemption(BaseModel):
    """Record of reward redemptions."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        FULFILLED = "fulfilled", "Fulfilled"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reward_redemptions",
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    points_spent = models.PositiveIntegerField()
    redeemed_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfilled_redemptions",
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "gamification_reward_redemptions"
        verbose_name = "Reward Redemption"
        verbose_name_plural = "Reward Redemptions"
        ordering = ["-redeemed_at"]

    def __str__(self):
        return f"{self.user.email} - {self.reward.name}"
