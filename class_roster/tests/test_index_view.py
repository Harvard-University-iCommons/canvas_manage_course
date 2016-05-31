from __future__ import unicode_literals
import uuid
from unittest import skip

from django.test import RequestFactory, TestCase
from django.core import urlresolvers
from django.test.utils import override_settings
from mock import patch, Mock, ANY, call, MagicMock

from class_roster.views import (
    index,
    _get_course_instances,
    _get_course_title,
    _get_roster_url)

mock_api_token = 'test-token'
mock_api_host = 'fake://path/'


@skip("Issues with django_auth_lti's reverse() in the index.html template")
@patch.multiple('django_auth_lti.patch_reverse', reverse=Mock(side_effect=urlresolvers.reverse))
@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class IndexViewTests(TestCase):
    longMessage = True

    def setUp(self):
        self.course_instance_id = uuid.uuid4().int
        self.user_id = uuid.uuid4().hex
        self.resource_link_id = uuid.uuid4().hex

        query = {'resource_link_id': self.resource_link_id}

        self.request = Mock(session={}, method='GET',
                            resource_link_id=self.resource_link_id)
        # self.request = RequestFactory().get('/fake-path', query)
        self.request.user = Mock(is_authenticated=Mock(return_value=True))
        self.request.resource_link_id = self.resource_link_id
        self.request.LTI = {
            'lis_course_offering_sourcedid': self.course_instance_id,
            'lis_person_sourcedid': self.user_id,
            # 'resource_link_id': self.resource_link_id,
        }

    @patch('class_roster.views._get_course_title')
    @patch('class_roster.views._get_roster_url')
    @patch('class_roster.views._get_course_instances')
    def test_index_template_no_data(self, mock_course_instances,
                                    mock_roster_url, mock_course_title,
                                    *args, **kwargs):

        mock_course_instances.return_value = []

        response = index(self.request)

        self.assertEqual(mock_course_instances.call_count, 0)
        self.assertEqual(mock_roster_url.call_count, 0)

        self.assertContains(response, 'No class roster could be found')

    @skip('todo')
    def test_index_template_without_xlisting(self):
        pass

    @skip('todo')
    def test_index_template_with_xlisting(self):
        pass


@override_settings(ICOMMONS_REST_API_HOST=mock_api_host)
@override_settings(ICOMMONS_REST_API_TOKEN=mock_api_token)
@override_settings(ICOMMONS_REST_API_SKIP_CERT_VERIFICATION=True)
class GetCourseInstancesTests(TestCase):
    longMessage = True
    course_instance_id = '123456'

    class ResponseStub():
        def __init__(self, status_code=200):
            self.status_code = status_code

    @patch('class_roster.views.logger.error')
    @patch('class_roster.views.requests.get')
    def test_no_course_instance_found(self, mock_get, mock_log):

        mock_get.return_value = MagicMock(status_code=404)

        result = _get_course_instances(self.course_instance_id)

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_log.call_count, 1)
        self.assertEqual(result, [])

    @patch('class_roster.views.logger.error')
    @patch('class_roster.views.requests.get')
    def test_invalid_course_instance_response(self, mock_get, mock_log):

        mock_json = Mock(return_value={})
        mock_get.return_value = Mock(status_code=200, json=mock_json)

        result = _get_course_instances(self.course_instance_id)

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_log.call_count, 1)
        self.assertEqual(result, [])

    @patch('class_roster.views.logger.error')
    @patch('class_roster.views.requests.get')
    def test_valid_response(self, mock_get, mock_log):

        mock_course_instance = {
            'course_instance_id': 1,
            'secondary_xlist_instances': []
        }
        mock_json = Mock(return_value=mock_course_instance)
        mock_get.return_value = Mock(status_code=200, json=mock_json)

        result = _get_course_instances(self.course_instance_id)

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_log.call_count, 0)
        self.assertEqual(result, [mock_course_instance])

    @patch('class_roster.views.logger.error')
    @patch('class_roster.views.requests.get')
    def test_valid_response_with_xlist_instances(self, mock_get, mock_log):

        mock_secondary_1 = {'course_instance_id': 1}
        mock_secondary_2 = {'course_instance_id': 2}
        mock_course_instance = {
            'course_instance_id': 3,
            'secondary_xlist_instances': [mock_secondary_1, mock_secondary_2]
        }
        mock_json = Mock(return_value=mock_course_instance)
        mock_get.return_value = Mock(status_code=200, json=mock_json)

        result = _get_course_instances(self.course_instance_id)

        self.assertEqual(mock_get.call_count, 1)
        self.assertEqual(mock_log.call_count, 0)
        self.assertEqual(result, [mock_course_instance, mock_secondary_1, mock_secondary_2])


class GetCourseTitleTests(TestCase):

    def test_extra_whitespace_short_title_and_section(self):
        test_course_instance = {
            'section': ' 001 ',
            'short_title': '\tABC123\n',
        }
        response = _get_course_title(test_course_instance)

        self.assertEqual(response, 'ABC123 001')

    def test_no_titles_or_section(self):
        """
        if preferred data for building the course link text is blank, we fall
        back on data we always expect to have
        """
        test_course_instance = {
            'course': {'registrar_code': 'ABCDE12345', 'school_id': 'fake'},
        }
        response = _get_course_title(test_course_instance)

        self.assertEqual(response, 'FAKE ABCDE12345')

    def test_short_title(self):
        test_course_instance = {
            'section': '001',
            'short_title': 'ABC123',
        }
        response = _get_course_title(test_course_instance)

        self.assertEqual(response, 'ABC123 001')

    def test_title(self):
        test_course_instance = {
            'section': ' 001 ',
            'title': 'Another Boring Course',
        }
        response = _get_course_title(test_course_instance)

        self.assertEqual(response, 'Another Boring Course 001')


@override_settings(CLASS_ROSTER={})  # todo: fill in this mock settings dict
class GetRosterURLTests(TestCase):

    @skip('for now')
    def test_blank_data(self):
        """
        if data required to build the roster link is missing, we log it and
        return None to indicate to calling procedure that we could not build it
        """
        pass

    @skip('for now')
    def test_good_data(self):
        pass
