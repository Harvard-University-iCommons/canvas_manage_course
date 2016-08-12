from django.test import RequestFactory
from django.test import TestCase
from django_auth_lti import const
from mock import patch

from manage_sections.utils import (
    is_enrollment_section,
    is_credit_status_section,
    is_sis_section,
    validate_course_id,
)


class CourseInstanceStub:
    """
    Stub out a course instance object
    """
    def __init__(self, is_enrollment_section=False):
        self.is_enrollment_section = is_enrollment_section


class IsPrimaryUtilsTest(TestCase):
    longMessage = True

    def setUp(self):
        self.section_id = 5678
        self.prim_section = {
            "course_id": 5947,
            "id": 17,
            "name": "Sapna&#x27;s Reserves Course",
            "sis_section_id": "305841"

        }
        self.registrar_section = {
            "course_id": 5948,
            "id": 17,
            "name": "Sapnas Reserves Course",
            "sis_section_id": "ext:305841_role_1"
        }

        self.reg_section = {
            "course_id": 5947,
            "id": 434,
            "name": "dummy test",
            "sis_section_id": "dog"
        }


    @patch('manage_sections.utils.CourseInstance.objects.get')
    def test_is_enrollment_section_true_for_int_sis_id(self, ci_mock):
        """
        Test that when an integer sis id is passed the method returns true
        """
        ci_mock.return_value = CourseInstanceStub(is_enrollment_section=True)
        res = is_enrollment_section(self.prim_section['sis_section_id'])
        self.assertTrue(res, 'Expected is_enrollment_section() to return True for course_instance with section_type E')

    @patch('manage_sections.utils.CourseInstance.objects.get')
    def test_is_enrollment_section_false_for_non_int_sis_id(self, ci_mock):
        """
        Test that when a non integer sis id is passed the method returns false
        """
        ci_mock.return_value = CourseInstanceStub()
        res = is_enrollment_section(self.registrar_section['sis_section_id'])
        self.assertFalse(res, 'Expected is_enrollment_section() to return True for course_instance with section_type E')

    @patch('manage_sections.utils.CourseInstance.objects.get')
    def test_is_sis_section_for_true(self, mock_ci):
        """
        Test that is_sis_section method returns True for primary section
        """
        mock_ci.return_value = CourseInstanceStub(is_enrollment_section=True)
        sis_section_id = self.prim_section['sis_section_id']
        res = is_sis_section(sis_section_id)
        self.assertEqual(
            res,
            True,
            'Section {} should return True from is_registrar_section, but did not.'.format(self.registrar_section)
        )

    @patch('manage_sections.utils.CourseInstance.objects.get')
    def test_is_sis_section_false(self, mock_ci):
        """
        Test that is_sis_section method returns False for non registrar section
        """
        mock_ci.return_value = None
        sis_section_id = self.reg_section['sis_section_id']
        res = is_sis_section(sis_section_id)
        self.assertEqual(
            res,
            False,
            'Section {} should return False from is_registrar_section, but did not.'.format(self.reg_section)
        )

    def test_is_credit_status_section_for_true(self):
        """
        Test that regular section is a credit status section
        """
        sis_section_id = self.registrar_section['sis_section_id']
        res = is_credit_status_section(sis_section_id)
        self.assertEqual(
            res,
            True,
            'Section {} should return True from is_registrar_section, but did not.'.format(self.registrar_section)
        )

    def test_is_credit_status_on_false(self):
        """
        Test that regular section is not a credit status section
        """
        sis_section_id = self.reg_section['sis_section_id']
        res = is_credit_status_section(sis_section_id)
        self.assertEqual(
            res,
            False,
            'Section {} should return False from is_registrar_section, but did not.'.format(self.reg_section)
        )


class ContextUtilsTest(TestCase):
    longMessage = True

    def setUp(self):
        self.factory = RequestFactory()
        self.canvas_course_id = 1234
        self.section_id = 5678
        self.resource_link_id = '1a3b4c5dsdfsdf345345'
        self.request = RequestFactory().get('/fake-path')
        self.request.LTI = {
            'custom_canvas_course_id': self.canvas_course_id,
            'roles': [const.INSTRUCTOR],
            'resource_link_id': '1a3b4c5dsdfsdf345345',
        }
        self.request.POST = {'section_id': "1234"}

    def test_validate_course_id_for_true(self):
        """
        Test that the section's course id matches the request.session's course id
        """
        section_canvas_course_id = 1234
        res = validate_course_id(
            section_canvas_course_id,
            self.request.LTI['custom_canvas_course_id']
        )
        self.assertEqual(res, True, 'Result should be True')

    def test_validate_course_id_for_false(self):
        """
        Test that the section's course id does not match the request.session's course id
        """
        section_canvas_course_id = 7896
        res = validate_course_id(
            section_canvas_course_id,
            self.request.LTI['custom_canvas_course_id']
        )
        self.assertEqual(res, False, 'Result should be False')

    def test_validate_course_id_fails_INT_conversion(self):
        """
        Test that the conversion to INT fails and returns False
        """
        section_canvas_course_id = "dog"
        res = validate_course_id(
            section_canvas_course_id,
            self.request.LTI['custom_canvas_course_id']
        )
        self.assertEqual(res, False, 'Result should be False')

    def test_validate_course_id_for_non_integer_convert_course_id(self):
        """
        Test that the request.session's course id can be passed in as string and converted to integer
        """
        section_canvas_course_id = 1234
        self.request.LTI['custom_canvas_course_id'] = "1234"
        res = validate_course_id(
            section_canvas_course_id,
            self.request.LTI['custom_canvas_course_id']
        )
        self.assertEqual(res, True, 'Result should be True')


def return_unmodified_input(input):
    """ used for Mock side effects to spy on calls to a mapping method """
    return input
