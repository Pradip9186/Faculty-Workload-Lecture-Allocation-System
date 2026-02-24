from django.shortcuts import redirect
from django.conf import settings


class EnforceRootLoginMiddleware:
    """Redirect unauthenticated requests to '/' to the login page.

    This middleware only handles the root path ('/'). It allows other
    paths (including '/login/', '/signup/', '/logout/', and '/admin/') to
    proceed normally.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only enforce for the root path
        if request.path == '/' and not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next=/")

        return self.get_response(request)
