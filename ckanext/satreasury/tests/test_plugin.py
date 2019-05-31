import json
import unittest
from functools import partial

import ckan.model as model
import responses
from ckanext.satreasury.plugin import SATreasuryDatasetPlugin
from mock import MagicMock, Mock, PropertyMock, patch

TRAVIS_ENDPOINT = "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal"
TRAVIS_COMMIT_MESSAGE = 'Rebuild with new/modified dataset'
TRAVIS_WEB_URL = "https://travis-ci.org/vulekamali/static-budget-portal/builds/"


class TestNotifyMethod(unittest.TestCase):
    @responses.activate
    def setUp(self):
        self.entity = Mock(spec=model.Package)
        self.entity.owner_org = PropertyMock(return_value=True)
        self.plugin = SATreasuryDatasetPlugin()

        flash_success_patch = patch(
            'ckanext.satreasury.plugin.ckan_helpers.flash_success')
        self.flash_success_mock = flash_success_patch.start()
        flash_error_patch = patch(
            'ckanext.satreasury.plugin.ckan_helpers.flash_error')
        self.flash_error_mock = flash_error_patch.start()
        self.addCleanup(flash_success_patch.stop)

    @patch(
        'ckanext.satreasury.plugin.travis.build_trigger_enabled',
        return_value=True)
    def test_notify_already_building(self, build_trigger_enabled_mock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/builds",
                json={
                    'builds': [
                        {
                            'id': 535878234,
                            'commit': {
                                'message': TRAVIS_COMMIT_MESSAGE
                            },
                        }]},
                status=200,
                content_type='application/json')
            self.plugin.notify(self.entity, None)
            message = "vulekamali will be updated in less than an hour. <a href='https://travis-ci.org/vulekamali/static-budget-portal/builds/535878234' >Check progress of the update process.</a>"
            self.flash_success_mock.assert_called_with(
                message, allow_html=True)

    @patch(
        'ckanext.satreasury.plugin.travis.build_trigger_enabled',
        return_value=True)
    def test_notify_build_triggered(self, build_trigger_enabled_mock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/builds",
                json={
                    'builds': []},
                status=200,
                content_type='application/json')
            rsps.add(
                responses.POST,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/requests",
                json={
                    'request': {
                        'id': 12345}},
                status=200,
                content_type='application/json')
            rsps.add(
                responses.GET,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/request/12345",
                json={
                    'builds': [
                        {
                            'commit': {
                                'message': TRAVIS_COMMIT_MESSAGE},
                            'id': 535878234,
                        }]},
                status=200,
                content_type='application/json')

            self.plugin.notify(self.entity, None)
            message = "vulekamali will be updated in less than an hour. <a href='https://travis-ci.org/vulekamali/static-budget-portal/builds/535878234' >Check progress of the update process.</a>"
            self.flash_success_mock.assert_called_with(
                message, allow_html=True)

    @patch(
        'ckanext.satreasury.plugin.travis.build_trigger_enabled',
        return_value=True)
    def test_notify_build_trigger_errored(self, build_trigger_enabled_mock):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/builds",
                json={
                    'builds': []},
                status=200,
                content_type='application/json')
            rsps.add(
                responses.POST,
                "https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/requests",
                json={
                    'request': {
                        'id': 12345}},
                status=500,
                content_type='application/json')

            self.plugin.notify(self.entity, None)
            message = 'An error occurred when updating the static site data. Technical details: 500 Server Error: Internal Server Error for url: https://api.travis-ci.org/repo/vulekamali%2Fstatic-budget-portal/requests'
            self.flash_error_mock.assert_called_with(message)

    @patch(
        'ckanext.satreasury.plugin.travis.build_trigger_enabled',
        return_value=False)
    def test_notify_build_not_enabled(self, build_trigger_enabled_mock):
        self.plugin.notify(self.entity, None)
        self.assertTrue(True)
