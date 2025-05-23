from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.conf import settings
from django.contrib import messages

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs that don't require authentication
        exempt_urls = [
            reverse('login:login'),
            '/admin/login/',
            '/admin/',
            '/static/',
            '/media/',
        ]

        # Check if the URL is valid
        try:
            resolve(request.path)
        except Resolver404:
            if request.user.is_authenticated:
                messages.warning(request, 'The page you tried to access does not exist.')
                return redirect('login:dashboard')
            else:
                messages.warning(request, 'Please login to access the application.')
                return redirect('login:login')

        # Check authentication for non-exempt URLs
        if not any(request.path.startswith(url) for url in exempt_urls):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login to access the application.')
                return redirect(settings.LOGIN_URL)

        response = self.get_response(request)
        return response 
