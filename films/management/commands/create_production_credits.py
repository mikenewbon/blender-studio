# noqa: D100

from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from films.models import Film, FilmProductionCredit


class Command(BaseCommand):
    help = 'Generate production credits for a film.'

    def add_arguments(self, parser):
        parser.add_argument('film_slug', type=str, help='Film slug, e.g. sprite-fright')
        parser.add_argument('start_date', type=str, help='Date formatted YYYY-MM-DD')

    def generate_credits(self, options):
        """Populate Production Credits list for a film.

        Fetch all active subscribers and ensure that they kept their subscription active
        from a specific moment in time until now. If so, add grant them a Production Credit.
        """
        try:
            film = Film.objects.get(slug=options['film_slug'])
        except Film.DoesNotExist:
            raise CommandError('Film "%s" does not exist' % options['film_slug'])
        start_date_str = options['start_date']
        user = get_user_model()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        current_tz = timezone.get_current_timezone()
        start_date_localized = current_tz.localize(start_date)
        users = user.objects.filter(
            subscription__status='active', subscription__started_at__lt=start_date_localized,
        )
        self.stdout.write(self.style.SUCCESS("All active users: %i" % users.count()))
        time_difference = relativedelta(timezone.now(), start_date_localized)
        time_difference_months = time_difference.months
        self.stdout.write(self.style.SUCCESS("Month threshold: %i" % time_difference_months))

        valid_credits = 0
        for u in users:
            s = u.subscription_set.filter(status='active').first()
            if s.interval_unit == 'year' and s.intervals_elapsed >= 1:
                valid_credits += 1
            elif (
                s.interval_unit == 'month'
                and s.interval_length == 6
                and s.intervals_elapsed >= (time_difference_months / 6)
            ):
                valid_credits += 1
            elif (
                s.interval_unit == 'month'
                and s.interval_length == 3
                and s.intervals_elapsed >= (time_difference_months / 3)
            ):
                valid_credits += 1
            elif (
                s.interval_unit == 'month'
                and s.interval_length == 1
                and s.intervals_elapsed >= time_difference_months
            ):
                valid_credits += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Non valid credit: {s.started_at} - {s.interval_unit} - {s.intervals_elapsed} - {u.id}"
                    )
                )
                continue

            FilmProductionCredit.objects.get_or_create(film=film, user=u)

        self.stdout.write(self.style.SUCCESS("Valid credits: %i" % valid_credits))

    def handle(self, *args, **options):
        self.generate_credits(options)
