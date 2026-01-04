"""
Forms for accounts app.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class LoginForm(forms.Form):
    """Login form with email and password."""

    email = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "correo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label=_("Contraseña"),
        widget=forms.PasswordInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label=_("Recordarme"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
    )


class ProfileForm(forms.ModelForm):
    """Form for editing user profile."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "photo"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full", "placeholder": "Nombre"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "input input-bordered w-full", "placeholder": "Apellido"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "input input-bordered w-full", "placeholder": "+57 300 123 4567"}
            ),
            "photo": forms.FileInput(attrs={"class": "file-input file-input-bordered w-full"}),
        }


class PasswordChangeForm(SetPasswordForm):
    """Form for changing password (requires old password)."""

    old_password = forms.CharField(
        label=_("Contraseña actual"),
        widget=forms.PasswordInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "••••••••",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(user, *args, **kwargs)
        # Reorder fields
        self.fields = {
            "old_password": self.fields["old_password"],
            "new_password1": self.fields["new_password1"],
            "new_password2": self.fields["new_password2"],
        }
        # Update widget classes
        self.fields["new_password1"].widget.attrs.update(
            {"class": "input input-bordered w-full", "placeholder": "••••••••"}
        )
        self.fields["new_password2"].widget.attrs.update(
            {"class": "input input-bordered w-full", "placeholder": "••••••••"}
        )

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_("La contraseña actual es incorrecta."))
        return old_password

    def save(self, commit=True):
        self.user.set_password(self.cleaned_data["new_password1"])
        if commit:
            self.user.save()
        return self.user


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset."""

    email = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(
            attrs={
                "class": "input input-bordered w-full",
                "placeholder": "correo@ejemplo.com",
                "autocomplete": "email",
            }
        ),
    )


class PasswordResetConfirmForm(SetPasswordForm):
    """Form for setting new password after reset."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {
                "class": "input input-bordered w-full",
                "placeholder": "••••••••",
                "autocomplete": "new-password",
            }
        )
        self.fields["new_password2"].widget.attrs.update(
            {
                "class": "input input-bordered w-full",
                "placeholder": "••••••••",
                "autocomplete": "new-password",
            }
        )


class TwoFactorVerifyForm(forms.Form):
    """Form for verifying 2FA code during login."""

    token = forms.CharField(
        label=_("Código de verificación"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full text-center text-2xl tracking-widest",
                "placeholder": "000000",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data.get("token")
        if token and not token.isdigit():
            raise forms.ValidationError(_("El código debe contener solo números."))
        return token


class TwoFactorSetupForm(forms.Form):
    """Form for setting up 2FA."""

    token = forms.CharField(
        label=_("Código de verificación"),
        max_length=6,
        min_length=6,
        help_text=_("Ingrese el código de 6 dígitos de su aplicación autenticadora."),
        widget=forms.TextInput(
            attrs={
                "class": "input input-bordered w-full text-center text-2xl tracking-widest",
                "placeholder": "000000",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": "[0-9]*",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data.get("token")
        if token and not token.isdigit():
            raise forms.ValidationError(_("El código debe contener solo números."))
        return token
