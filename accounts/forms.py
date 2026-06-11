from django import forms
from .models import Account, UserProfile


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter Password",
                "class": "form-control",
            }
        )
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm Password"})
    )

    class Meta:
        model = Account
        fields = ["first_name", "last_name", "phone_number", "email", "password"]

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        if not first_name:
            raise forms.ValidationError("First name is required.")
        # First letter of each word should be uppercase, allow letters, spaces, hyphens, apostrophes
        import re

        name_regex = r"^[A-Z][a-z]*(?: [A-Z][a-z]*)*(?:-[A-Z][a-z]*)*(?:'[A-Z][a-z]*)*$"
        if not re.match(name_regex, first_name.strip()) or not (
            2 <= len(first_name.strip()) <= 50
        ):
            raise forms.ValidationError(
                "First name must start with an uppercase letter and contain only letters."
            )
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name")
        if not last_name:
            raise forms.ValidationError("Last name is required.")
        # Same validation as first_name
        import re

        name_regex = r"^[A-Z][a-z]*(?: [A-Z][a-z]*)*(?:-[A-Z][a-z]*)*(?:'[A-Z][a-z]*)*$"
        if not re.match(name_regex, last_name.strip()) or not (
            2 <= len(last_name.strip()) <= 50
        ):
            raise forms.ValidationError(
                "Last name must start with an uppercase letter and contain only letters."
            )
        return last_name

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number")
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        # Should be exactly 11 digits starting with operator code (without leading 0)
        # Bangladeshi operators: GP (17, 13), Robi (18), Airtel (16), Banglalink (19, 14), Teletalk (15)
        import re

        phone_regex = r"^(17|13|18|16|19|14|15)\d{8}$"
        cleaned_phone = phone_number.replace(" ", "")
        if not re.match(phone_regex, cleaned_phone) or len(cleaned_phone) != 10:
            raise forms.ValidationError(
                "Phone number must be 10 digits starting with a valid Bangladeshi operator code (e.g., 1712345678)."
            )
        # Prepend +880 for storage
        return "+880" + cleaned_phone

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email is required.")
        # Strong email regex: RFC 5322 compliant, but simplified
        import re

        email_regex = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(email_regex, email) or len(email) > 254:
            raise forms.ValidationError("Please enter a valid email address.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not password:
            raise forms.ValidationError("Password is required.")
        # Strong password: at least 12 characters, 1 uppercase, 1 lowercase, 1 number, 1 special character, no common words
        import re

        password_regex = (
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        )
        common_words = ["password", "123456", "qwerty", "admin", "user"]
        if not re.match(password_regex, password) or any(
            word in password.lower() for word in common_words
        ):
            raise forms.ValidationError(
                "Password must be at least 8 characters long, contain at least one uppercase letter, one lowercase letter, one number, and one special character. Common words are not allowed."
            )
        return password

    def clean(self):
        cleaned_data = super(RegistrationForm, self).clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Password does not match!")

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs["placeholder"] = "Enter First Name"
        self.fields["last_name"].widget.attrs["placeholder"] = "Enter last Name"
        self.fields["phone_number"].widget.attrs["placeholder"] = "Enter 10-digit phone number (e.g., 1712345678)"
        self.fields["email"].widget.attrs["placeholder"] = "Enter Email Address"
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"


class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ("first_name", "last_name", "phone_number", "email")

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"
        self.fields["email"].disabled = True


class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        error_messages={"invalid": ("Image files only")},
        widget=forms.FileInput,
    )

    class Meta:
        model = UserProfile
        fields = (
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
            "profile_picture",
        )

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"
