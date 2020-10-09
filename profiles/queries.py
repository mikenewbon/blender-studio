from typing import List, Set, Union
import logging

from django.contrib.auth.models import User, Group

logger = logging.getLogger(__name__)


def set_groups(user: User, group_names: Union[List[str], Set[str]]) -> None:
    """Set user groups to match the given list of `group_names`.

    If a group with a particular name doesn't exist, create one.
    """
    group_names = set(group_names)
    current_groups = user.groups.all()
    current_group_names = {group.name for group in current_groups}

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
