"""Implement custom activity streams."""
from actstream.managers import ActionManager, stream


class CustomStreamManager(ActionManager):
    """Defines custom activity streams, such as personal notifications."""

    verb_commented = 'commented'
    verb_liked = 'liked'
    verb_replied = 'replied to'

    @stream
    def notifications(self, user, **kwargs):
        """Retrieve all personal notifications."""
        return self.filter(
            notifications__user=user,
            **kwargs,
        ).prefetch_related('notifications')
