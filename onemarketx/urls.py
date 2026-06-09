from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('secure-control-portal/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('accounts.urls')),
]