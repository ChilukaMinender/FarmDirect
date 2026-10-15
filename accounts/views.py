from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .forms import RegistrationForm
from .models import Profile


def get_user_role(user):
    """Return the user's role, creating a default profile if needed."""
    profile, created = Profile.objects.get_or_create(
        user=user,
        defaults={"role": "customer"},
    )
    return profile.role


def role_redirect(user):
    """Redirect farmers and customers to the appropriate page."""
    role = get_user_role(user)

    if role == "farmer":
        return redirect("farmer_dashboard")

    return redirect("home")


def register_view(request):
    if request.user.is_authenticated:
        return role_redirect(request.user)

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                role = form.cleaned_data.get("role", "customer")

                Profile.objects.update_or_create(
                    user=user,
                    defaults={
                        "role": role,
                        "phone": form.cleaned_data.get("phone", ""),
                        "address": form.cleaned_data.get("address", ""),
                    },
                )

            authenticated_user = authenticate(
                request,
                username=user.username,
                password=form.cleaned_data["password"],
            )

            if authenticated_user is not None:
                login(request, authenticated_user)

                messages.success(
                    request,
                    "Welcome to FarmDirect! Your account is ready.",
                )

                return role_redirect(authenticated_user)

            messages.success(
                request,
                "Account created successfully. Please log in.",
            )
            return redirect("login")

    else:
        form = RegistrationForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


def login_view(request):
    if request.user.is_authenticated:
        return role_redirect(request.user)

    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            login(request, user)

            messages.success(
                request,
                "Welcome back to FarmDirect!",
            )

            return role_redirect(user)

        error = "Invalid username or password. Please try again."

    return render(
        request,
        "accounts/login.html",
        {"error": error},
    )


@login_required
@require_POST
def logout_view(request):
    logout(request)

    messages.success(
        request,
        "You have logged out successfully.",
    )

    return redirect("home")