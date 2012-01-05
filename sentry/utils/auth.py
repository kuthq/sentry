"""
sentry.utils.auth
~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
import hmac
from django.utils.hashcompat import sha_constructor
from sentry.conf import settings


def get_signature(message, timestamp, key=None):
    if not key:
        key = settings.KEY
    return hmac.new(key, '%s %s' % (timestamp, message), sha_constructor).hexdigest()


def get_auth_header(signature, timestamp, client, api_key=None):
    header = [
        ('sentry_timestamp', timestamp),
        ('sentry_signature', signature),
        ('sentry_client', client),
    ]
    if api_key:
        header.append(('sentry_key', api_key))

    return 'Sentry %s' % ', '.join('%s=%s' % (k, v) for k, v in header)


def parse_auth_header(header):
    return dict(map(lambda x: x.strip().split('='), header.split(' ', 1)[1].split(',')))
