from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                user_role = request.user.profile.role
            except Exception:
                return redirect('login')
            if user_role in roles:
                return view_func(request, *args, **kwargs)
            return redirect('access_denied')
        return wrapper
    return decorator


def permission_required(perm_field):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                role = request.user.profile.role
            except Exception:
                return redirect('login')

            # Admin always has access
            if role == 'admin':
                return view_func(request, *args, **kwargs)

            # Check waiter permission
            from .models import RolePermission
            perms = RolePermission.get()
            if getattr(perms, perm_field, False):
                return view_func(request, *args, **kwargs)

            return redirect('access_denied')
        return wrapper
    return decorator