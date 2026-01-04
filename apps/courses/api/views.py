"""
API views for courses app.
"""

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import (
    Category,
    Course,
    Enrollment,
    Lesson,
    LessonProgress,
    MediaAsset,
    Module,
)

from .serializers import (
    BulkEnrollmentSerializer,
    CategoryListSerializer,
    CategorySerializer,
    CourseCreateSerializer,
    CourseListSerializer,
    CourseSerializer,
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
    LessonSerializer,
    MediaAssetSerializer,
    ModuleSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category CRUD operations."""

    queryset = Category.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return CategoryListSerializer
        return CategorySerializer

    def get_queryset(self):
        queryset = Category.objects.filter(is_active=True)

        # Filter only root categories (no parent)
        root_only = self.request.query_params.get("root_only")
        if root_only and root_only.lower() == "true":
            queryset = queryset.filter(parent__isnull=True)

        # Filter by parent category
        parent_id = self.request.query_params.get("parent")
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)

        return queryset.annotate(
            course_count=Count("courses", filter=Q(courses__status="published"))
        ).order_by("order", "name")

    @action(detail=True, methods=["get"])
    def courses(self, request, pk=None):
        """Get all courses in this category."""
        category = self.get_object()
        courses = Course.objects.filter(
            category=category, status=Course.Status.PUBLISHED
        )
        serializer = CourseListSerializer(courses, many=True)
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet for Course CRUD operations."""

    queryset = Course.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return CourseListSerializer
        if self.action == "create":
            return CourseCreateSerializer
        return CourseSerializer

    def get_queryset(self):
        queryset = Course.objects.prefetch_related(
            "modules", "modules__lessons", "category", "contracts"
        ).select_related("category", "created_by")

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by course type
        course_type = self.request.query_params.get("type")
        if course_type:
            queryset = queryset.filter(course_type=course_type)

        # Filter by risk level
        risk_level = self.request.query_params.get("risk_level")
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)

        # Filter by target profile
        profile = self.request.query_params.get("profile")
        if profile:
            queryset = queryset.filter(target_profiles__contains=[profile])

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by category slug
        category_slug = self.request.query_params.get("category_slug")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Filter by contract
        contract = self.request.query_params.get("contract")
        if contract:
            queryset = queryset.filter(contracts__id=contract)

        # Search by title or code
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(code__icontains=search)
            )

        return queryset.distinct()

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish a course."""
        course = self.get_object()
        if course.status == Course.Status.PUBLISHED:
            return Response(
                {"error": "Course is already published"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        course.status = Course.Status.PUBLISHED
        course.published_at = timezone.now()
        course.save()

        return Response({"status": "Course published"})

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive a course."""
        course = self.get_object()
        course.status = Course.Status.ARCHIVED
        course.save()
        return Response({"status": "Course archived"})

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a course with all modules and lessons."""
        original = self.get_object()

        with transaction.atomic():
            # Clone course
            new_course = Course.objects.create(
                code=f"{original.code}_copy",
                title=f"{original.title} (copia)",
                description=original.description,
                objectives=original.objectives,
                duration=original.duration,
                course_type=original.course_type,
                risk_level=original.risk_level,
                target_profiles=original.target_profiles,
                validity_months=original.validity_months,
                created_by=request.user,
                status=Course.Status.DRAFT,
            )

            # Clone modules and lessons
            for module in original.modules.all():
                new_module = Module.objects.create(
                    course=new_course,
                    title=module.title,
                    description=module.description,
                    order=module.order,
                )

                for lesson in module.lessons.all():
                    Lesson.objects.create(
                        module=new_module,
                        title=lesson.title,
                        description=lesson.description,
                        lesson_type=lesson.lesson_type,
                        content=lesson.content,
                        video_url=lesson.video_url,
                        duration=lesson.duration,
                        order=lesson.order,
                        is_mandatory=lesson.is_mandatory,
                        is_offline_available=lesson.is_offline_available,
                        metadata=lesson.metadata,
                    )

        serializer = CourseSerializer(new_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ModuleViewSet(viewsets.ModelViewSet):
    """ViewSet for Module CRUD operations."""

    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs.get("course_pk")
        return Module.objects.filter(course_id=course_id).prefetch_related("lessons")

    def perform_create(self, serializer):
        course_id = self.kwargs.get("course_pk")
        course = get_object_or_404(Course, pk=course_id)
        serializer.save(course=course)


class LessonViewSet(viewsets.ModelViewSet):
    """ViewSet for Lesson CRUD operations."""

    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        module_id = self.kwargs.get("module_pk")
        return Lesson.objects.filter(module_id=module_id)

    def perform_create(self, serializer):
        module_id = self.kwargs.get("module_pk")
        module = get_object_or_404(Module, pk=module_id)
        serializer.save(module=module)


class MediaAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for MediaAsset CRUD operations."""

    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = MediaAsset.objects.all()

        file_type = self.request.query_params.get("type")
        if file_type:
            queryset = queryset.filter(file_type=file_type)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Enrollment CRUD operations."""

    queryset = Enrollment.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return EnrollmentCreateSerializer
        return EnrollmentSerializer

    def get_queryset(self):
        queryset = Enrollment.objects.select_related("user", "course", "assigned_by")

        # Filter by user
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by course
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        """Enroll multiple users in a course."""
        serializer = BulkEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data["user_ids"]
        course_id = serializer.validated_data["course_id"]
        due_date = serializer.validated_data.get("due_date")

        course = get_object_or_404(Course, pk=course_id)
        enrollments = []

        for user_id in user_ids:
            enrollment, created = Enrollment.objects.get_or_create(
                user_id=user_id,
                course=course,
                defaults={
                    "due_date": due_date,
                    "assigned_by": request.user,
                },
            )
            if created:
                enrollments.append(enrollment)

        return Response(
            {
                "created": len(enrollments),
                "skipped": len(user_ids) - len(enrollments),
            },
            status=status.HTTP_201_CREATED,
        )


class MyEnrollmentsView(APIView):
    """View for current user's enrollments."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get current user's enrollments."""
        enrollments = Enrollment.objects.filter(user=request.user).select_related(
            "course"
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)

        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class LessonProgressView(APIView):
    """View for tracking lesson progress."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, enrollment_id):
        """Get lesson progress for an enrollment."""
        enrollment = get_object_or_404(
            Enrollment, pk=enrollment_id, user=request.user
        )
        progress = LessonProgress.objects.filter(enrollment=enrollment).select_related(
            "lesson"
        )
        serializer = LessonProgressSerializer(progress, many=True)
        return Response(serializer.data)

    def post(self, request, enrollment_id, lesson_id):
        """Update or create lesson progress."""
        enrollment = get_object_or_404(
            Enrollment, pk=enrollment_id, user=request.user
        )
        lesson = get_object_or_404(Lesson, pk=lesson_id)

        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson,
        )

        serializer = LessonProgressUpdateSerializer(
            progress, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Mark as completed if progress is 100%
        if progress.progress_percent >= 100 and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()

        # Update enrollment status and progress
        self._update_enrollment_progress(enrollment)

        return Response(LessonProgressSerializer(progress).data)

    def _update_enrollment_progress(self, enrollment):
        """Update enrollment progress based on lesson completion."""
        course = enrollment.course
        total_lessons = sum(
            module.lessons.filter(is_mandatory=True).count()
            for module in course.modules.all()
        )

        if total_lessons == 0:
            return

        completed_lessons = LessonProgress.objects.filter(
            enrollment=enrollment,
            is_completed=True,
            lesson__is_mandatory=True,
        ).count()

        enrollment.progress = (completed_lessons / total_lessons) * 100

        # Update status
        if enrollment.progress > 0 and enrollment.status == Enrollment.Status.ENROLLED:
            enrollment.status = Enrollment.Status.IN_PROGRESS
            enrollment.started_at = timezone.now()

        if enrollment.progress >= 100:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completed_at = timezone.now()

        enrollment.save()
