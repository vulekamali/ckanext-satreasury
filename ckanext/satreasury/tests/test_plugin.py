from ckanext.satreasury.plugin import SATreasuryDatasetPlugin

import json
from mock import Mock, patch, PropertyMock, MagicMock
from functools import partial
import unittest
import responses
import ckan.model as model


TRAVIS_ENDPOINT = "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal"
TRAVIS_COMMIT_MESSAGE = 'Rebuild with new/modified dataset'
TRAVIS_WEB_URL = "https://travis-ci.org/vulekamali/static-budget-portal/builds/"


class TestNotify(unittest.TestCase):

    def setUp(self):
        self.entity = Mock(spec=model.Package)
        self.entity.owner_org = PropertyMock(return_value=True)
        self.plugin = SATreasuryDatasetPlugin()

    @responses.activate
    @patch('ckanext.satreasury.plugin.travis.build_trigger_enabled', return_value=True)
    @patch('ckanext.satreasury.plugin.ckan_helpers.flash_success')
    def test_notify_already_building(self, flash_success_mock, build_trigger_enabled_mock):
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/builds",
                     json={'builds': [{'@type': 'build', 'commit': {'message': TRAVIS_COMMIT_MESSAGE}, '@href': '/build/535878234', '@representation': 'minimal', 'id': 535878234, 'number': '1593', 'state': 'created', 'duration': 49, 'event_type': 'push', 'previous_state': 'passed', 'pull_request_title': None, 'pull_request_number': None, 'started_at': '2019-05-22T16:52:20Z', 'finished_at': '2019-05-22T16:53:09Z', 'private': False}]}, status=200,
                     content_type='application/json')
            self.plugin.notify(self.entity, None)
            message = "vulekamali will be updated in less than an hour. <a href='https://travis-ci.org/vulekamali/static-budget-portal/builds/535878234' >Check progress of the update process.</a>"
            flash_success_mock.assert_called_with(message, allow_html=True)

    @responses.activate
    @patch('ckanext.satreasury.plugin.travis.build_trigger_enabled', return_value=True)
    @patch('ckanext.satreasury.plugin.ckan_helpers.flash_success')
    def test_notify_build_triggered(self, flash_success_mock, build_trigger_enabled_mock):
        self.get_builds_calls = 0

        def get_builds_callback(request):
            if self.get_builds_calls == 0:
                self.get_builds_calls += 1
                response_body = {'builds': []}
                return (200, {}, json.dumps(response_body))
            else:
                response_body = {'builds': [{'@type': 'build', 'commit': {'message': TRAVIS_COMMIT_MESSAGE}, '@href': '/build/535878234', '@representation': 'minimal', 'id': 535878234, 'number': '1593', 'state': 'created',
                                             'duration': 49, 'event_type': 'push', 'previous_state': 'passed', 'pull_request_title': None, 'pull_request_number': None, 'started_at': '2019-05-22T16:52:20Z', 'finished_at': '2019-05-22T16:53:09Z', 'private': False}]}
                return (200, {}, json.dumps(response_body))

        with responses.RequestsMock() as rsps:
            # TODO add response for get request
            # if isinstance(entity, model.Package) and entity.owner_org:
            rsps.add_callback(responses.GET, "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/builds",
                              callback=get_builds_callback,
                              content_type='application/json')
            rsps.add(responses.POST, "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/requests",
                     json={'builds': []}, status=200,
                     content_type='application/json')
            self.plugin.notify(self.entity, None)
            message = "vulekamali will be updated in less than an hour. <a href='https://travis-ci.org/vulekamali/static-budget-portal/builds/535878234' >Check progress of the update process.</a>"
            flash_success_mock.assert_called_with(message, allow_html=True)
