from unittest import TestCase
from manage_sections.utils import unique_enrollments_not_in_section_filter


class UniqueEnrollmentsNotInSectionFilterUtilsTest(TestCase):
    longMessage = True

    def enroll(self, user_id, role, section_id, sortable_name=''):
        """
        Helper method that returns a dict resembling an Enrollment JSON object passed
        back from the Canvas API.
        """
        return {
            'user_id': user_id,
            'role': role,
            'course_section_id': section_id,
        }

    def test_some_enrollments_in_section(self):
        """
        Test that enrollments present in the given section list are filtered out of return list
        """
        current_section_id = 1234
        other_section_id = 5678
        enrollments = [
            self.enroll(1, role='Student', section_id=current_section_id),
            self.enroll(2, role='Teacher', section_id=other_section_id),
            self.enroll(3, role='Student', section_id=current_section_id),
            self.enroll(4, role='Observer', section_id=other_section_id),
        ]
        # Should return the enrollments above that are not in current section
        expected_result = [enrollments[1], enrollments[3]]
        res = unique_enrollments_not_in_section_filter(current_section_id, enrollments)
        self.assertEqual(res, expected_result, "Enrollments in current section should be filtered out")

    def test_all_enrollments_in_section(self):
        """
        Test that an empty list is returned if all of the enrollments are tied to the
        current section
        """
        current_section_id = 1234
        enrollments = [
            self.enroll(1, role='Student', section_id=current_section_id),
            self.enroll(2, role='Teacher', section_id=current_section_id),
            self.enroll(3, role='Observer', section_id=current_section_id),
        ]
        res = unique_enrollments_not_in_section_filter(current_section_id, enrollments)
        self.assertEqual(res, [], "Expected an empty list of enrollments!")

    def test_duplicate_user_and_roles_across_sections(self):
        """
        Test that if some users are enrolled in other sections with the same role, the
        duplicate records are filtered out.
        """
        current_section_id = 123
        other_section_ids = [45, 67, 89]
        enrollments = [
            self.enroll(1, role='Student', section_id=other_section_ids[0]),
            self.enroll(2, role='Teacher', section_id=other_section_ids[0]),
            self.enroll(1, role='Student', section_id=other_section_ids[1]),
            self.enroll(2, role='Teacher', section_id=other_section_ids[1]),
            self.enroll(1, role='Student', section_id=other_section_ids[2]),
            self.enroll(2, role='Teacher', section_id=other_section_ids[2]),
        ]
        # Should return the last of each unique user_id/role combo
        expected_result = [enrollments[4], enrollments[5]]
        res = unique_enrollments_not_in_section_filter(current_section_id, enrollments)
        # Order doesn't matter here, so use itemsEqual instead of listEqual
        self.assertItemsEqual(res, expected_result, "Similar enrollments should be filtered out")

    def test_same_user_with_different_roles_across_sections(self):
        """
        Test that the same user with different roles across sections can be part of
        result set, provided the sections are not the current section.
        """
        current_section_id = 123
        other_section_ids = [45, 67, 89]
        enrollments = [
            self.enroll(1, role='Student', section_id=other_section_ids[0]),
            self.enroll(1, role='Teacher', section_id=other_section_ids[0]),
            self.enroll(1, role='Observer', section_id=other_section_ids[1]),
            self.enroll(1, role='Teacher', section_id=other_section_ids[1]),
            self.enroll(1, role='Student', section_id=other_section_ids[2]),
            self.enroll(1, role='Observer', section_id=other_section_ids[2]),
        ]
        # Should return the last of each unique user_id/role combo
        expected_result = [enrollments[5], enrollments[4], enrollments[3]]
        res = unique_enrollments_not_in_section_filter(current_section_id, enrollments)
        # Order doesn't matter here, so use itemsEqual instead of listEqual
        self.assertItemsEqual(res, expected_result, "Similar enrollments should be filtered out")

    def test_same_user_with_a_role_in_section_and_a_role_outside_section(self):
        """
        Test that a user with one role in the current section, but a different role
        in another section is part of result set.
        """
        current_section_id = 123
        other_section_id = 89
        enrollments = [
            self.enroll(1, role='Student', section_id=current_section_id),
            self.enroll(1, role='Teacher', section_id=other_section_id),
        ]
        res = unique_enrollments_not_in_section_filter(current_section_id, enrollments)
        # Order doesn't matter here, so use itemsEqual instead of listEqual
        self.assertEqual(res, [enrollments[1]], "Should allow for user to be present with different role")
