import json
import os
from random import choice

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import HttpResponse, get_object_or_404, redirect, render

from .forms import *
from .models import Settings, Task


def validate_turnstile_widget_response(token, request_ip):
    secret_key = os.environ["CLOUDFLARE_TURNSTILE_SECRET_KEY"]
    response = requests.post(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data={
            "secret": secret_key,
            "response": token,
            "remoteip": request_ip,
        },
    ).json()
    if not response["success"]:
        raise ValidationError(
            "Cloudflare was unable to validate you, please try again. If the problem persist please contact us."
        )


def reset_done(request):
    messages.info(request, "Password reset successfully.")
    return redirect("home")


def landing(request):
    signup_form = SignupForm()
    login_form = LoginForm()
    reset_form = ResetForm()
    cloudflare_turnstile_site_key = os.environ["CLOUDFLARE_TURNSTILE_SITE_KEY"]

    if request.method == "POST":
        if "signup" in request.POST:
            request_ip = request.META.get("REMOTE_ADDR")
            token = request.POST.get("cf-turnstile-response")
            try:
                validate_turnstile_widget_response(token, request_ip)
                signup_form = SignupForm(request.POST)
                if signup_form.is_valid():
                    user = signup_form.save()
                    login(request, user)

                    # Create base tasks and subtasks
                    selfcare = Task.objects.create(user=user, name="Self care")
                    Task.objects.create(user=user, parent=selfcare, name="Work out")
                    house = Task.objects.create(user=user, name="House chores")
                    bathroom = Task.objects.create(
                        user=user,
                        name="Clean bathroom",
                        parent=house,
                        status=Task.Status.INPROGRESS,
                    )
                    Task.objects.create(
                        user=user,
                        name="Change towels",
                        parent=bathroom,
                        status=Task.Status.DONE,
                    )
                    Task.objects.create(
                        user=user,
                        name="Clean sink",
                        parent=bathroom,
                        status=Task.Status.PENDING,
                    )
                    Task.objects.create(user=user, name="Empty trashcans", parent=house)
                    Task.objects.create(user=user, name="Work stuff")

                    return redirect("home")
                else:
                    messages.info(request, "Sign up error:")
                    for field, errors in signup_form.errors.items():
                        field_name = field.replace("_", " ").title()
                        if field == "password2":
                            field_name = "Password"
                        for error in errors:
                            message = f"{field_name}: {error}"
                            messages.info(request, message)

            except ValidationError as e:
                messages.info(request, e)

        elif "login" in request.POST:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data.get("username")
                password = login_form.cleaned_data.get("password")
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect("home")
            else:
                messages.info(request, "Invalid username or password.")

        elif "reset" in request.POST:
            reset_form = ResetForm(request.POST)
            if reset_form.is_valid():
                reset_message = "If an account exists with the email address you provided, we have sent a password reset link. Please check your inbox and spam folder."
                if not User.objects.filter(
                    email=reset_form.cleaned_data["email"]
                ).exists():
                    messages.info(
                        request,
                        reset_message,
                    )
                else:
                    reset_form.save()
                    messages.info(
                        request,
                        reset_message,
                    )

    elif request.user.is_authenticated:
        return redirect("home")

    context = {
        "signup_form": signup_form,
        "login_form": login_form,
        "reset_form": reset_form,
        "cloudflare_turnstile_site_key": cloudflare_turnstile_site_key,
    }
    return render(
        request,
        "login.html",
        context,
    )


def logout_user(request):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def account(request):
    change_password_form = ChangePasswordForm(request.user)
    update_email_form = UpdateEmailForm(instance=request.user)
    title = "Account"

    try:
        settings = Settings.objects.get(user=request.user)
        apikey = settings.ai_apikey
    except:
        apikey = ""

    if request.method == "POST":
        if "change-password" in request.POST:
            change_password_form = ChangePasswordForm(request.user, request.POST)
            if change_password_form.is_valid():
                change_password_form.save()
                messages.info(request, "Password changed successfully.")
            else:
                for field, errors in change_password_form.errors.items():
                    for error in errors:
                        messages.info(request, error)

        elif "delete-account" in request.POST:
            password = request.POST.get("password")
            user = authenticate(
                request, username=request.user.username, password=password
            )
            if user is not None:
                user.delete()
                logout(request)
                messages.info(request, "Your account has been successfully deleted.")
                return redirect("login")
            else:
                messages.info(request, "Incorrect password. Account deletion failed.")

        elif "update-email" in request.POST:
            update_email_form = UpdateEmailForm(request.POST, instance=request.user)
            if update_email_form.is_valid():
                update_email_form.save()
                messages.info(request, "Email updated successfully.")
            else:
                for field, errors in update_email_form.errors.items():
                    for error in errors:
                        messages.info(request, error)

        elif "update-apikey" in request.POST:
            apikey = request.POST.get("apikey")
            settings, created = Settings.objects.update_or_create(
                user=request.user, defaults={"ai_apikey": apikey}
            )
            messages.info(request, "API key updated successfully.")

    context = {
        "change_password_form": change_password_form,
        "update_email_form": update_email_form,
        "apikey": apikey,
        "title": title,
    }

    return render(request, "account.html", context)


