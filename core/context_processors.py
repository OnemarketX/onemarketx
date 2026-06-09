from django.utils import timezone

from .models import (
    Notification,
    BroadcastMessage
)


def notification_data(request):

    
    # NOTIFICATIONS
    

    if request.user.is_authenticated:

        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        latest_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-id')[:5]

    else:

        unread_notifications = 0
        latest_notifications = []


    
    # BROADCASTS
    

    now = timezone.now()

    broadcasts = BroadcastMessage.objects.filter(
        is_active=True
    ).order_by(
        '-is_pinned',
        '-created_at'
    )

    active_broadcasts = []

    for broadcast in broadcasts:

        # Not started yet
        if (
            broadcast.start_date and
            broadcast.start_date > now
        ):
            continue

        # Expired
        if (
            broadcast.end_date and
            broadcast.end_date < now
        ):
            continue

        active_broadcasts.append(
            broadcast
        )


    return {

        
        'unread_notifications':
        unread_notifications,

        'latest_notifications':
        latest_notifications,

        
        'active_broadcasts':
        active_broadcasts[:3],

    }