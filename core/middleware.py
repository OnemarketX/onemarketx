from django.shortcuts import redirect
from .utils import get_site_settings


class MaintenanceModeMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        settings_obj = get_site_settings()

        allowed_paths = [
            '/future-admin-tools/',
            '/admin/',
            '/login/',
        ]


        if (
            settings_obj.maintenance_mode
            and not request.user.is_superuser
        ):

            allowed = False

            for path in allowed_paths:

                if request.path.startswith(path):
                    allowed = True
                    break

            if not allowed:
                return redirect('/maintenance/')


        response = self.get_response(request)

        return response