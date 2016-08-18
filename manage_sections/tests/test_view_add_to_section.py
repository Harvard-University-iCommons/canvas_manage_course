import unittest
import json
import copy

from django_auth_lti import const
from manage_sections.views import add_to_section
from mock import patch, ANY, DEFAULT, Mock

from canvas_sdk.exceptions import CanvasAPIError


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
    session = {}
    user = UserStub(auth=True)

    def __init__(self):
        self.LTI = {
            'custom_canvas_course_id': '12345',
            'roles': [],
            'lis_course_offering_sourcedid': '92345',
            'resource_link_id': 'b45f234f'
        }

    def set_roles(self, roles):
        self.LTI['roles'] = roles

@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class SectionAddToSectionViewTest(unittest.TestCase):
    """
    Test cases for add to section
    """
    longMessage = True

    def setUp(self):
        self.add_to_section_stub_body = {
            "section_id": 1694,
            "users_to_add": [
                {
                    "enrollment_user_id": "79610",
                    "enrollment_role_id": "2",
                    "enrollment_type": "TeacherEnrollment"
                },
                {
                    "enrollment_user_id": "104779",
                    "enrollment_role_id": "2",
                    "enrollment_type": "TeacherEnrollment"
                }
            ]
        }

    def add_to_section_stub(self):
        req = RequestStub()
        req.resource_link_id = 'b45f234f'
        req.set_roles([const.INSTRUCTOR, const.TEACHING_ASSISTANT, const.ADMINISTRATOR, const.CONTENT_DEVELOPER])
        req.method = "POST"
        req.body = json.dumps(self.add_to_section_stub_body)
        return req

    @patch('manage_sections.views.canvas_api_enrollments.enroll_user_sections')
    @patch('manage_sections.views.logger.error')
    def test_add_to_section_success_on_enroll_user_sections_returning_200(self, logger_replacement,
                                                                          add_to_section_replacement):
        """ Assert that when SDK method returns success, then remove_section returns correct status code """
        request = self.add_to_section_stub()
        response = add_to_section(request)
        add_to_section_replacement.return_value.status_code = 200
        self.assertEqual(response.status_code, 200)

    @patch('manage_sections.views.canvas_api_enrollments.enroll_user_sections')
    def test_add_to_section_makes_sdk_call_with_correct_params(self, add_to_section_replacement):
        """
        Assert that the enrollments.enroll_user_sections SDK method is being called with the expected parameters
        """
        request = self.add_to_section_stub()
        add_to_section(request)
        user_to_add = self.add_to_section_stub_body['users_to_add'][0]
        add_to_section_replacement.assert_any_call(
            ANY,
            self.add_to_section_stub_body['section_id'],
            user_to_add['enrollment_user_id'],
            enrollment_type=user_to_add['enrollment_type'],
            enrollment_role_id=user_to_add['enrollment_role_id'],
            enrollment_enrollment_state='active',
        )

    @patch('manage_sections.views.canvas_api_enrollments.enroll_user_sections')
    @patch('manage_sections.views.logger.error')
    def test_add_to_section_raises_exception_on_missing_section_id(self, log_replacement, add_to_section_replacement):
        """ Assert that add_to_section returns a 500 response on missing section id   """
        request = self.add_to_section_stub()
        request_body = copy.deepcopy(self.add_to_section_stub_body)
        del request_body['section_id']
        request.body = json.dumps(request_body)
        response = add_to_section(request)
        assert log_replacement.called
        self.assertEqual(response.status_code, 500)

    @patch('manage_sections.views.canvas_api_enrollments.enroll_user_sections')
    @patch('manage_sections.views.logger.error')
    def test_add_to_section_raises_exception_on_missing_enrollment_id(self, log_replacement,
                                                                      add_to_section_replacement):
        """ Assert that add_to_section returns a 500 response when the enrollment_user_id is missing """
        request = self.add_to_section_stub()
        request_body = copy.deepcopy(self.add_to_section_stub_body)
        del request_body['users_to_add'][0]['enrollment_user_id']
        request.body = json.dumps(request_body)
        response = add_to_section(request)
        assert log_replacement.called
        self.assertEqual(len(json.loads(response.content)['failed']), 1)

    @patch('manage_sections.views.canvas_api_enrollments.enroll_user_sections')
    @patch('manage_sections.views.logger.error')
    def test_add_to_section_logs_exception_on_failure_status_code(
            self, log_replacement, add_to_section_replacement):
        """ Assert that logger is logging an exception when return from backend
        is status code 4XX """
        request = self.add_to_section_stub()
        add_to_section_replacement.side_effect = CanvasAPIError()
        response = add_to_section(request)
        assert log_replacement.called
        self.assertEqual(len(json.loads(response.content)['failed']), 2)
