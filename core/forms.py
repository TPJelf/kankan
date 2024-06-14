from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from .models import Task


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields["username"].widget = forms.TextInput(
            attrs={"class": "form-control", "placeholder": ""}
        )
        self.fields["email"].widget = forms.EmailInput(
            attrs={"class": "form-control", "placeholder": ""}
        )
        self.fields["password1"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": ""}
        )
        self.fields["password2"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": ""}
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)  # Don't save yet
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.fields["username"].widget = forms.TextInput(
            attrs={"class": "form-control", "placeholder": ""}
        )
        self.fields["password"].widget = forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": ""}
        )


class ResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super(ResetForm, self).__init__(*args, **kwargs)
        self.fields["email"].widget = forms.EmailInput(
            attrs={"class": "form-control", "placeholder": ""}
        )


class CreateTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.parent = kwargs.pop("parent", None)
        super(CreateTaskForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(CreateTaskForm, self).save(commit=False)
        instance.user = self.user
        instance.parent = self.parent
        if commit:
            instance.save()
        return instance


class ChangePasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

        self.fields["new_password1"].widget = forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "",
            }
        )

        self.fields["new_password2"].widget = forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "",
            }
        )


class UpdateEmailForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "New email"
        self.fields["email"].widget = forms.EmailInput(
            attrs={"class": "form-control", "placeholder": self.instance.email}
        )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email
