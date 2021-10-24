# noqa: D100

from django.core.management.base import BaseCommand, CommandError

from films.models import Film, FilmProductionCredit


class Command(BaseCommand):
    help = 'Generate production credits text for a film.'

    def add_arguments(self, parser):
        parser.add_argument('film_slug', type=str, help='Film slug, e.g. sprite-fright')

    def handle(self, *args, **options):
        try:
            film = Film.objects.get(slug=options['film_slug'])
        except Film.DoesNotExist:
            raise CommandError('Film "%s" does not exist' % options['film_slug'])

        credits = FilmProductionCredit.objects.filter(
            film=film, is_public=True, user__full_name__isnull=False
        )

        credits_upper = sorted([credit.user.full_name.upper() for credit in credits])

        lines = []
        line = ''
        for credit in credits_upper:
            formatted_name = credit
            if formatted_name.startswith('_'):
                continue
            if line and line[0] != formatted_name[0]:
                line += "\n\n"
                lines.append(line)
                line = ''

            if line != '':
                formatted_name = f' • {formatted_name}'
            line += formatted_name
            if len(line) > 200:
                line += "\n"
                lines.append(line)
                line = ''

        if line:
            lines.append(line)

        with open('credits.txt', 'w') as out:
            out.writelines(lines)
