from django.contrib.auth import views as auth_views
from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.landing, name="login"),
    path("accounts/login/", views.landing, name="login"),
    path("reset/done/", views.reset_done, name="reset_done"),
    path("logout/", views.logout_user, name="logout"),
    path("account/", views.account, name="account"),
    path("home/", views.home, name="home"),
    path("task/<int:pk>/", views.task, name="task"),
    path("delete_task/<int:pk>/", views.delete_task, name="delete_task"),
    path("create_task/<int:parent_pk>/", views.create_task, name="create_task"),
    path(
        "create_ai_tasks/<int:parent_pk>/",
        views.create_ai_tasks,
        name="create_ai_tasks",
    ),
    path(
        "update_task_position/<int:pk>/<int:status>/<int:position>/",
        views.update_task_position,
        name="update_task_position",
    ),
    path("edit_task/<int:pk>/", views.edit_task, name="edit_task"),
    path("dice_roll/", views.dice_roll, name="dice_roll"),
    path("search_task/", views.search_task, name="search_task"),
    # Password reset paths
    path(
        "password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"
    ),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    re_path(
        r"^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z\-]+)/$",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
