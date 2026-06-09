from django.urls import path
from . import views
from .views import (
    owner_dashboard_view,
    owner_analytics_view,
    finance_panel_view,
    users_management_view,
    user_detail_view,
)

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('faq/', views.faq, name='faq'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('deposit/', views.deposit_view, name='deposit'),
    path('withdraw/', views.withdraw_view, name='withdraw'),
    path('referrals/', views.referrals_view, name='referrals'),
    path('investments/', views.investments_view, name='investments'),
    path('transactions/', views.transactions_view, name='transactions'),
    path('owner-dashboard/', owner_dashboard_view, name='owner_dashboard'),
    path('owner-analytics/', owner_analytics_view, name='owner_analytics'),
    path('finance-panel/', finance_panel_view, name='finance_panel'),
    path('owner-users/' , users_management_view, name='owner_users'),
    path('owner-user/<int:user_id>/' , user_detail_view, name='owner_user_detail'),
    path('future-admin-tools/', views.future_admin_tools_view,name='future_admin_tools'),
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path('broadcast-message/', views.broadcast_message_view, name='broadcast_message'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('read-notification/<int:notification_id>/', views.read_notification_view, name='read_notification'),
    path('read-all-notifications/', views.read_all_notifications_view, name='read_all_notifications'),
    path('owner-action-logs/', views.owner_action_logs_view, name='owner_action_logs'),
    path('owner-broadcasts/', views.owner_broadcasts_view, name='owner_broadcasts'),
    path('settings/', views.settings_view, name='settings'),
    path('verify-email-change/', views.verify_email_change_view, name='verify_email_change'),
    path('verify-password-change/', views.verify_password_change_view, name='verify_password_change'),
    path('resend-email-change-code/', views.resend_email_change_code, name='resend_email_change_code'),
    path('resend-password-change-code/', views.resend_password_change_code, name='resend_password_change_code'),
    path('kyc/', views.kyc_view, name='kyc'),
    path(
    'owner-kyc/',
    views.owner_kyc_view,
    name='owner_kyc'
),

path(
    'owner-kyc/<int:kyc_id>/',
    views.owner_kyc_detail_view,
    name='owner_kyc_detail'
),
]