import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout 
from django.utils import timezone
from datetime import timedelta
import random
from datetime import timedelta


from .forms import RegisterForm

User = get_user_model()


def register_view(request):

    # referral from URL example: /register/?ref=ABCD1234
    ref_code = request.GET.get("ref", "")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = False

            # email verification code
            code = str(random.randint(100000, 999999))
            user.verification_code = code

            # referral logic
            referral_input = form.cleaned_data.get("referral")

            if referral_input:
                try:
                    referrer = User.objects.get(
                        referral_code=referral_input
                    )
                    user.referred_by = referrer
                except User.DoesNotExist:
                    pass

            user.save()

            # send verification email
            send_mail(
                "OneMarketX Verification Code",
                f"Your verification code is {code}",
                "supportonemarketx@gmail.com",
                [user.email],
                fail_silently=False
            )

            # store email in session
            request.session["verify_email"] = user.email

            messages.success(
                request,
                "Verification code sent to your email."
            )

            return redirect("/verify-email/")

        else:
            messages.error(
                request,
                "Please correct the errors below."
            )

    else:
        # prefill referral field from URL
        form = RegisterForm(
            initial={"referral": ref_code}
        )

    return render(
        request,
        "register.html",
        {"form": form}
    )


def verify_email_view(request):

    email = request.session.get("verify_email")

    if not email:
        return redirect("/register/")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return redirect("/register/")

    if request.method == "POST":

        code = request.POST.get("code", "").strip()

        if code == user.verification_code:
            user.is_verified = True
            user.is_active = True
            user.verification_code = ""
            user.save()

            messages.success(
                request,
                "Email verified successfully."
            )

            return redirect("/login/")

        else:
            messages.error(
                request,
                "Invalid verification code."
            )

    return render(
        request,
        "verify_email.html"
    )


def login_view(request):

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")

        # try username first
        user = authenticate(
            request,
            username=username_or_email,
            password=password
        )

        # if username fails, try email
        if user is None:
            try:
                found_user = User.objects.get(email=username_or_email)
                user = authenticate(
                    request,
                    username=found_user.username,
                    password=password
                )
            except User.DoesNotExist:
                user = None

        if user is not None:

            # ACCOUNT SUSPENSION LOCK
            if user.is_suspended:
                messages.error(
                    request,
                    "Your account has been suspended. Contact support."
                )
                return redirect("/login/")

            # EMAIL VERIFICATION LOCK
            if not user.is_verified:
                messages.error(
                    request,
                    "Please verify your email first."
                )
                return redirect("/login/")

            login(request, user)

            messages.success(
                request,
                "Login successful."
            )

            return redirect("/dashboard/")

        else:
            messages.error(
                request,
                "Invalid username/email or password."
            )

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("/login/")




# FORGOT PASSWORD

def forgot_password_view(request):

    if request.method == "POST":

        email = request.POST.get("email").strip()

        try:
            user = User.objects.get(email=email)

            code = str(
                random.randint(100000, 999999)
            )

            request.session["reset_email"] = email
            request.session["reset_code"] = code
            request.session["reset_expiry"] = (
                timezone.now() +
                timedelta(minutes=10)
            ).isoformat()

            send_mail(
                "OneMarketX Password Reset",
                f"Your reset code is: {code}",
                "supportonemarketx@gmail.com",
                [email],
                fail_silently=False
            )

            messages.success(
                request,
                "Reset code sent successfully."
            )

            return redirect('/verify-reset/')

        except User.DoesNotExist:

            messages.error(
                request,
                "No account found with that email."
            )

    return render(
        request,
        "forgot_password.html"
    )



# VERIFY RESET CODE

def verify_reset_view(request):

    if not request.session.get("reset_email"):
        return redirect('/forgot-password/')

    if request.method == "POST":

        code = request.POST.get("code").strip()

        saved_code = request.session.get(
            "reset_code"
        )

        expiry = request.session.get(
            "reset_expiry"
        )

        expiry_time = timezone.datetime.fromisoformat(
            expiry
        )

        if timezone.now() > expiry_time:

            messages.error(
                request,
                "Reset code expired."
            )

            return redirect('/forgot-password/')

        if code == saved_code:

            request.session["reset_verified"] = True

            return redirect('/new-password/')

        else:

            messages.error(
                request,
                "Invalid reset code."
            )

    return render(
        request,
        "verify_reset.html"
    )



# SET NEW PASSWORD

def new_password_view(request):

    if not request.session.get(
        "reset_verified"
    ):
        return redirect('/forgot-password/')

    if request.method == "POST":

        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if password != confirm:

            messages.error(
                request,
                "Passwords do not match."
            )

            return redirect('/new-password/')

        email = request.session.get(
            "reset_email"
        )

        user = User.objects.get(email=email)

        user.set_password(password)
        user.save()

        request.session.flush()

        messages.success(
            request,
            "Password reset successful."
        )

        return redirect('/login/')

    return render(
        request,
        "new_password.html"
    )

    
