from unittest import TestCase

from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, ANY, Mock, DEFAULT

from manage_sections.views import section_user_list
from test_utils import return_unmodified_input


@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
@patch.multiple('manage_sections.views.canvas_api_helper_enrollments', add_role_labels_to_enrollments=DEFAULT)
class SectionUserListViewTest(TestCase):
    longMessage = True

    def setUp(self):
        self.section = {
            'section_id': 123,
            'name': 'Test Name',
            'sis_section_id': '123'
        }
        self.canvas_course_id = 1234
        self.resource_link_id = '1a3b4c5dsdfsdf345345'
        self.request = RequestFactory().get('/fake-path')
        self.request.user = Mock(name='user_mock')
        self.request.user.is_authenticated.return_value = True
        self.request.section_id = 5678
        self.request.section_sis_id = 8989
        self.request.LTI = {
            'custom_canvas_course_id': self.canvas_course_id,
            'roles': [const.INSTRUCTOR],
            'resource_link_id': self.resource_link_id,
        }
        self.SOME_SECTION = {
            'course_id': 5947,
            'id': 17,
            'name': 'Sapna&#x27;s Reserves Course',
            'sis_section_id': '305841',
            'enrollments': []
        }

    def get_render_context_value(self, render_mock, context_key):
        """ Returns the value of the context dictionary key associated with the render mock object """
        context = render_mock.call_args[0][2]
        return context.get(context_key)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')  # Mock the logger to keep log messages off the console.
    def test_section_user_list_on_section_id_numeric_string(self, log_replacement, section_replacement,
                                                            render_replacement, add_role_labels_to_enrollments, **kwargs):
        """Display section_user_list page when section id is numeric string(sucessful test case) """
        request = self.request
        request.section_id = 123
        add_role_labels_to_enrollments.side_effect = return_unmodified_input
        section_replacement.return_value = self.SOME_SECTION
        response = section_user_list(request, request.section_id)
        render_replacement.assert_called_with(request, 'manage_sections/_section_userlist.html', {
            'allow_edit': ANY,
            'enrollments': ANY,
            'enroll_count': ANY,
            'section_id': int(request.section_id)
        })

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')  # Mock the logger to keep log messages off the console.
    def test_section_user_list_when_primary(self, log_replacement, section_replacement, is_editable_section,
                                            render_replacement, add_role_labels_to_enrollments, **kwargs):
        """Display section_user_list page when section id is numeric string(successful test case) """
        request = self.request
        request.section_id = '123'
        add_role_labels_to_enrollments.side_effect = return_unmodified_input
        section_replacement.return_value = self.SOME_SECTION
        is_editable_section.return_value = False
        response = section_user_list(request, request.section_id)
        self.assertEqual(self.get_render_context_value(render_replacement, 'allow_edit'), False)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')  # Mock the logger to keep log messages off the console.
    def test_section_user_list_when_not_primary(self, log_replacement, section_replacement, is_editable_section,
                                                render_replacement, add_role_labels_to_enrollments, **kwargs):
        """Display section_user_list page when section id is numeric string(sucessful test case) """
        request = self.request
        request.section_id = '123'
        add_role_labels_to_enrollments.side_effect = return_unmodified_input
        section_replacement.return_value = self.SOME_SECTION
        is_editable_section.return_value = True
        response = section_user_list(request, request.section_id)
        self.assertEqual(self.get_render_context_value(render_replacement, 'allow_edit'), True)
