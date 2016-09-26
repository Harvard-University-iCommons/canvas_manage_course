import copy
import uuid

import oauthlib

import requests
from django.test import LiveServerTestCase
from mock import MagicMock, patch
from requests_oauthlib import OAuth1Session

from django_auth_lti import const


@patch.multiple('lti_school_permissions.decorators', is_allowed=MagicMock(return_value=True))
class LTIResourceLinkTests(LiveServerTestCase):
    '''
    Runs against a live server instance so we can use requests to test how
    the server behaves when interacting with multiple tabs in the same session.

    NOTE: The 'session.auth = None' lines are used to prevent the Oauth1Session
    objects from continuing to sign further requests.  LTI only calls for the
    launch to be signed.

    NOTE: The foo/bar oauth credentials are added in unit_test settings.
    '''
    longMessage = True

    def setUp(self):
        self.resource_link_id = uuid.uuid4().hex
        self.test_user = uuid.uuid4().hex
        self.params = {
            'custom_canvas_api_domain': 'canvas.harvard.edu',
            'custom_canvas_course_id': '5',
            'lis_course_offering_sourcedid': '5',
            'lti_message_type': 'basic-lti-launch-request',
            'lti_version': 'LTI-1p0',
            'resource_link_id': self.resource_link_id,
            'roles': ','.join([const.INSTRUCTOR, const.TEACHING_ASSISTANT,
                               const.ADMINISTRATOR, const.CONTENT_DEVELOPER]),
            'user_id': self.test_user,
        }


    @patch('canvas_manage_course.views.get_previous_isites')
    def test_lti_launch(self, mock_get_previous_isites):
        mock_get_previous_isites.returns = []

        # run the launch, verify we get redirected to a url ending in our
        # resource_link_id
        session = OAuth1Session(client_key='foo', client_secret='bar',
                                signature_type=oauthlib.oauth1.SIGNATURE_TYPE_BODY)
        url = self.live_server_url + '/lti_launch'
        response = session.post(url, data=self.params, allow_redirects=False)
        self.assertEqual(response.status_code, requests.codes.found)
        self.assertIn('sessionid', response.cookies)
        self.assertTrue(
            response.headers['location'].endswith(self.resource_link_id))

        # try following the redirect, we should get a 200
        session.auth = None
        response2 = session.get(response.headers['location'])
        mock_get_previous_isites.assert_called_with(
            self.params['lis_course_offering_sourcedid'])
        self.assertEqual(response2.status_code, requests.codes.ok)

    @patch('canvas_manage_course.views.get_previous_isites')
    def test_multiple_lti_launch(self, mock_get_previous_isites):
        mock_get_previous_isites.returns = []

        # run the launch, verify we get redirected to a url ending in our
        # resource_link_id
        session = OAuth1Session(client_key='foo', client_secret='bar',
                                signature_type=oauthlib.oauth1.SIGNATURE_TYPE_BODY)
        url = self.live_server_url + '/lti_launch'

        # launch "tab 1" and verify success
        response1 = session.post(url, data=self.params, allow_redirects=False)
        self.assertEqual(response1.status_code, requests.codes.found)
        self.assertIn('sessionid', response1.cookies)
        self.assertTrue(
            response1.headers['location'].endswith(self.resource_link_id))

        # launch "tab 2" and verify success
        params2 = copy.deepcopy(self.params)
        params2['resource_link_id'] = uuid.uuid4().hex
        response2 = session.post(url, data=params2, allow_redirects=False)
        self.assertEqual(response2.status_code, requests.codes.found)
        self.assertIn('sessionid', response2.cookies)
        self.assertTrue(
            response2.headers['location'].endswith(params2['resource_link_id']))

        # follow the "tab 2" redirect and verify 200
        session.auth = None
        response3 = session.get(response2.headers['location'])
        mock_get_previous_isites.assert_called_with(
            self.params['lis_course_offering_sourcedid'])
        self.assertEqual(response3.status_code, requests.codes.ok)

        # follow the "tab 1" redirect and verify 200
        response4 = session.get(response1.headers['location'])
        self.assertEqual(response3.status_code, requests.codes.ok)
