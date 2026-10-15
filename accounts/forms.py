from django import forms
from django.contrib.auth.models import User

from .models import Profile


class RegistrationForm(forms.ModelForm):

    ROLE_CHOICES = [
        ("farmer", "Farmer"),
        ("customer", "Customer"),
    ]

    password = forms.CharField(
        label="Password",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Create a strong password",
                "autocomplete": "new-password",
            }
        ),
        help_text="Use at least 8 characters.",
    )

    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your password again",
                "autocomplete": "new-password",
            }
        ),
    )

    role = forms.ChoiceField(
        label="I want to join FarmDirect as",
        choices=ROLE_CHOICES,
        widget=forms.Select(),
    )

    phone = forms.CharField(
        label="Phone number",
        max_length=15,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your phone number",
                "autocomplete": "tel",
            }
        ),
    )

    address = forms.CharField(
        label="Address",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Enter your address",
                "autocomplete": "street-address",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "email"]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "Enter your name",
                    "autocomplete": "given-name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),
        }

        labels = {
            "username": "Username",
            "first_name": "Full name",
            "email": "Email address",
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already taken. Please choose another."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if not email:
            raise forms.ValidationError(
                "Please enter your email address."
            )

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()

        if phone:
            allowed_characters = set("0123456789+- ()")

            if not all(char in allowed_characters for char in phone):
                raise forms.ValidationError(
                    "Enter a valid phone number."
                )

            digits = "".join(char for char in phone if char.isdigit())

            if not 7 <= len(digits) <= 15:
                raise forms.ValidationError(
                    "Phone number must contain 7 to 15 digits."
                )

        return phone

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error(
                "confirm_password",
                "Passwords do not match.",
            )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.username = self.cleaned_data["username"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.set_password(self.cleaned_data["password"])

        if commit:
            user.save()

            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "role": self.cleaned_data["role"],
                    "phone": self.cleaned_data.get("phone", ""),
                    "address": self.cleaned_data.get("address", ""),
                },
            )

        return user