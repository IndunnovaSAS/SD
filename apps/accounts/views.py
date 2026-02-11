"""
Web views for accounts app (HTMX-powered).
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods, require_POST

from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import (
    LoginForm,
    PasswordChangeForm,
    PasswordResetConfirmForm,
    PasswordResetRequestForm,
    ProfileForm,
    TwoFactorSetupForm,
    TwoFactorVerifyForm,
    UserCreateForm,
    UserEditForm,
)
from .models import JobHistory

logger = logging.getLogger(__name__)
User = get_user_model()


def login_view(request):
    """Login page with HTMX support."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    form = LoginForm(request.POST or None)
    error = None

    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", False)

            # El backend soporta autenticación por email o número de documento
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # Check if user has 2FA enabled
                if user_has_2fa(user):
                    # Store user ID in session for 2FA verification
                    request.session["pending_2fa_user_id"] = user.pk
                    request.session["pending_2fa_remember"] = remember_me

                    if request.htmx:
                        return render(request, "accounts/partials/2fa_form.html")
                    return redirect("accounts:verify_2fa")

                # No 2FA, log in directly
                login(request, user)

                if not remember_me:
                    request.session.set_expiry(0)

                next_url = request.GET.get("next", "accounts:dashboard")

                if request.htmx:
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse(next_url) if ":" in next_url else next_url
                    return response

                return redirect(next_url)
            else:
                error = "Credenciales inválidas. Por favor, intente de nuevo."
                logger.warning(f"Failed login attempt for: {username}")

    context = {
        "form": form,
        "error": error,
    }

    if request.htmx:
        return render(request, "accounts/partials/login_form.html", context)

    return render(request, "accounts/login.html", context)


def verify_2fa_view(request):
    """Verify 2FA code during login."""
    user_id = request.session.get("pending_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")

    user = get_object_or_404(User, pk=user_id)
    form = TwoFactorVerifyForm(request.POST or None)
    error = None

    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]

        # Verify the token against user's TOTP devices
        for device in devices_for_user(user, confirmed=True):
            if device.verify_token(token):
                login(request, user)

                remember = request.session.pop("pending_2fa_remember", False)
                request.session.pop("pending_2fa_user_id", None)

                if not remember:
                    request.session.set_expiry(0)

                if request.htmx:
                    response = HttpResponse()
                    response["HX-Redirect"] = reverse("accounts:dashboard")
                    return response

                return redirect("accounts:dashboard")

        error = "Código inválido. Por favor, intente de nuevo."

    context = {"form": form, "error": error}

    if request.htmx:
        return render(request, "accounts/partials/2fa_verify_form.html", context)

    return render(request, "accounts/verify_2fa.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    """Logout user with confirmation."""
    if request.method == "POST":
        logout(request)
        messages.success(request, "Has cerrado sesión exitosamente.")
        return redirect("accounts:login")

    return render(request, "accounts/logout_confirm.html")


@login_required
def dashboard(request):
    """Main dashboard."""
    from apps.courses.models import Category

    categories = Category.objects.filter(parent__isnull=True, is_active=True).order_by(
        "order", "name"
    )
    context = {
        "user": request.user,
        "categories": categories,
        "job_profiles": User.JobProfile.choices,
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile(request):
    """User profile page."""
    context = {
        "user": request.user,
        "has_2fa": user_has_2fa(request.user),
    }
    return render(request, "accounts/profile.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    """Edit user profile."""
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")

        if request.htmx:
            return render(request, "accounts/partials/profile_success.html")

        return redirect("accounts:profile")

    context = {"form": form}

    if request.htmx:
        return render(request, "accounts/partials/profile_form.html", context)

    return render(request, "accounts/profile_edit.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """Change user password."""
    form = PasswordChangeForm(user=request.user, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, "Contraseña actualizada correctamente. Por favor, inicie sesión nuevamente."
        )
        logout(request)
        return redirect("accounts:login")

    context = {"form": form}
    return render(request, "accounts/change_password.html", context)


def password_reset_request(request):
    """Request password reset email."""
    form = PasswordResetRequestForm(request.POST or None)
    email_sent = False

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        try:
            user = User.objects.get(email=email)
            # Generate token and send email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_url = request.build_absolute_uri(
                reverse("accounts:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
            )

            context = {
                "user": user,
                "reset_url": reset_url,
            }

            subject = "Recuperar contraseña - SD LMS"
            message = render_to_string("accounts/emails/password_reset.txt", context)
            html_message = render_to_string("accounts/emails/password_reset.html", context)

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Password reset email sent to {email}")
        except User.DoesNotExist:
            # Don't reveal if email exists
            logger.info(f"Password reset requested for non-existent email: {email}")

        email_sent = True

    context = {
        "form": form,
        "email_sent": email_sent,
    }

    if request.htmx and email_sent:
        return render(request, "accounts/partials/password_reset_sent.html")

    return render(request, "accounts/password_reset.html", context)


def password_reset_confirm(request, uidb64, token):
    """Confirm password reset with new password."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/password_reset_invalid.html")

    form = PasswordResetConfirmForm(user=user, data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, "Contraseña restablecida correctamente. Ahora puede iniciar sesión."
        )
        return redirect("accounts:login")

    context = {"form": form}
    return render(request, "accounts/password_reset_confirm.html", context)


