from __future__ import unicode_literals
import uuid
from unittest import skip

from django.test import RequestFactory, TestCase
from django.core import urlresolvers
from django.test import override_settings
from mock import patch, Mock, ANY, call, MagicMock

from class_roster.views import (
    index,
    _get_course_instances,
    _get_course_title,
    _get_roster_url)

mock_api_token = 'test-token'
mock_api_host = 'fake://path/'
test_roster_url_settings = {
    'sis_roster': {
        'base_url': 'https://',
        'base_path': 'fake.path/',
        'base_query': '?a=b&c=d&',
        'static_path': 'sub/dirs/',
    }
}


@skip("TLT-2635: Issues with django_auth_lti's reverse() in the index.html template")
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


class GetRosterURLTests(TestCase):

    def setUp(self):
        self.test_dynamic_query_template = 'INSTRUCTOR_ID={}&CLASS_NBR={}&STRM={}'
        test_settings = test_roster_url_settings['sis_roster']
        self.test_roster_url_base = '{}{}{}{}'.format(
            test_settings['base_url'],
            test_settings['base_path'],
            test_settings['static_path'],
            test_settings['base_query'])
        self.test_user_id = '12345678'

    @patch('class_roster.views.logger.error')
    def test_blank_data(self, mock_logger_error):
        """
        if data required to build the roster link is missing, we log it and
        return None to indicate to calling procedure that we could not build it
        """
        test_course_instances = [
            {
                'cs_class_number': '56789',
                'term': {'calendar_year': '2016'}
            },
            {
                'cs_class_number': None,
                'term': {'calendar_year': '2016', 'term_code': '2'}
            },
            {
                'cs_class_number': '56789',
                'term': {'term_code': '2'}
            },
            {
                'term': {'calendar_year': '2016', 'term_code': '2'}
            },
        ]
        for test_course_instance in test_course_instances:
            response = _get_roster_url(test_course_instance, self.test_user_id)
            self.assertIsNone(response)
            self.assertEqual(mock_logger_error.call_count, 1)
            mock_logger_error.reset_mock()

    @skip('TLT-2635: Issues with override_settings() not being applied before the code runs')
    @override_settings(CLASS_ROSTER=test_roster_url_settings)
    @patch('class_roster.views.logger.error')
    def test_good_data(self, mock_logger_error):
        test_course_instance = {
            'cs_class_number': '56789',
            'term': {'calendar_year': '2016', 'term_code': '2'}
        }

        expected_dynamic_query = self.test_dynamic_query_template.format(
            self.test_user_id,
            test_course_instance['cs_class_number'],
            '2162')
        expected_url = '{}{}'.format(self.test_roster_url_base,
                                     expected_dynamic_query)

        response = _get_roster_url(test_course_instance, self.test_user_id)

        self.assertEqual(response, expected_url)
        self.assertEqual(mock_logger_error.call_count, 0)
