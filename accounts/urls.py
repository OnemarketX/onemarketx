from django.urls import path
from .views import (
    register_view,
    verify_email_view,
    login_view,
    logout_view,
    forgot_password_view,
    verify_reset_view,
    new_password_view
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('verify-email/', verify_email_view, name='verify_email'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('verify-reset/', verify_reset_view, name='verify_reset'),
    path('new-password/', new_password_view,name='new_password'),
]