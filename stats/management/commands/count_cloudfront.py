"""Aggregate views/downloads from CloudFront logs imported into postgresql."""
# from pprint import pprint
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify
import psycopg2

logger = logging.getLogger('write_stats')
logger.setLevel(logging.DEBUG)
TABLE_NAME = 'cflogs'

uniq_visitor = """
distinct(
   c_ip, csuser_agent, cs_protocol, cs_protocol_version, x_forwarded_for, cscookie
) as visitor
"""
film_asset_id = """
split_part(
    split_part(split_part(csreferer, '.org/', 2), '?asset=', 2), '&', 1) as film_asset_id
"""
common_filters = """
and cs_method = 'GET'
and csreferer not like '%studio.local%'
and sc_status = 200
and x_edge_response_result_type != 'Error'
"""
asset_visits_q = f"""
select film_asset_id, count(1) as count from (
    select {uniq_visitor}, {film_asset_id} from {TABLE_NAME}
    where csreferer != 'https://cloud.blender.org/'
          and csreferer like '%?asset=%'
          and csreferer not like '%?asset=undefined%'
          {common_filters}
) as tmp
group by film_asset_id
order by count desc;
"""

section_endpoint = """
split_part(
    split_part(
        split_part(csreferer, '.org/', 2), '?', 1), '&', 1
) as section_endpoint
"""
section_visits_q = f"""
select section_endpoint, count(1) as count from (
    select {uniq_visitor}, {section_endpoint} from {TABLE_NAME}
    where csreferer != 'https://cloud.blender.org/'
          and csreferer like '%/training/%'
          and csreferer not like '%/chapter/%'
          and csreferer not like '%/chapters/%'
          and csreferer not like '%/pages/%'
          {common_filters}
) as tmp
where section_endpoint like 'training/%/_%' group by section_endpoint
order by count desc;
"""

source_hash = "split_part(cs_uri_stem, '/', 3) as source_hash"
source_downloads_q = f"""
select source_hash, count(1) as count from (
    select {uniq_visitor}, {source_hash} from {TABLE_NAME}
    where cs_uri_stem like '/__/%/%.%'
        and csreferer not like '%studio.local%'
        and cs_uri_query like '%Expires%Signature%'
        {common_filters}
) as tmp
group by source_hash
order by count desc;
"""


def _cf_field_to_table(value: str) -> str:
    return slugify(value.replace('-', '_'))


class Command(BaseCommand):
    """Do subj."""

    def _connect(self):
        dbname = settings.DATABASES['default']['NAME']
        user = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']
        self.connection = psycopg2.connect(f'dbname={dbname} user={user} password={password}')
        self.cursor = self.connection.cursor()

    def _write_film_asset_view_counts(self):
        logger.info('Running the following q: %s', asset_visits_q)
        self.cursor.execute(asset_visits_q)

        with open('cf_film_asset_view_counts.csv', 'w+') as f:
            res = self.cursor.fetchall()
            logger.info('Writing results into %s', f.name)
            for pk, view_count in res:
                f.write(f'"{pk}";"{view_count}"\n')

    def _write_training_section_view_counts(self):
        logger.info('Running the following q: %s', section_visits_q)
        self.cursor.execute(section_visits_q)

        with open('cf_training_section_view_counts.csv', 'w+') as f:
            res = self.cursor.fetchall()
            logger.info('Writing results into %s', f.name)
            for endpoint, view_count in res:
                f.write(f'"{endpoint}";"{view_count}"\n')

    def _write_source_downloads(self):
        logger.info('Running the following q: %s', source_downloads_q)
        self.cursor.execute(source_downloads_q)

        with open('cf_source_download_counts.csv', 'w+') as f:
            res = self.cursor.fetchall()
            logger.info('Writing results into %s', f.name)
            for source_hash, download_count in res:
                f.write(f'"{source_hash}";"{download_count}"\n')

    def handle(self, *args, **options):
        """Do subj."""
        self._connect()

        self._write_film_asset_view_counts()

        self._write_training_section_view_counts()

        self._write_source_downloads()
