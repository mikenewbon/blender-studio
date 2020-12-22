from typing import List, Set, Union, Any
import logging
import re

from actstream import action
from actstream.models import Action
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
import users.tasks as tasks

User = get_user_model()
logger = logging.getLogger(__name__)
re_cloud_role_name_cleanup = re.compile('^cloud_')


def clean_role_names(names: Union[List[str], Set[str]]) -> Set[str]:
    """Remove Blender Cloud prefixes from given Blender ID roles.

    Blender Cloud strips "cloud_" prefix from the role names before storing them,
    so to keep group/role naming consistent, Blender Studio shall do the same.
    """
    return {re_cloud_role_name_cleanup.sub('', name) for name in names}


def set_groups_from_roles(user: User, group_names: Union[List[str], Set[str]]) -> None:
    """Set user groups to match the given list of `group_names`.

    If a group with a particular name doesn't exist, create one.
    Ignores Blender Studio own internal groups that start with "_".
    """
    group_names = clean_role_names(group_names)
    current_groups = user.groups.all()
    # Blender ID role names map onto group names, with exception of group name starting with "_"
    current_group_names = {group.name for group in current_groups if not group.name.startswith('_')}

    names_to_add_to = group_names - current_group_names
    # Look up all groups this user is now being added to and make sure they actually exist
    groups_to_add_to = []
    for group_name in names_to_add_to:
        group, _ = Group.objects.get_or_create(name=group_name)
        groups_to_add_to.append(group)

    if groups_to_add_to:
        logger.warning(f'Adding user #{user.pk} to the following groups: {groups_to_add_to}')
        user.groups.add(*groups_to_add_to)

    names_to_remove_from = current_group_names - group_names
    # Remove user from the groups that are no longer in the user info payload
    groups_to_remove_from = [
        group for group in current_groups if group.name in names_to_remove_from
    ]
    if groups_to_remove_from:
        logger.warning(f'Removing user #{user.pk} from the groups: {groups_to_remove_from}')
        user.groups.remove(*groups_to_remove_from)

    subscriber_status_changed = 'subscriber' in (*names_to_add_to, *names_to_remove_from)
    if subscriber_status_changed:
        tasks.handle_is_subscribed_to_newsletter(pk=user.pk)


def duplicate_action_exists(actor: User, target: Any, verb: str, action_object: Any = None) -> bool:
    """Check if user activity on the given objects exists already.

    Useful in cases when creating activity record doesn't make sense,
    such as when a person "unliked" a post and then "liked" it again.
    """
    qs = Action.objects.filter(
        actor_object_id=actor.pk,
        verb=verb,
    )
    if target:
        target_ct = ContentType.objects.get_for_model(type(target))
        qs = qs.filter(
            target_content_type=target_ct,
            target_object_id=target.pk,
        )
    if action_object:
        action_object_ct = ContentType.objects.get_for_model(type(action_object))
        qs = qs.filter(
            action_object_content_type=action_object_ct,
            action_object_object_id=action_object.pk,
        )

    return qs.exists()


def create_action_from_like(actor: User, target: Any, action_object: Any = None) -> None:
    """Creates an activity action for a Like."""
    verb_liked = 'liked'
    if duplicate_action_exists(
        actor=actor, target=target, action_object=action_object, verb=verb_liked
    ):
        # Avoid generating duplicate activity for repeated likes
        return

    action.send(actor, verb=verb_liked, target=target, action_object=action_object, public=False)
