from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    referral = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'country']

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")

        return email

    def clean_referral(self):
        code = self.cleaned_data.get('referral')

        if code:
            if not User.objects.filter(referral_code=code).exists():
                raise forms.ValidationError("Invalid referral code.")

        return code

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")

        return cleaned