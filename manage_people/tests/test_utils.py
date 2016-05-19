from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from mock import Mock, patch
from unittest import skip

from icommons_common.models import (
    CourseGuest,
    CourseEnrollee,
    CourseStaff,
)

from manage_people.utils import (
    get_available_roles,
    get_course_member_class,
)


class GetAvailableRolesTest(TestCase):
    fixtures = [
        'manage_people_role.json',
        'user_role.json',
    ]
    longMessage = True

    def setUp(self):
        self.course_instance_id = 12345678

    @patch('manage_people.utils.CourseInstance.objects.get')
    def test_get_available_roles_on_school_with_default_roles(self, mock_ci_get):
        """
        Test that get_available_roles returns the full list of manage_people_role
        entries for a school which hasn't overridden the role choices.
        """
        mock_ci_get.return_value.course.school.school_id = 'deadbeef'
        result = get_available_roles(self.course_instance_id)
        self.assertEqual(len(result), 11, 'Count of manage people roles')
        self.assertEqual(sorted([r['role_id'] for r in result]),
                         [0, 1, 2, 5, 7, 9, 10, 11, 12, 14, 15],
                         'List of manage people role user_role_ids')

    @patch('manage_people.utils.CourseInstance.objects.get')
    def test_get_available_roles_on_school_with_overridden_roles(self, mock_ci_get):
        """
        Test that get_available_roles returns just the overridden roles for
        a school which overrides the defaults.
        """
        mock_ci_get.return_value.course.school.school_id = 'gse'
        expected_role_ids = [9, 10, 11, 12, 15]
        result = get_available_roles(self.course_instance_id)
        self.assertEqual(len(result), len(expected_role_ids),
                         'Count of manage people roles')
        self.assertEqual(sorted([r['role_id'] for r in result]),
                         expected_role_ids,
                         'List of manage people role user_role_ids')

    @patch('manage_people.utils.logger.exception')
    @patch('manage_people.utils.CourseInstance.objects.get')
    def test_get_available_roles_throws_exception(self, mock_ci, mock_exception):
        """
        Test that get_available_roles logs the exception that is thrown
        when the course instance id does not exist
        """
        mock_ci.side_effect = ObjectDoesNotExist
        get_available_roles(self.course_instance_id)
        self.assertTrue(mock_exception.called)


class GetCourseMemberClassTest(TestCase):
    longMessage = True

    def test_guest(self):
        mock_role = Mock(guest="1", staff="0", student="0")
        self.assertIs(get_course_member_class(mock_role), CourseGuest)

    def test_staff(self):
        mock_role = Mock(guest="0", staff="1", student="0")
        self.assertIs(get_course_member_class(mock_role), CourseStaff)

    def test_student(self):
        mock_role = Mock(guest="0", staff="0", student="1")
        self.assertIs(get_course_member_class(mock_role), CourseEnrollee)

    def test_none_of_the_above(self):
        mock_role = Mock(guest="0", staff="0", student="0")
        with self.assertRaises(RuntimeError):
            get_course_member_class(mock_role)
