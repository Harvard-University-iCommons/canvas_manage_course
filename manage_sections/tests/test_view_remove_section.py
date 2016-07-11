import unittest

from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, Mock, DEFAULT

from manage_sections.views import remove_section


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
            'roles': [],
            'custom_canvas_course_id': '12345',
            'lis_course_offering_sourcedid': '92345'
        }

    def set_roles(self, roles):
        self.LTI['roles'] = roles

@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class RemoveSectionsTest(unittest.TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.section = {
            'id': 123,
            'name': 'Test Name',
            'sis_section_id': '123'
        }

    # Test cases for delete section
    def delete_section_stub(self):
        req = RequestStub()
        req.set_roles([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
        req.method = "POST"
        req.section_id = '371'
        req.sis_section_id = '123'
        req.resource_link_id = '987'
        req.LTI['lis_course_offering_sourcedid'] = '123456'
        req.LTI['resource_link_id'] = '987'
        req.LTI['custom_canvas_course_id'] = '111'
        return req

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_helper_sections.delete_section')
    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    def test_remove_section_success_on_delete_section_returning_200(self, get_section_replacement,
                                                                    is_editable_section_replacement,
                                                                    delete_section_replacement, render_replacement):
        """ Assert that when SDK method returns sucess, then remove_section returns correct status code """
        request = self.delete_section_stub()
        get_section_replacement.return_value = self.section
        is_editable_section_replacement.return_value = True
        delete_section_replacement.return_value = self.section
        response = remove_section(request, request.section_id)
        self.assertEqual(response.status_code, 200)

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')
    def test_remove_section_for_primary_section_fails(self, log_replacement, get_section_replacement,
                                                      is_editable_section_replacement):
        """ Assert that status code 422 is returned when section is a primary section   """
        request = self.delete_section_stub()
        request.sis_section_id = '123456'
        get_section_replacement.return_value = DEFAULT
        is_editable_section_replacement.return_value = False
        response = remove_section(request, request.section_id)
        self.assertEqual(response.status_code, 422)

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')
    def test_remove_section_for_non_editable_section_fails(self, log_replacement, get_section_replacement,
                                                           is_editable_section_replacement):
        """ Status 422 should be returned for a primary or registrar section """
        request = self.delete_section_stub()
        request.sis_section_id = '123456'
        get_section_replacement.return_value = DEFAULT
        is_editable_section_replacement.return_value = False
        response = remove_section(request, request.section_id)
        self.assertEqual(response.status_code, 422)

    @patch('manage_sections.views.canvas_api_helper_sections.delete_section')
    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    @patch('manage_sections.views.logger.error')
    def test_remove_section_logs_exception_on_failure_status_code(self, log_replacement, get_section_replacement,
                                                                  is_editable_section_replacement,
                                                                  delete_section_replacement):
        """ Assert that logger is logging an exception when return from backend  is status code 4XX """
        request = self.delete_section_stub()
        get_section_replacement.return_value = self.section
        is_editable_section_replacement.return_value = True
        delete_section_replacement.return_value = None
        response = remove_section(request, request.section_id)
        assert log_replacement.called

    @patch('manage_sections.views.canvas_api_helper_sections.delete_section')
    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.canvas_api_helper_sections.get_section')
    # @patch('manage_sections.views.logger.error')
    def test_remove_section_throws_exception_when_get_section_fails(self, get_section_replacement,
                                                                    is_editable_section_replacement,
                                                                    delete_section_replacement):
        """ Assert that  an exception is raised when get_section_by_id fails making SDK call """
        request = self.delete_section_stub()
        get_section_replacement.return_value = None
        response = remove_section(request, request.section_id)
        self.assertEqual(response.status_code, 500)
