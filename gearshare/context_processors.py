from django.conf import settings

def google_auth(request):
    return {
        'google_redirect_uri': settings.GOOGLE_OAUTH_REDIRECT
    }