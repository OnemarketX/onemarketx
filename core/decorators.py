from django.shortcuts import redirect
from django.contrib import messages


def superuser_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect('/login/')

        if not request.user.is_superuser:
            messages.error(
                request,
                "Owner access only."
            )
            return redirect('/dashboard/')

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


def staff_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect('/login/')

        if not request.user.is_staff:
            messages.error(
                request,
                "Staff access only."
            )
            return redirect('/dashboard/')

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper