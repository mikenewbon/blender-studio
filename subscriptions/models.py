from typing import Optional, Dict, Any
import logging

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, transaction

import looper.models

from common import mixins
import subscriptions.validators

User = get_user_model()
logger = logging.getLogger(__name__)


class Team(mixins.CreatedUpdatedMixin, models.Model):
    name = models.CharField(max_length=256, default='', blank=True)
    users = models.ManyToManyField(User, through='TeamUsers', related_name='teams')
    subscription = models.OneToOneField(
        looper.models.Subscription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='team',
    )

    seats = models.IntegerField(
        blank=True,
        null=True,
        help_text='If set, limits the size of the team to this number',
    )
    emails = ArrayField(
        models.EmailField(max_length=254, blank=False),
        blank=True,
        default=list,
        null=True,
        help_text="Comma-separated list of team members' emails.",
    )
    email_domain = models.CharField(
        max_length=253,
        null=True,
        blank=True,
        help_text=(
            'Team email domain. If set to "my-awesome-team.org", everyone with an email'
            ' ending with "@my-awesome-team.org" will be considered a member of this team.'
            ' Domains of common email providers are not allowed.'
        ),
        validators=[subscriptions.validators.validate_email_domain],
    )
    invoice_reference = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text=(
            'Invoice reference, such as purchase order number. '
            'Included into newly generated invoices '
            '(changing this will not affect existing invoices).'
        ),
        validators=[subscriptions.validators.validate_invoice_reference],
    )

    def __str__(self) -> str:
        maybe_name = ''
        if self.name:
            maybe_name = f' ("{self.name}")'
        return f'<Team {self.subscription}{maybe_name}>'

    @property
    def manager(self) -> Optional[User]:
        """User who manages the team subscription."""
        return self.subscription.user if self.subscription_id else None

    def add(self, user: User) -> None:
        """Add given user to the team."""
        seats_taken = self.users.count()
        # Not adding the team manager to the team
        if user.pk == self.subscription.user_id:
            return
        if self.seats is not None and seats_taken >= self.seats:
            logger.warning(
                'Not adding user pk=%s to team pk=%s: %s out of %s seats taken',
                user.pk,
                self.pk,
                seats_taken,
                self.seats,
            )
            return
        logger.info('Adding user pk=%s to team pk=%s', user.pk, self.pk)
        with transaction.atomic():
            self.users.add(user)
            message = 'Added user pk={instance.id} to the team'
            looper.admin_log.attach_log_entry(self, message)

    def remove(self, user: User) -> None:
        """Remove given user from the team."""
        logger.info('Removing user pk=%s from team pk=%s', user.pk, self.pk)
        with transaction.atomic():
            self.users.remove(user)
            message = f'Removed user pk={user.pk} from the team'
            looper.admin_log.attach_log_entry(self, message)

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)

    def _clean_invoice_reference(self) -> None:
        self.invoice_reference = self.invoice_reference and self.invoice_reference.strip()
        if self.invoice_reference == '':
            self.invoice_reference = None

    def _clean_email_domain(self) -> None:
        if self.email_domain:
            self.email_domain = self.email_domain.strip()
            self.email_domain = self.email_domain.lower()
        if self.email_domain == '':
            self.email_domain = None

    def clean(self):
        # Make sure there are no duplicate emails and sort them
        self.emails = sorted([unique_email for unique_email in {email for email in self.emails}])
        super().clean()

        self._clean_email_domain()
        self._clean_invoice_reference()

        if self.seats is not None and len(self.emails) > self.seats:
            raise ValidationError(
                {
                    'emails': (
                        f'Not enough seats ({self.seats})'
                        f' for the given number of team emails ({len(self.emails)})'
                    ),
                },
            )

    def to_dict(self) -> Dict[str, Any]:
        """Return team data as a dict, useful for preparing JSON API responses."""
        return {
            'email_domain': self.email_domain,
            'emails': self.emails,
            'invoice_reference': self.invoice_reference,
            'name': self.name,
            'seats': self.seats,
        }


class TeamUsers(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Team Users'
        verbose_name_plural = 'Team Users'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_users')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_users')

    def __str__(self) -> str:
        return f'<Team member: {self.user}>'


class TeamPlanProperties(mixins.CreatedUpdatedMixin, models.Model):
    class Meta:
        verbose_name = 'Team Plan Properties'
        verbose_name_plural = 'Team Plan Properties'

    plan = models.OneToOneField(
        looper.models.Plan, on_delete=models.CASCADE, related_name='team_properties'
    )
    seats = models.IntegerField(blank=True, null=True)

    def __str__(self) -> str:
        return f'<Team plan properties: {self.seats and self.seats or "unlimited"} seats>'
