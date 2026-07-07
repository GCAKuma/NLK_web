from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    ReadOnlyPasswordHashField,
)
from django.contrib.auth.password_validation import validate_password

from .models import Address, User

INPUT_CLASS = "field-input"


class RegistrationForm(forms.ModelForm):
    """Customer sign-up form (email + phone + password)."""

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("full_name", "email", "phone_number")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS, "autocomplete": "email"}),
            "phone_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("The two password fields didn't match.")
        validate_password(p2)
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Login form relabeled for email-based authentication."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Email"
        self.fields["username"].widget = forms.EmailInput(
            attrs={"class": INPUT_CLASS, "autocomplete": "email", "autofocus": True}
        )
        self.fields["password"].widget = forms.PasswordInput(
            attrs={"class": INPUT_CLASS, "autocomplete": "current-password"}
        )


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name", "phone_number", "address_line1", "address_line2",
            "city", "district", "postal_code",
        )
        widgets = {f: forms.TextInput(attrs={"class": INPUT_CLASS}) for f in fields}


class ProfileForm(forms.ModelForm):
    """Edit personal details on the account/profile page."""

    class Meta:
        model = User
        fields = ("full_name", "phone_number")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "phone_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
        }


# --------------------------------------------------------------------------
# Admin forms (email-based; the default auth forms assume a username field)
# --------------------------------------------------------------------------
class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "full_name", "phone_number")

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change it using "
            '<a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = (
            "email", "password", "full_name", "phone_number",
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
        )