# ==================== 2FA Views ====================


@login_required
def setup_2fa(request):
    """Set up 2FA for user account."""
    user = request.user

    # Check if user already has a confirmed device
    if user_has_2fa(user):
        messages.info(request, "Ya tiene la autenticación de dos factores activada.")
        return redirect("accounts:profile")

    # Get or create an unconfirmed TOTP device
    device, created = TOTPDevice.objects.get_or_create(
        user=user,
        confirmed=False,
        defaults={"name": "Autenticador"},
    )

    if request.method == "POST":
        form = TwoFactorSetupForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["token"]
            if device.verify_token(token):
                device.confirmed = True
                device.save()
                messages.success(request, "Autenticación de dos factores activada correctamente.")
                return redirect("accounts:profile")
            else:
                form.add_error("token", "Código inválido. Por favor, intente de nuevo.")
    else:
        form = TwoFactorSetupForm()

    # Generate QR code URL
    totp_url = device.config_url

    context = {
        "form": form,
        "totp_url": totp_url,
        "secret_key": device.key,
    }

    return render(request, "accounts/setup_2fa.html", context)


@login_required
@require_POST
def disable_2fa(request):
    """Disable 2FA for user account."""
    user = request.user

    # Delete all TOTP devices for user
    TOTPDevice.objects.filter(user=user).delete()

    messages.success(request, "Autenticación de dos factores desactivada.")
    return redirect("accounts:profile")


# ==================== Helper Functions ====================


def user_has_2fa(user):
    """Check if user has any confirmed 2FA devices."""
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


# ==================== Lockout View ====================


def lockout_view(request):
    """View shown when user is locked out due to too many failed attempts."""
    return render(request, "accounts/lockout.html")


# ==================== User Management Views (Admin Only) ====================


