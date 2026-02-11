"""
Signals for gamification app.

Automatically award points and badges based on user actions.
"""

from django.db.models.signals import post_save

from apps.gamification.services import BadgeService, PointService

# Point category slugs
CATEGORY_TRAINING = "training"
CATEGORY_SAFETY = "safety"
CATEGORY_COLLABORATION = "collaboration"
CATEGORY_ENGAGEMENT = "engagement"


def award_course_completion_points(sender, instance, created, **kwargs):
    """Award points when user completes a course."""
    if instance.status == "completed" and instance.completed_at:
        PointService.award_points(
            user=instance.user,
            points=100,
            category_slug=CATEGORY_TRAINING,
            description=f"Completed course: {instance.course.title}",
            reference_type="course",
            reference_id=instance.course.id,
        )

        # Check for first course badge
        from apps.courses.models import Enrollment

        completed_count = Enrollment.objects.filter(user=instance.user, status="completed").count()

        if completed_count == 1:
            BadgeService.award_badge(
                user=instance.user,
                badge_slug="first-course",
                reference_type="course",
                reference_id=instance.course.id,
            )
        elif completed_count == 10:
            BadgeService.award_badge(
                user=instance.user,
                badge_slug="course-expert",
                reference_type="course",
                reference_id=instance.course.id,
            )


def award_assessment_completion_points(sender, instance, created, **kwargs):
    """Award points when user completes an assessment."""
    if instance.status == "completed" and instance.score is not None:
        base_points = 50

        # Bonus for high scores
        if instance.score >= 90:
            base_points = 100
            BadgeService.award_badge(
                user=instance.user,
                badge_slug="assessment-ace",
                reference_type="assessment",
                reference_id=instance.assessment.id,
            )
        elif instance.score >= 80:
            base_points = 75

        PointService.award_points(
            user=instance.user,
            points=base_points,
            category_slug=CATEGORY_TRAINING,
            description=f"Assessment completed: {instance.assessment.title} ({instance.score}%)",
            reference_type="assessment",
            reference_id=instance.assessment.id,
        )


def award_certification_points(sender, instance, created, **kwargs):
    """Award points when user earns a certification."""
    if created:
        PointService.award_points(
            user=instance.user,
            points=200,
            category_slug=CATEGORY_TRAINING,
            description=f"Certification earned: {instance.certification.name}",
            reference_type="certification",
            reference_id=instance.certification.id,
        )

        # Award certification badge
        BadgeService.award_badge(
            user=instance.user,
            badge_slug="certified",
            reference_type="certification",
            reference_id=instance.certification.id,
        )


def award_lesson_learned_points(sender, instance, **kwargs):
    """Award points when lesson learned is approved."""
    if instance.status == "approved" and instance.created_by:
        PointService.award_points(
            user=instance.created_by,
            points=75,
            category_slug=CATEGORY_COLLABORATION,
            description=f"Lesson learned approved: {instance.title}",
            reference_type="lesson_learned",
            reference_id=instance.id,
        )

        # Check for first contribution badge
        from apps.lessons_learned.models import LessonLearned

        approved_count = LessonLearned.objects.filter(
            created_by=instance.created_by, status="approved"
        ).count()

        if approved_count == 1:
            BadgeService.award_badge(
                user=instance.created_by,
                badge_slug="first-contribution",
                reference_type="lesson_learned",
                reference_id=instance.id,
            )


def award_preop_talk_points(sender, instance, **kwargs):
    """Award points for conducting preop talks."""
    if instance.status == "completed" and instance.completed_at:
        # Award points to conductor
        PointService.award_points(
            user=instance.conducted_by,
            points=50,
            category_slug=CATEGORY_SAFETY,
            description=f"Preop talk conducted: {instance.topic}",
            reference_type="preop_talk",
            reference_id=instance.id,
        )


def award_attendance_points(sender, instance, **kwargs):
    """Award points for attending a preop talk."""
    if instance.attended and instance.signature:
        PointService.award_points(
            user=instance.user,
            points=25,
            category_slug=CATEGORY_SAFETY,
            description=f"Attended preop talk: {instance.talk.topic}",
            reference_type="preop_talk_attendance",
            reference_id=instance.id,
        )


def connect_gamification_signals():
    """
    Connect gamification signals to relevant models.

    Call this from apps.gamification.apps.GamificationConfig.ready()
    """
    try:
        from apps.courses.models import Enrollment

        post_save.connect(
            award_course_completion_points,
            sender=Enrollment,
            dispatch_uid="gamification_course_completion",
        )
    except ImportError:
        pass

    try:
        from apps.assessments.models import AssessmentAttempt

        post_save.connect(
            award_assessment_completion_points,
            sender=AssessmentAttempt,
            dispatch_uid="gamification_assessment_completion",
        )
    except ImportError:
        pass

    try:
        from apps.certifications.models import UserCertification

        post_save.connect(
            award_certification_points,
            sender=UserCertification,
            dispatch_uid="gamification_certification",
        )
    except ImportError:
        pass

    try:
        from apps.lessons_learned.models import LessonLearned

        post_save.connect(
            award_lesson_learned_points,
            sender=LessonLearned,
            dispatch_uid="gamification_lesson_learned",
        )
    except ImportError:
        pass

    try:
        from apps.preop_talks.models import PreOpTalk, TalkAttendee

        post_save.connect(
            award_preop_talk_points,
            sender=PreOpTalk,
            dispatch_uid="gamification_preop_talk",
        )
        post_save.connect(
            award_attendance_points,
            sender=TalkAttendee,
            dispatch_uid="gamification_attendance",
        )
    except ImportError:
        pass


# Connect signals when module is imported
connect_gamification_signals()
