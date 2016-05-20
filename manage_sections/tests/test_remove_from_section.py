import unittest

from canvas_sdk.exceptions import CanvasAPIError
from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, Mock

from manage_sections.views import remove_from_section


# Basic stub for the user object that is sent as part of a Django request
class UserStub:
    authenticated = True

    def __init__(self, auth=True):
        self.authenticated = auth

    def is_authenticated(self):
        return self.authenticated


# Stub of the request object that is passed to a view method.
class RequestStub:
    method = 'POST'
    user = UserStub(auth=True)

    def __init__(self):
        self.LTI = {
            'roles': [],
            'custom_canvas_course_id': '12345',
            'lis_course_offering_sourcedid': '92345',
            'resource_link_id': 'b45f234f'
        }

    def set_roles(self, roles):
        self.LTI['roles'] = roles


class SectionRemoveFromSectionViewTest(unittest.TestCase):
    longMessage = True

    def remove_from_section_stub(self):
        self.factory = RequestFactory()
        req = RequestStub()
        req.set_roles([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
        req.method = "POST"
        req.POST = {'user_section_id': '1234', 'section_id': 12}
        req.LTI['custom_canvas_course_id'] = '123456'
        return req

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.logger.error')
    def test_render_from_remove_from_section_on_empty_user_section_id(self, log_replacement, render_replacement):
        """ Check render on remove from section test with no user section id """
        request = self.remove_from_section_stub()
        del request.POST['user_section_id']
        response = remove_from_section(request)
        self.assertEqual(response.status_code, 500)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.logger.error')
    def test_status_from_remove_from_section_on_blank_user_section_id(self, log_replacement, render_replacement):
        """ Check status on remove from section test with bad user section id """
        request = self.remove_from_section_stub()
        request.POST['user_section_id'] = ''
        response = remove_from_section(request)
        self.assertEqual(response.status_code, 500)

    @patch('manage_sections.views.render')
    @patch('manage_sections.views.canvas_api_enrollments.conclude_enrollment')
    @patch('manage_sections.views.logger.error')
    def test_remove_from_section_conclude_enrollment_fails(self, log_replacement, conclude_enrollment_replacement,
                                                              render_replacement):
        """ Remove from section should return error if conclude_enrollment fails """
        request = self.remove_from_section_stub()
        conclude_enrollment_replacement.side_effect = CanvasAPIError
        response = remove_from_section(request)
        self.assertEqual(response.status_code, 500)

    @patch('manage_sections.views.canvas_api_enrollments.conclude_enrollment')
    @patch('manage_sections.views.logger.error')
    def test_remove_from_section_succeeds(self, log_replacement, conclude_enrollment_replacement):
        # Remove from section should return sucess status code on matching course id,
        # valid section, and successful deletion of user
        request = self.remove_from_section_stub()
        conclude_enrollment_replacement.return_value = Mock(json=lambda: {})
        response_json = {}
        response = remove_from_section(request)
        self.assertEqual(response.status_code, 200, "Incorrect code for validate_course=True ")
