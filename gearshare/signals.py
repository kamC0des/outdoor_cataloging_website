from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from .models import Profile
import logging
from django.contrib.auth.signals import user_logged_in

logger = logging.getLogger(__name__)

@receiver(post_save, sender=SocialAccount)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure that when a SocialAccount is created, the related Profile is updated or created.
    """
    user = instance.user
    extra_data = instance.extra_data

    if not extra_data:
        logger.warning("No extra_data found in SocialAccount.")
        return

    logger.debug(f"Google OAuth extra_data: {extra_data}")

    # Ensure profile exists
    profile, _ = Profile.objects.get_or_create(user=user)

    # Update profile with OAuth data
    profile.real_name = extra_data.get('name', user.email.split('@')[0])
    profile.email = extra_data.get('email', user.email)
    profile.profile_picture = extra_data.get('picture', 'profiles/default.jpg')
    profile.save()
@receiver(user_logged_in)
def check_user_overdue_items(sender, request, user, **kwargs):
    try:
        profile = user.profile
        if profile.check_overdue_items():
            # Optional: Add a message to notify the user
            from django.contrib import messages
            messages.warning(request, "Points were deducted for overdue items")
    except Profile.DoesNotExist:
        pass