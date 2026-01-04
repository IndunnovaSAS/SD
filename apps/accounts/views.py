"""
Web views for accounts app (HTMX-powered).
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


def login_view(request):
    """Login page."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "accounts:dashboard")
            return redirect(next_url)
        else:
            return render(request, "accounts/login.html", {"error": "Credenciales inválidas"})

    return render(request, "accounts/login.html")


@login_required
def logout_view(request):
    """Logout user."""
    logout(request)
    return redirect("accounts:login")


@login_required
def dashboard(request):
    """Main dashboard."""
    return render(request, "accounts/dashboard.html")


@login_required
def profile(request):
    """User profile page."""
    return render(request, "accounts/profile.html")


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    """Edit user profile."""
    if request.method == "POST":
        # Handle profile update
        user = request.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.phone = request.POST.get("phone", user.phone)
        user.save()

        if request.headers.get("HX-Request"):
            return render(request, "accounts/partials/profile_success.html")

        return redirect("accounts:profile")

    return render(request, "accounts/profile_edit.html")
