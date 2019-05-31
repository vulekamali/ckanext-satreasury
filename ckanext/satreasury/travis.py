import logging
import os

import requests

from ckan.common import config
import ckan.plugins.toolkit as tk

TRAVIS_ENDPOINT = "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal"
TRAVIS_COMMIT_MESSAGE = 'Rebuild with new/modified dataset'
TRAVIS_WEB_URL = "https://travis-ci.org/vulekamali/static-budget-portal/builds/"
TRAVIS_TOKEN = os.environ.get(
    'CKAN_SATREASURY_TRAVIS_TOKEN',
    config.get('satreasury.travis_token')
)
TRAVIS_HEADERS = {
    "Travis-API-Version": "3",
    "Authorization": "token %s" % TRAVIS_TOKEN,
}

log = logging.getLogger(__name__)


def build_trigger_enabled():
    return tk.asbool(os.environ.get(
        'CKAN_SATREASURY_BUILD_TRIGGER_ENABLED',
        config.get('satreasury.build_trigger_enabled', True)
    ))


def queued_build_filter(build):
    return build['commit']['message'] == TRAVIS_COMMIT_MESSAGE


def get_builds_from_created_request(build_request):
    updated_build_request = get_request(build_request['request']['id'])
    return updated_build_request['builds']


def get_request(request_id):
    r = requests.get(TRAVIS_ENDPOINT + '/request/' +
                     str(request_id), headers=TRAVIS_HEADERS)
    return r.json()


def get_queued_builds():
    params = {
        "build.state": "created",
        "branch.name": "master",
    }
    r = requests.get(TRAVIS_ENDPOINT + '/builds',
                     headers=TRAVIS_HEADERS, params=params)
    r.raise_for_status()
    return list(filter(queued_build_filter, r.json()['builds']))


def trigger_build():
    payload = {
        'request': {
            'message': TRAVIS_COMMIT_MESSAGE,
            'branch': 'master',
            'config': {
                'merge_mode': 'deep_merge',
                'branches': {'except': []},
                'env': {'REMOTE_TRIGGER': 'true'}
            },
        }
    }
    r = requests.post(TRAVIS_ENDPOINT + '/requests',
                      json=payload, headers=TRAVIS_HEADERS)
    log.debug(r.text)
    r.raise_for_status()
    return r.json()


def get_build_url(build):
    url = TRAVIS_WEB_URL + str(build['id'])
    return url
