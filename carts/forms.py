from django import forms
from .models import Order, OTP
from django.core.exceptions import ValidationError


class ShippingForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "first_name", "last_name", "phone", "email",
            "address_line_1", "address_line_2",
            "city", "state", "country",
            "order_note", "additional_info",
        ]
        widgets = {
            "first_name":     forms.TextInput(attrs={"class": "form-control"}),
            "last_name":      forms.TextInput(attrs={"class": "form-control"}),
            "phone":          forms.TextInput(attrs={"class": "form-control"}),
            "email":          forms.EmailInput(attrs={"class": "form-control"}),
            "address_line_1": forms.TextInput(attrs={"class": "form-control"}),
            "address_line_2": forms.TextInput(attrs={"class": "form-control"}),
            "city":           forms.TextInput(attrs={"class": "form-control"}),
            "state":          forms.TextInput(attrs={"class": "form-control"}),
            "country":        forms.TextInput(attrs={"class": "form-control"}),
            "order_note":     forms.TextInput(attrs={"class": "form-control"}),
            "additional_info":forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class OTPForm(forms.Form):
    email_otp = forms.CharField(
        max_length=6, widget=forms.TextInput(attrs={"placeholder": "Enter OTP"})
    )

    def __init__(self, email, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = email

    def clean_email_otp(self):
        otp = self.cleaned_data["email_otp"]
        otp_obj = OTP.objects.filter(email=self.email).order_by("-created_at").first()
        if not otp_obj:
            raise ValidationError("Please request an OTP first.")
        if otp_obj.is_expired():
            raise ValidationError("OTP has expired. Please request a new one.")
        if otp_obj.otp_code != otp:
            raise ValidationError("Invalid OTP. Please check and try again.")
        return otp


class OrderForm(forms.ModelForm):
    email_otp = forms.CharField(
        max_length=6,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Enter OTP"}),
    )

    class Meta:
        model = Order
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
            "order_note",
            "additional_info",
            "email_verified",
        ]

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        email_otp = cleaned_data.get("email_otp")

        if email and email_otp:
            otp_obj = OTP.objects.filter(email=email).order_by("-created_at").first()
            if not otp_obj:
                raise ValidationError("Please request an OTP first.")
            if otp_obj.is_expired():
                raise ValidationError("OTP has expired. Please request a new one.")
            if otp_obj.otp_code != email_otp:
                raise ValidationError("Invalid OTP. Please check and try again.")
            # If OTP is valid, set email_verified to True
            cleaned_data["email_verified"] = True

        return cleaned_data
