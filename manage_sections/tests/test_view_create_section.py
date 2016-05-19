from unittest import TestCase

from django_auth_lti import const
from mock import MagicMock
from mock import patch, ANY

from manage_sections.views import create_section


# Basic stub for the user object that is sent as part of a Django request
class UserStub:
    authenticated = True

    def __init__(self, auth=True):
        self.authenticated = auth

    def is_authenticated(self):
        return self.authenticated


# Stub of the request object that is passed to a view method.
class RequestStub:
    method = 'GET'
    session = {}
    user = UserStub(auth=True)

    def __init__(self):
        self.LTI = {
            'custom_canvas_course_id': '12345',
            'roles': [],
            'lis_course_offering_sourcedid': '92345'
        }

    def set_roles(self, roles):
        self.LTI['roles'] = roles


class SectionCreateSectionViewTest(TestCase):
    longMessage = True

    def setUp(self):
        self.canvas_course_id = 1234
        self.section_id = 5678
        self.sis_section_id = 8989
        self.resource_link_id = '1a3b4c5dsdfsdf345345'
        self.section = {
            'section_id': 123,
            'name': 'Test Name',
            'sis_section_id': '123'
        }

    def create_section_request_stub(self):
        req = RequestStub()
        req.set_roles([const.INSTRUCTOR])
        req.method = "POST"
        req.POST = {
            'section_name_input': 'Section Name'
        }
        req.LTI = {
            'custom_canvas_course_id': self.canvas_course_id,
            'roles': [const.INSTRUCTOR],
            'resource_link_id': '1a3b4c5dsdfsdf345345',
        }
        return req

    @patch('manage_sections.views.render')
    def test_create_section_status_on_missing_section_name(self, render_replacement):
        """Create Section should return 400 if the section name is missing"""
        request = self.create_section_request_stub()
        del request.POST['section_name_input']
        create_section(request)
        render_replacement.assert_called_with(request, ANY, ANY, status=400)

    @patch('manage_sections.views.render')
    def test_create_section_status_on_empty_section_name(self, render_replacement):
        """Create Section should return 400 if the section name is empty"""
        request = self.create_section_request_stub()
        request.POST['section_name_input'] = ""
        create_section(request)
        render_replacement.assert_called_with(request, ANY, ANY, status=400)

    @patch('manage_sections.views.render')
    def test_create_section_template_error_on_empty_section_name(self, render_replacement):
        """Create Section should render an error message if the section name is empty"""
        request = self.create_section_request_stub()
        request.POST['section_name_input'] = ""
        create_section(request)
        render_replacement.assert_called_with(request, 'manage_sections/create_section_form.html', ANY, status=ANY)

    @patch('manage_sections.views.render')
    def test_create_section_status_on_whitespace_section_name(self, render_replacement):
        """Create Section should return 400 if the section name contains only whitespace"""
        request = self.create_section_request_stub()
        request.POST['section_name_input'] = "       "
        response = create_section(request)
        render_replacement.assert_called_with(request, ANY, ANY, status=400)

    @patch('manage_sections.views.render')
    def test_create_section_template_error_on_whitespace_section_name(self, render_replacement):
        """Create Section should render an error message if the section name contains only whitespace"""
        request = self.create_section_request_stub()
        request.POST['section_name_input'] = "       "
        response = create_section(request)
        render_replacement.assert_called_with(request, 'manage_sections/create_section_form.html', ANY, status=ANY)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_instance_id_string_type_to_canvas(self, get_create_section, render_replacement):
        """Create Section passes the correct string-typed instance ID to make the canvas call"""
        request = self.create_section_request_stub()
        create_section(request)
        get_create_section.assert_called_with(self.canvas_course_id, ANY)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_section_name_to_canvas(self, get_create_section, render_replacement):
        """Create Section passes the correct section name to make the canvas call"""
        request = self.create_section_request_stub()
        response = create_section(request)
        get_create_section.assert_called_with(self.canvas_course_id, request.POST['section_name_input'])
    
    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_section_name_whitespace_to_canvas(self, get_create_section, render_replacement):
        """Create Section trims extra whitespace before passing the section name to make the canvas call"""
        request = self.create_section_request_stub()
        request.POST['section_name_input'] = '   extra whitespace   '
        get_create_section.return_value = self.section
        response = create_section(request)
        get_create_section.assert_called_with(self.canvas_course_id, request.POST['section_name_input'].strip())

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_status_on_success(self, get_create_section, render_replacement):
        """Create Section returns 200 on success"""
        request = self.create_section_request_stub()
        get_create_section.return_value = self.section
        response = create_section(request)
        render_replacement.assert_called_with(ANY, 'manage_sections/section_list.html', ANY)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_status_on_fail_return_500(self, get_create_section, render_replacement):
        """Create Section returns 500 on failure"""
        request = self.create_section_request_stub()
        get_create_section.return_value = None
        response = create_section(request)
        render_replacement.assert_called_with(ANY, 'manage_sections/create_section_form.html', ANY, status=500)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_template_on_success(self, get_create_section, render_replacement):
        """Create Section renders the create section form on success"""
        request = self.create_section_request_stub()
        response = create_section(request)
        render_replacement.assert_called_with(request, 'manage_sections/section_list.html', ANY)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_created_the_section_with_the_correct_data(self, get_create_section, render_replacement):
        """Create Section renders the correct section with the correct section data"""
        request = self.create_section_request_stub()
        get_create_section.return_value = {'sis_section_id': '123', 'enrollment_count': 0, 'section_id': 123, 'name': 'Test Name'}
        response = create_section(request)
        render_replacement.assert_called_with(request, 'manage_sections/section_list.html', {
            'section': get_create_section.return_value
        })

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.create_section')
    def test_create_section_set_enrollment_called_with_0_value(self, get_create_section, render_replacement):
        """Test that create_section responds correctly"""
        request = self.create_section_request_stub()
        section_mock = MagicMock(name='section_mock')
        get_create_section.return_value = section_mock
        response = create_section(request)
        section_mock.__setitem__.assert_called_with('enrollment_count', 0)
