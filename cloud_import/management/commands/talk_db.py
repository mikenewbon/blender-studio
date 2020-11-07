from django.core.management.base import BaseCommand
from django.db import connection
from dataclasses import dataclass


@dataclass
class Revision:
    title: str
    topic: str
    content: str
    description: str
    header: str
    thumbnail: str


class Command(BaseCommand):
    help = 'Import file for films'

    def fetch_latest_revision(self, post_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT title, topic, content, description, header, thumbnail "
                "FROM blog_revision WHERE post_id = %s ORDER BY date_updated DESC",
                [post_id],
            )
            row = cursor.fetchone()

        return Revision(*row)

    def handle(self, *args, **options):
        a = self.fetch_latest_revision(4)
        print(a)