@login_required(login_url="login")
def home(request):
    title = "Home"
    tasks = Task.objects.filter(user=request.user).order_by("position")
    pending = tasks.filter(
        Q(status=Task.Status.PENDING) | Q(status=Task.Status.INPROGRESS),
        parent__isnull=False,
    ).exists()
    tasks = tasks.filter(parent=None)

    for task in tasks:
        counts = task.count_recently_updated_subtasks()
        task.count_last_24_hours = counts["count_last_24_hours"]
        task.count_last_7_days = counts["count_last_7_days"]

    context = {
        "tasks": tasks,
        "pending": pending,
        "parent_pk": 0,
        "title": title,
    }
    return render(request, "home.html", context)


@login_required(login_url="login")
def task(request, pk):

    parent = get_object_or_404(Task, pk=pk, user=request.user)
    title = parent.name
    tasks = Task.objects.filter(user=request.user).order_by("position")
    pending = tasks.filter(
        Q(status=Task.Status.PENDING) | Q(status=Task.Status.INPROGRESS),
        parent__isnull=False,
    ).exists()
    tasks = tasks.filter(parent=parent).order_by("position")
    tasks_pending = tasks.filter(status=Task.Status.PENDING)
    tasks_inprogress = tasks.filter(status=Task.Status.INPROGRESS)
    tasks_done = tasks.filter(status=Task.Status.DONE)

    try:
        settings = Settings.objects.get(user=request.user)
        apikey = settings.ai_apikey
    except:
        apikey = ""

    context = {
        "tasks": tasks,
        "pending": pending,
        "parent_pk": parent.pk,
        "title": title,
        "apikey": apikey,
        "parent": parent,
        "tasks_pending": tasks_pending,
        "tasks_inprogress": tasks_inprogress,
        "tasks_done": tasks_done,
    }

    return render(request, "task.html", context)


@login_required(login_url="login")
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == "POST":
        task.name = request.POST.get("name")
        task.save()
        if task.parent is not None:
            return redirect("task", pk=task.parent.pk)
        else:
            return redirect("home")

    context = {"task": task}
    return render(request, "edit_task.html", context)


@login_required(login_url="login")
def create_task(request, parent_pk):
    if request.method == "POST":
        if parent_pk == 0:
            parent = None
        else:
            parent = get_object_or_404(Task, pk=parent_pk, user=request.user)

        form = CreateTaskForm(request.POST, user=request.user, parent=parent)
        if form.is_valid():
            form.save()
        else:
            return HttpResponse(status=400)

        if parent is not None:
            return redirect("task", pk=parent.pk)

        else:
            return redirect("home")


@login_required(login_url="login")
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    if task.parent is not None:
        return redirect("task", pk=task.parent.pk)

    else:
        return redirect("home")


@login_required(login_url="login")
def update_task_position(request, pk, status, position):
    if request.method == "POST":
        task = get_object_or_404(Task, pk=pk, user=request.user)
        task.status = status
        task.position = position
        task.save()
        return HttpResponse(status=200)


@login_required(login_url="login")
def dice_roll(request):
    supertasks = (
        Task.objects.filter(user=request.user, parent__isnull=True)
        .values_list("pk", flat=True)
        .distinct()
    )

    dice_roll = Task.objects.filter(
        user=request.user, status__in=[Task.Status.PENDING, Task.Status.INPROGRESS]
    ).exclude(id__in=supertasks)

    task = choice(dice_roll)

    context = {"task": task}
    return render(request, "dice_roll.html", context)


@login_required(login_url="login")
def create_ai_tasks(request, parent_pk):
    if request.method == "POST":
        try:
            task_names = json.loads(request.body)
            parent = get_object_or_404(Task, pk=parent_pk, user=request.user)

            for task_name in task_names:
                Task.objects.create(user=request.user, name=task_name, parent=parent)

            return HttpResponse(status=201)

        except:
            return HttpResponse(status=400)


@login_required(login_url="login")
def search_task(request):
    search_term = request.GET.get("search-term")

    if search_term != "":
        tasks = Task.objects.filter(
            user=request.user, name__icontains=search_term
        ).order_by("position")
    else:
        tasks = None
    context = {"tasks": tasks}
    return render(request, "search_task.html", context)
