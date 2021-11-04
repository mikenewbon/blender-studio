"""
Import CloudFront logs into postgresql.

Use the following command to the info about progress and ETA:
    kill -SIGUSR1 $(ps aux | grep import_cloud | grep -v grep | awk '{print $2}')
"""
# from pprint import pprint
from datetime import timedelta, datetime
import gzip
import logging
import os
import os.path
import signal
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from psycopg2.extras import execute_values
import psycopg2

logger = logging.getLogger('write_stats')
logger.setLevel(logging.DEBUG)
User = get_user_model()
BATCH_SIZE = 5000
TABLE_NAME = 'cflogs'
varchar_len_max = 2000
field_defs = {
    # contains comma-separated IPs sometimes, cannot use cidr
    'c-ip': f'VARCHAR({varchar_len_max})',
    'c-port': 'integer',
    'cs(Cookie)': f'VARCHAR({varchar_len_max})',
    'cs(Host)': f'VARCHAR({varchar_len_max})',
    'cs(Referer)': f'VARCHAR({varchar_len_max})',
    'cs(User-Agent)': f'VARCHAR({varchar_len_max})',
    'cs-bytes': 'bigint',
    'cs-method': 'VARCHAR(7)',
    'cs-protocol': 'VARCHAR(5)',
    'cs-protocol-version': 'VARCHAR(8)',
    'cs-uri-query': 'VARCHAR(2000)',
    'cs-uri-stem': 'VARCHAR(256)',
    'date': 'date',
    # 'fle-encrypted-fields': b'-',
    # 'fle-status': b'-',
    'sc-bytes': 'bigint',
    'sc-content-len': 'bigint',
    'sc-content-type': f'VARCHAR({varchar_len_max})',
    'sc-range-end': 'bigint',
    'sc-range-start': 'bigint',
    'sc-status': 'smallint',
    # 'ssl-cipher': b'TLS_AES_128_GCM_SHA256',
    # 'ssl-protocol': b'TLSv1.3',
    'time': 'time',
    'time-taken': 'integer',  # must mult by 10**3
    'time-to-first-byte': 'integer',  # must mult by 10**3
    'x-edge-detailed-result-type': 'VARCHAR(20)',
    'x-edge-location': 'VARCHAR(10)',
    'x-edge-request-id': 'VARCHAR(60)',
    'x-edge-response-result-type': 'VARCHAR(20)',
    'x-edge-result-type': 'VARCHAR(20)',
    # contains comma-separated IPs sometimes, cannot use cidr
    'x-forwarded-for': f'VARCHAR({varchar_len_max})',
    'x-host-header': f'VARCHAR({varchar_len_max})',
}


def _cf_field_to_table(value: str) -> str:
    return slugify(value.replace('-', '_'))


class Command(BaseCommand):
    """Do subj."""

    files_handled = 0
    table_fields = None
    insert_q = None
    data = []

    def _handle_line(self, line):
        if line.startswith(b'#Version') or line.startswith(b'#Fields'):
            return
        values = {field: line.split(b'\t')[self.fields.index(field)] for field in self.fields}
        status = values['sc-status']
        if status != b'200':
            return

        q_values = []
        for k in self.fields:
            if k not in field_defs:
                continue
            v = values[k].decode()
            if v in ('-', '-\n'):
                v = None
            elif k in ('time-taken', 'time-to-first-byte'):
                v = float(v) + 1000
            else:
                v = v[:varchar_len_max]
            q_values.append(v)
        self.data.append(q_values)

        if len(self.data) > BATCH_SIZE:
            assert all(
                len(_) == len(self.table_fields) for _ in self.data
            ), f'{len(self.data[0])} == {len(self.table_fields)}'
            # pprint(self.data)
            execute_values(self.cursor, self.insert_q, self.data)
            self.connection.commit()
            self.data = []

    def _handle_gz(self, file_path):
        self.line_count = 0
        with gzip.open(file_path, 'r') as f:
            for line in f:
                if line.startswith(b'#Fields'):
                    if not self.table_fields:
                        self.fields = line.decode().split()[1:]
                        self.table_fields = [
                            _cf_field_to_table(f) for f in self.fields if f in field_defs
                        ]
                        # placeholders = ','.join(['%s'] * len(self.table_fields))
                        self.insert_q = (
                            f"INSERT INTO cflogs ({','.join(self.table_fields)}) VALUES %s"
                        )
                    continue
                self._handle_line(line)
                self.line_count += 1
        self.files_handled += 1

    def _print_summary(self):
        logger.info('Files handled: %s/%s', self.files_handled, self.files_total)
        try:
            eta = timedelta(
                seconds=(
                    ((self.files_total - self.files_handled) / self.files_handled)
                    * (time.time() - self.start_t)
                )
            )
            logger.info(
                'ETA %s (%s%%), %s',
                eta,
                int(self.files_handled / self.files_total * 100),
                datetime.now() + eta,
            )
        except Exception:
            pass

    def _drop_table(self):
        self.cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
        self.connection.commit()

    def _create_table(self):
        dbname = settings.DATABASES['default']['NAME']
        user = settings.DATABASES['default']['USER']
        password = settings.DATABASES['default']['PASSWORD']
        self.connection = psycopg2.connect(f'dbname={dbname} user={user} password={password}')
        self.cursor = self.connection.cursor()

        self._drop_table()

        fields = ','.join(
            [_cf_field_to_table(name) + ' ' + datatype for name, datatype in field_defs.items()]
        )
        table_def = f"CREATE TABLE {TABLE_NAME} ({fields});"
        self.cursor.execute(table_def)
        self.connection.commit()

    def handle(self, *args, **options):
        """Do subj."""
        self._create_table()

        path = '../cloudfront-logs/cloudfront'
        all_files = sorted(os.listdir(path))
        self.files_total = len(all_files)

        def receiveSignal(signalNumber, frame):
            self._print_summary()
            return

        signal.signal(signal.SIGHUP, receiveSignal)
        signal.signal(signal.SIGUSR1, receiveSignal)
        signal.signal(signal.SIGUSR2, receiveSignal)

        self.start_t = time.time()
        for _file in all_files:
            try:
                file_path = os.path.join(str(path), _file)
                self._handle_gz(file_path)
            except KeyboardInterrupt:
                self._print_summary()
                break
            except Exception:
                logger.exception('Stopped at %s:%s', file_path, self.line_count)
                self._print_summary()
                raise
