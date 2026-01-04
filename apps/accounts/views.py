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
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
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
)

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
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", False)

            user = authenticate(request, email=email, password=password)

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
                logger.warning(f"Failed login attempt for email: {email}")

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
    context = {
        "user": request.user,
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
        messages.success(request, "Contraseña actualizada correctamente. Por favor, inicie sesión nuevamente.")
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
        messages.success(request, "Contraseña restablecida correctamente. Ahora puede iniciar sesión.")
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
