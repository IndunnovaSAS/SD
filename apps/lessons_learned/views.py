"""
Lessons Learned views for SD LMS.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from apps.lessons_learned.models import Category, LessonLearned, LessonComment
from apps.lessons_learned.services import (
    CategoryService,
    LessonCommentService,
    LessonLearnedService,
)


@login_required
@require_GET
def lesson_list(request):
    """Lesson list page."""
    categories = Category.objects.filter(is_active=True).order_by("name")

    context = {
        "categories": categories,
    }

    # Check if this is an HTMX request for the grid
    if request.headers.get("HX-Request"):
        return lesson_grid(request)

    return render(request, "lessons_learned/lesson_list.html", context)


@login_required
@require_GET
def lesson_grid(request):
    """Get lesson grid (HTMX partial)."""
    category_id = request.GET.get("category")
    severity = request.GET.get("severity")
    lesson_type = request.GET.get("type")
    search = request.GET.get("search")
    page = request.GET.get("page", 1)

    # Get approved lessons
    lessons = LessonLearnedService.get_approved_lessons(
        category_id=category_id,
        lesson_type=lesson_type,
        severity=severity,
        search=search,
    )

    paginator = Paginator(lessons, 12)
    page_obj = paginator.get_page(page)

    context = {"lessons": page_obj}
    return render(request, "lessons_learned/partials/lesson_grid.html", context)


@login_required
@require_GET
def lesson_detail(request, lesson_id):
    """Lesson detail page."""
    lesson = get_object_or_404(
        LessonLearned.objects.select_related("created_by", "category"),
        id=lesson_id
    )

    # Increment view count
    LessonLearnedService.increment_view_count(lesson)

    context = {"lesson": lesson}
    return render(request, "lessons_learned/lesson_detail.html", context)


@login_required
def lesson_create(request):
    """Create a new lesson."""
    categories = Category.objects.filter(is_active=True)

    if request.method == "POST":
        lesson = LessonLearnedService.create_lesson(
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            lesson_type=request.POST.get("lesson_type"),
            severity=request.POST.get("severity"),
            created_by=request.user,
            category_id=request.POST.get("category") or None,
            root_cause=request.POST.get("root_cause"),
            corrective_actions=request.POST.get("corrective_actions"),
            preventive_actions=request.POST.get("preventive_actions"),
            recommendations=request.POST.get("recommendations"),
        )

        messages.success(request, "Lección creada exitosamente")
        return redirect("lessons_learned:detail", lesson_id=lesson.id)

    context = {"categories": categories}
    return render(request, "lessons_learned/lesson_form.html", context)


@login_required
def lesson_edit(request, lesson_id):
    """Edit a lesson."""
    lesson = get_object_or_404(LessonLearned, id=lesson_id)

    # Check permissions
    if lesson.created_by != request.user and not request.user.is_staff:
        messages.error(request, "No tienes permiso para editar esta lección")
        return redirect("lessons_learned:detail", lesson_id=lesson.id)

    categories = Category.objects.filter(is_active=True)

    if request.method == "POST":
        lesson = LessonLearnedService.update_lesson(
            lesson=lesson,
            title=request.POST.get("title"),
            description=request.POST.get("description"),
            lesson_type=request.POST.get("lesson_type"),
            severity=request.POST.get("severity"),
            category_id=request.POST.get("category") or None,
            root_cause=request.POST.get("root_cause"),
            corrective_actions=request.POST.get("corrective_actions"),
            preventive_actions=request.POST.get("preventive_actions"),
            recommendations=request.POST.get("recommendations"),
        )

        messages.success(request, "Lección actualizada exitosamente")
        return redirect("lessons_learned:detail", lesson_id=lesson.id)

    context = {"lesson": lesson, "categories": categories}
    return render(request, "lessons_learned/lesson_form.html", context)


@login_required
@require_POST
def submit_for_review(request, lesson_id):
    """Submit lesson for review."""
    lesson = get_object_or_404(LessonLearned, id=lesson_id)

    if lesson.created_by != request.user:
        return HttpResponse("No autorizado", status=403)

    LessonLearnedService.submit_for_review(lesson)

    if request.headers.get("HX-Request"):
        return HttpResponse(
            '<span class="badge badge-warning">Pendiente revisión</span>'
        )

    messages.success(request, "Lección enviada para revisión")
    return redirect("lessons_learned:detail", lesson_id=lesson.id)


@login_required
@require_POST
def approve_lesson(request, lesson_id):
    """Approve a lesson (staff only)."""
    if not request.user.is_staff:
        return HttpResponse("No autorizado", status=403)

    lesson = get_object_or_404(LessonLearned, id=lesson_id)
    notes = request.POST.get("notes", "")

    LessonLearnedService.approve_lesson(lesson, request.user, notes)

    if request.headers.get("HX-Request"):
        return HttpResponse('<span class="badge badge-success">Aprobada</span>')

    messages.success(request, "Lección aprobada")
    return redirect("lessons_learned:detail", lesson_id=lesson.id)


@login_required
@require_POST
def reject_lesson(request, lesson_id):
    """Reject a lesson (staff only)."""
    if not request.user.is_staff:
        return HttpResponse("No autorizado", status=403)

    lesson = get_object_or_404(LessonLearned, id=lesson_id)
    reason = request.POST.get("reason", "")

    if not reason:
        return HttpResponse("Debe indicar el motivo del rechazo", status=400)

    LessonLearnedService.reject_lesson(lesson, request.user, reason)

    if request.headers.get("HX-Request"):
        return HttpResponse('<span class="badge badge-error">Rechazada</span>')

    messages.info(request, "Lección rechazada")
    return redirect("lessons_learned:detail", lesson_id=lesson.id)


@login_required
@require_POST
def add_comment(request, lesson_id):
    """Add a comment to a lesson."""
    lesson = get_object_or_404(LessonLearned, id=lesson_id)
    content = request.POST.get("content", "").strip()

    if not content:
        return HttpResponse("El comentario no puede estar vacío", status=400)

    comment = LessonCommentService.add_comment(lesson, request.user, content)

    # Return the new comment HTML
    context = {"comment": comment}
    return render(request, "lessons_learned/partials/comment_item.html", context)


@login_required
@require_GET
def my_lessons(request):
    """Get user's lessons."""
    lessons = LessonLearned.objects.filter(
        created_by=request.user
    ).order_by("-created_at")

    context = {"lessons": lessons}
    return render(request, "lessons_learned/my_lessons.html", context)
