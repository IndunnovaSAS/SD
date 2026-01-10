"""
Web views for courses app.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Category, Course, Enrollment, Lesson, LessonProgress, Module
from .services import EnrollmentService


@login_required
def course_list(request):
    """List all published courses."""
    courses = Course.objects.filter(status=Course.Status.PUBLISHED).select_related(
        "category", "created_by"
    ).prefetch_related("modules")

    # Filtering
    category_slug = request.GET.get("category")
    if category_slug:
        courses = courses.filter(category__slug=category_slug)

    course_type = request.GET.get("type")
    if course_type:
        courses = courses.filter(course_type=course_type)

    risk_level = request.GET.get("risk_level")
    if risk_level:
        courses = courses.filter(risk_level=risk_level)

    search = request.GET.get("search")
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # Get categories for filter
    categories = Category.objects.filter(is_active=True, parent__isnull=True).annotate(
        course_count=Count("courses", filter=Q(courses__status="published"))
    )

    # Get user's enrollments
    user_enrollments = set(
        Enrollment.objects.filter(user=request.user).values_list("course_id", flat=True)
    )

    context = {
        "courses": courses,
        "categories": categories,
        "user_enrollments": user_enrollments,
        "current_category": category_slug,
        "current_type": course_type,
        "current_risk_level": risk_level,
        "search_query": search,
    }
    return render(request, "courses/course_list.html", context)


@login_required
def course_detail(request, course_id):
    """View course details."""
    course = get_object_or_404(
        Course.objects.select_related("category", "created_by").prefetch_related(
            "modules__lessons", "prerequisites"
        ),
        id=course_id,
    )

    # Check if user is enrolled
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()

    # Get lesson progress if enrolled
    lesson_progress = {}
    if enrollment:
        progress_qs = LessonProgress.objects.filter(enrollment=enrollment)
        lesson_progress = {lp.lesson_id: lp for lp in progress_qs}

    context = {
        "course": course,
        "enrollment": enrollment,
        "lesson_progress": lesson_progress,
    }
    return render(request, "courses/course_detail.html", context)


@login_required
@require_http_methods(["POST"])
def enroll_course(request, course_id):
    """Enroll current user in a course."""
    course = get_object_or_404(Course, id=course_id, status=Course.Status.PUBLISHED)

    # Check prerequisites
    if course.prerequisites.exists():
        completed_prereqs = Enrollment.objects.filter(
            user=request.user,
            course__in=course.prerequisites.all(),
            status=Enrollment.Status.COMPLETED,
        ).count()

        if completed_prereqs < course.prerequisites.count():
            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "courses/partials/enroll_error.html",
                    {"error": "Debes completar los prerrequisitos primero."},
                )
            return redirect("courses:detail", course_id=course_id)

    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={"assigned_by": request.user},
    )

    if request.headers.get("HX-Request"):
        return render(
            request,
            "courses/partials/enrollment_status.html",
            {"enrollment": enrollment, "course": course},
        )
    return redirect("courses:detail", course_id=course_id)


@login_required
def lesson_view(request, course_id, lesson_id):
    """View a lesson."""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # Get or create enrollment
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    # Get or create lesson progress
    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
    )

    # Get next and previous lessons
    all_lessons = list(
        Lesson.objects.filter(module__course=course).order_by("module__order", "order")
    )
    current_index = next(
        (i for i, l in enumerate(all_lessons) if l.id == lesson.id), 0
    )
    prev_lesson = all_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = (
        all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None
    )

    context = {
        "course": course,
        "lesson": lesson,
        "progress": progress,
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "enrollment": enrollment,
    }
    return render(request, "courses/lesson_view.html", context)


@login_required
@require_http_methods(["POST"])
def update_progress(request, course_id, lesson_id):
    """Update lesson progress via HTMX."""
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
    )

    # Update progress
    new_progress = request.POST.get("progress", 0)
    progress.progress_percent = min(float(new_progress), 100)

    if progress.progress_percent >= 100:
        progress.is_completed = True
        from django.utils import timezone
        progress.completed_at = timezone.now()

    progress.save()

    # Update enrollment progress using the service
    EnrollmentService.update_enrollment_progress(enrollment)

    if request.headers.get("HX-Request"):
        return render(
            request,
            "courses/partials/progress_bar.html",
            {"progress": progress, "enrollment": enrollment},
        )

    return JsonResponse({"status": "ok", "progress": float(progress.progress_percent)})


@login_required
def my_courses(request):
    """View user's enrolled courses."""
    enrollments = (
        Enrollment.objects.filter(user=request.user)
        .select_related("course", "course__category")
        .order_by("-updated_at")
    )

    # Filter by status
    status_filter = request.GET.get("status")
    if status_filter:
        enrollments = enrollments.filter(status=status_filter)

    context = {
        "enrollments": enrollments,
        "current_status": status_filter,
    }
    return render(request, "courses/my_courses.html", context)
