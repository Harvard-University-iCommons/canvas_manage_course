import unittest

from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, DEFAULT, Mock

from manage_sections.views import create_section_form


@patch.multiple('manage_sections.views', render=DEFAULT)
@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class CreateSectionFormTest(unittest.TestCase):
    """
    Tests for the create_section_form view.
    """
    longMessage = True

    def setUp(self):
        self.canvas_course_id = 1234
        self.section_id = 5678
        self.sis_section_id = '92345'
        self.resource_link_id = '1a3b4c5dsdfsdf345345'
        self.lis_course_offering_sourcedid = '92345'
        self.request = RequestFactory().get('/fake-path')
        self.request.user = Mock(name='user_mock')
        self.request.user.is_authenticated.return_value = True
        self.request.LTI = {
            'custom_canvas_course_id': self.canvas_course_id,
            'roles': [const.INSTRUCTOR],
            'resource_link_id': self.resource_link_id,
            'lis_course_offering_sourcedid': self.lis_course_offering_sourcedid
        }
        self.sections_current_match = [{
            'id': self.section_id,
            'name': 'a section',
            'sis_section_id': self.sis_section_id,
            'enrollments': []
        }]
        self.sections_current_prefix_match = [{
            'id': self.section_id,
            'name': 'a section',
            'sis_section_id': "ci:%s" % self.sis_section_id,
            'enrollments': []
        }]
        self.sections = [{
            'id': self.section_id,
            'name': 'Z section',
            'enrollments': []
        }, {
            'id': self.section_id + 1,
            'name': 'a section',
            'enrollments': []
        }]

    @patch('manage_sections.views.is_sis_section')
    @patch('manage_sections.views.is_enrollment_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success(self, get_section_replacement, is_enrollment_section_mock, is_sis_mock,
                                                   render):
        """ Create Section Form View should render form page upon success"""
        request = self.request
        get_section_replacement.return_value = self.sections
        is_enrollment_section_mock.return_value = False
        is_sis_mock.return_value = False
        response = create_section_form(request)
        section_list = sorted(self.sections, key=lambda x: x[u'name'].lower())
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': section_list,
            'sisenrollmentsections': []
        })

    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success_when_current_match(self, get_section_replacement, render):
        """ Create Section Form View should return success when current ci matches"""
        request = self.request
        get_section_replacement.return_value = self.sections_current_match
        response = create_section_form(request)
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': [],
            'sisenrollmentsections': self.sections_current_match
        })

    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success_when_ci_match(self, get_section_replacement, render):
        """ Create Section Form View should return success when ci prefix"""
        request = self.request
        request.LTI['lis_course_offering_sourcedid'] = "ci:%s" % self.sis_section_id
        get_section_replacement.return_value = self.sections_current_prefix_match
        response = create_section_form(request)
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': [],
            'sisenrollmentsections': self.sections_current_prefix_match
        })

    @patch('manage_sections.views.is_sis_section')
    @patch('manage_sections.views.is_enrollment_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success_when_primary_match(self, get_section_replacement, is_enrollment_section_mock,
                                                                      is_sis_mock, render):
        """ Create Section Form View should return success when numeric"""
        request = self.request
        get_section_replacement.return_value = self.sections
        is_enrollment_section_mock.return_value = True
        is_sis_mock.return_value = False
        response = create_section_form(request)
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': [],
            'sisenrollmentsections': self.sections
        })

    @patch('manage_sections.views.is_sis_section')
    @patch('manage_sections.views.is_enrollment_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success_when_registrar_match(self, get_section_replacement, is_enrollment_section_mock,
                                                                        is_sis_mock, render):
        """ Create Section Form View should return success when numeric"""
        request = self.request
        get_section_replacement.return_value = self.sections
        is_enrollment_section_mock.return_value = False
        is_sis_mock.return_value = True
        response = create_section_form(request)
        section_list = sorted(self.sections, key=lambda x: x[u'name'].lower())
        self.assertIn('registrar_section_flag', get_section_replacement.return_value[0])
        self.assertEqual(get_section_replacement.return_value[0]['registrar_section_flag'], True)
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': section_list,
            'sisenrollmentsections': []
        })

    @patch('manage_sections.views.is_sis_section')
    @patch('manage_sections.views.is_enrollment_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_sections')
    def test_section_form_view_template_on_success_when_non_sis_match(self, get_section_replacement, is_enrollment_section_mock,
                                                                      is_sis_mock, render):
        """ Create Section Form View should return success when no sis"""
        request = self.request
        get_section_replacement.return_value = self.sections
        is_enrollment_section_mock.return_value = False
        is_sis_mock.return_value = False
        response = create_section_form(request)
        section_list = sorted(self.sections, key=lambda x: x[u'name'].lower())
        render.assert_called_with(request, 'manage_sections/create_section_form.html', {
            'sections': section_list,
            'sisenrollmentsections': []
        })

    @patch('manage_sections.views.logger.error')  # Mock the logger to keep log messages off the console.
    def test_section_form_view_status_without_custom_canvas_course_id(self, log_replacement, render):
        """
        Create Section Form view should return error page if there was no
        lis_course_offering_sourcedid
        """
        request = self.request
        request.LTI['lis_course_offering_sourcedid'] = None
        create_section_form(request)
        render.assert_called_with(request, 'manage_sections/error.html', status=500)

    @patch('manage_sections.views.logger.error')  # Mock the logger to keep log messages off the console.
    @patch('lti_permissions.decorators', is_allowed=Mock(return_value=False))
    def test_section_form_view_when_not_permitted(self, lti_decorator, log_replacement, render):
        """
        When the user does not have the right permissions, verify that it
        redirects to unauthorized page
        """
        request = self.request
        request.LTI['lis_course_offering_sourcedid'] = "ci:%s" % self.sis_section_id

        response = create_section_form(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/not_authorized')

