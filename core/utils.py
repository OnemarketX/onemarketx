from .models import SiteSettings
from .models import OwnerActionLog
from .models import Notification

def get_site_settings():

    settings_obj, created = SiteSettings.objects.get_or_create(
        id=1
    )

    return settings_obj






def create_owner_log(
    owner,
    action,
    description,
    target_user=None
):

    OwnerActionLog.objects.create(
        owner=owner,
        action=action,
        description=description,
        target_user=target_user
    )


def create_notification(
    user,
    title,
    message
):

    Notification.objects.create(
        user=user,
        title=title,
        message=message
    )