@login_required
@require_http_methods(["GET"])
def user_list(request):
    """List all users (admin/staff only)."""
    if not request.user.is_staff:
        messages.error(request, "No tiene permisos para acceder a esta página.")
        return redirect("accounts:dashboard")

    # Get search and filter parameters
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")
    job_profile_filter = request.GET.get("job_profile", "")

    users = User.objects.all().order_by("-created_at")

    if search:
        users = users.filter(
            models.Q(first_name__icontains=search)
            | models.Q(last_name__icontains=search)
            | models.Q(email__icontains=search)
            | models.Q(document_number__icontains=search)
        )

    if status_filter:
        users = users.filter(status=status_filter)

    if job_profile_filter:
        users = users.filter(job_profile=job_profile_filter)

    # Get unique job profiles for filter dropdown
    job_profiles = (
        User.objects.values_list("job_profile", flat=True).distinct().order_by("job_profile")
    )

    context = {
        "users": users,
        "search": search,
        "status_filter": status_filter,
        "job_profile_filter": job_profile_filter,
        "job_profiles": job_profiles,
        "status_choices": User.Status.choices,
    }

    if request.htmx:
        return render(request, "accounts/partials/user_list_table.html", context)

    return render(request, "accounts/user_list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def user_create(request):
    """Create a new user (admin/staff only)."""
    if not request.user.is_staff:
        messages.error(request, "No tiene permisos para acceder a esta página.")
        return redirect("accounts:dashboard")

    form = UserCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Usuario {user.get_full_name()} creado exitosamente.")
        logger.info(f"User {user.document_number} created by {request.user.document_number}")

        if request.htmx:
            response = HttpResponse()
            response["HX-Redirect"] = reverse("accounts:user_list")
            return response

        return redirect("accounts:user_list")

    context = {"form": form}

    if request.htmx:
        return render(request, "accounts/partials/user_form.html", context)

    return render(request, "accounts/user_create.html", context)


@login_required
@require_http_methods(["GET"])
def user_detail(request, user_id):
    """View user details (admin/staff only)."""
    if not request.user.is_staff:
        messages.error(request, "No tiene permisos para acceder a esta página.")
        return redirect("accounts:dashboard")

    user = get_object_or_404(User, pk=user_id)

    context = {
        "user_obj": user,
        "has_2fa": user_has_2fa(user),
    }

    if request.htmx:
        return render(request, "accounts/partials/user_detail.html", context)

    return render(request, "accounts/user_detail.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def user_edit(request, user_id):
    """Edit user details (admin/staff only)."""
    if not request.user.is_staff:
        messages.error(request, "No tiene permisos para acceder a esta página.")
        return redirect("accounts:dashboard")

    user = get_object_or_404(User, pk=user_id)

    # Store old values before update for job history tracking
    old_position = user.job_position
    old_profile = user.job_profile
    old_employment_type = user.employment_type

    form = UserEditForm(request.POST or None, instance=user)

    if request.method == "POST" and form.is_valid():
        updated_user = form.save()

        # Check if job-related fields changed and create history record
        position_changed = old_position != updated_user.job_position
        profile_changed = old_profile != updated_user.job_profile
        employment_changed = old_employment_type != updated_user.employment_type

        if position_changed or profile_changed or employment_changed:
            JobHistory.objects.create(
                user=updated_user,
                previous_position=old_position,
                new_position=updated_user.job_position,
                previous_profile=old_profile,
                new_profile=updated_user.job_profile,
                previous_employment_type=old_employment_type,
                new_employment_type=updated_user.employment_type,
                change_date=timezone.now().date(),
                changed_by=request.user,
                reason="Modificado desde el sistema web",
            )

        messages.success(request, f"Usuario {user.get_full_name()} actualizado exitosamente.")
        logger.info(f"User {user.document_number} updated by {request.user.document_number}")

        if request.htmx:
            response = HttpResponse()
            response["HX-Redirect"] = reverse("accounts:user_detail", kwargs={"user_id": user.pk})
            return response

        return redirect("accounts:user_detail", user_id=user.pk)

    context = {
        "form": form,
        "user_obj": user,
    }

    if request.htmx:
        return render(request, "accounts/partials/user_form.html", context)

    return render(request, "accounts/user_edit.html", context)


@login_required
@require_POST
def user_toggle_status(request, user_id):
    """Toggle user active status (admin/staff only)."""
    if not request.user.is_staff:
        messages.error(request, "No tiene permisos para realizar esta acción.")
        return redirect("accounts:dashboard")

    user = get_object_or_404(User, pk=user_id)

    # Prevent self-deactivation
    if user.pk == request.user.pk:
        messages.error(request, "No puede desactivar su propia cuenta.")
        if request.htmx:
            response = HttpResponse()
            response["HX-Redirect"] = reverse("accounts:user_list")
            return response
        return redirect("accounts:user_list")

    user.is_active = not user.is_active
    user.save()

    action = "activado" if user.is_active else "desactivado"
    messages.success(request, f"Usuario {user.get_full_name()} {action} exitosamente.")
    logger.info(f"User {user.document_number} {action} by {request.user.document_number}")

    if request.htmx:
        response = HttpResponse()
        response["HX-Redirect"] = reverse("accounts:user_list")
        return response

    return redirect("accounts:user_list")
