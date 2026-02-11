"""
Serializers for assessments API.
"""

from rest_framework import serializers

from apps.assessments.models import (
    Answer,
    Assessment,
    AssessmentAttempt,
    AttemptAnswer,
    Question,
)


class AnswerSerializer(serializers.ModelSerializer):
    """Serializer for Answer model."""

    class Meta:
        model = Answer
        fields = ["id", "text", "order", "feedback"]
        read_only_fields = ["id"]


class AnswerWithCorrectSerializer(serializers.ModelSerializer):
    """Serializer for Answer with correct answer info (for review)."""

    class Meta:
        model = Answer
        fields = ["id", "text", "is_correct", "order", "feedback"]
        read_only_fields = ["id"]


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for Question model."""

    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_type",
            "text",
            "points",
            "order",
            "image",
            "answers",
        ]
        read_only_fields = ["id"]


class QuestionWithAnswersSerializer(serializers.ModelSerializer):
    """Serializer for Question with correct answers (for review)."""

    answers = AnswerWithCorrectSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_type",
            "text",
            "explanation",
            "points",
            "order",
            "image",
            "answers",
        ]
        read_only_fields = ["id"]


class QuestionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating questions with answers."""

    answers = AnswerSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "question_type",
            "text",
            "explanation",
            "points",
            "order",
            "image",
            "answers",
        ]

    def create(self, validated_data):
        answers_data = validated_data.pop("answers", [])
        question = Question.objects.create(**validated_data)
        for answer_data in answers_data:
            Answer.objects.create(question=question, **answer_data)
        return question


class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for Assessment model."""

    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.ReadOnlyField()
    total_points = serializers.ReadOnlyField()
    course_title = serializers.CharField(source="course.title", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    user_attempts = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "description",
            "assessment_type",
            "course",
            "course_title",
            "lesson",
            "passing_score",
            "time_limit",
            "max_attempts",
            "shuffle_questions",
            "shuffle_answers",
            "show_correct_answers",
            "status",
            "total_questions",
            "total_points",
            "questions",
            "created_by",
            "created_by_name",
            "user_attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_user_attempts(self, obj):
        """Get number of attempts by current user."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.attempts.filter(user=request.user).count()


class AssessmentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for assessment lists."""

    total_questions = serializers.ReadOnlyField()
    course_title = serializers.CharField(source="course.title", read_only=True)
    user_best_score = serializers.SerializerMethodField()
    user_passed = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "assessment_type",
            "course",
            "course_title",
            "passing_score",
            "time_limit",
            "max_attempts",
            "status",
            "total_questions",
            "user_best_score",
            "user_passed",
        ]

    def get_user_best_score(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        best_attempt = (
            obj.attempts.filter(user=request.user, status=AssessmentAttempt.Status.GRADED)
            .order_by("-score")
            .first()
        )
        return float(best_attempt.score) if best_attempt else None

    def get_user_passed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return obj.attempts.filter(user=request.user, passed=True).exists()


class AssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assessments."""

    class Meta:
        model = Assessment
        fields = [
            "title",
            "description",
            "assessment_type",
            "course",
            "lesson",
            "passing_score",
            "time_limit",
            "max_attempts",
            "shuffle_questions",
            "shuffle_answers",
            "show_correct_answers",
        ]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class AttemptAnswerSerializer(serializers.ModelSerializer):
    """Serializer for AttemptAnswer model."""

    question_text = serializers.CharField(source="question.text", read_only=True)
    question_type = serializers.CharField(source="question.question_type", read_only=True)

    class Meta:
        model = AttemptAnswer
        fields = [
            "id",
            "question",
            "question_text",
            "question_type",
            "selected_answers",
            "text_answer",
            "is_correct",
            "points_awarded",
            "feedback",
            "answered_at",
        ]
        read_only_fields = ["id", "is_correct", "points_awarded", "feedback", "answered_at"]


class AttemptAnswerSubmitSerializer(serializers.Serializer):
    """Serializer for submitting an answer."""

    question_id = serializers.IntegerField()
    selected_answer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=[],
    )
    text_answer = serializers.CharField(required=False, allow_blank=True, default="")


class AssessmentAttemptSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentAttempt model."""

    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    attempt_answers = AttemptAnswerSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentAttempt
        fields = [
            "id",
            "user",
            "user_name",
            "assessment",
            "assessment_title",
            "status",
            "attempt_number",
            "score",
            "points_earned",
            "passed",
            "time_spent",
            "started_at",
            "submitted_at",
            "graded_at",
            "attempt_answers",
        ]
        read_only_fields = [
            "id",
            "user",
            "attempt_number",
            "score",
            "points_earned",
            "passed",
            "started_at",
            "submitted_at",
            "graded_at",
        ]

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class AssessmentAttemptListSerializer(serializers.ModelSerializer):
    """Simplified serializer for attempt lists."""

    assessment_title = serializers.CharField(source="assessment.title", read_only=True)

    class Meta:
        model = AssessmentAttempt
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "status",
            "attempt_number",
            "score",
            "passed",
            "time_spent",
            "started_at",
            "submitted_at",
        ]


class StartAttemptSerializer(serializers.Serializer):
    """Serializer for starting an assessment attempt."""

    assessment_id = serializers.IntegerField()


class SubmitAttemptSerializer(serializers.Serializer):
    """Serializer for submitting an assessment attempt."""

    answers = AttemptAnswerSubmitSerializer(many=True)
    time_spent = serializers.IntegerField(required=False, default=0)
