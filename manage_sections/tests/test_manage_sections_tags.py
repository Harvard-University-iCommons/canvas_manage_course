from unittest import TestCase
from manage_sections.templatetags import manage_sections_tags


class ManageSectionsTagsTest(TestCase):
    longMessage = True

    def test_to_letter_range_empty_string(self):
        """
        Test that if name value is empty, an empty string is returned
        """
        res = manage_sections_tags.to_letter_range('', 'A-D,E-F')
        self.assertEqual(res, '', 'Expected an empty string from filter')

    def test_to_letter_range_mixed_case_lower_upper(self):
        """
        Test that if name is lowercased, it matches uppercase range
        """
        res = manage_sections_tags.to_letter_range('bermudez, jaime', 'A-D,E-F')
        self.assertEqual(res, 'A-D', 'Result should be uppercased')

    def test_to_letter_range_mixed_case_upper_lower(self):
        """
        Test that if name is uppercase, it matches lowercase range
        """
        res = manage_sections_tags.to_letter_range('Bermudez, Jaime', 'a-d,e-f')
        self.assertEqual(res, 'A-D', 'Result should be uppercased')

    def test_to_letter_range_lower_end_of_range(self):
        """
        Test that if name matches the left edge of a range, that range is returned
        """
        res = manage_sections_tags.to_letter_range('Adams, James', 'A-D,E-F,G-H')
        self.assertEqual(res, 'A-D', 'Result is in unexpected range')

    def test_to_letter_range_upper_end_of_range(self):
        """
        Test that if name matches the right edge of a range, that range is returned
        """
        res = manage_sections_tags.to_letter_range('Foo, James', 'A-D,E-F,G-H')
        self.assertEqual(res, 'E-F', 'Result is in unexpected range')

    def test_to_letter_range_single_range(self):
        """
        Test that if a single range with no commas works
        """
        res = manage_sections_tags.to_letter_range('Bar, Foo', 'B-C')
        self.assertEqual(res, 'B-C', 'Result is in unexpected range')

    def test_to_letter_range_single_letter(self):
        """
        Test that a range on a single letter will return that letter
        """
        res = manage_sections_tags.to_letter_range('End,Foo', 'A-D,E,C-F')
        self.assertEqual(res, 'E', 'Result should match single letter')

    def test_list_comp_single_level(self):
        """
        Test that filter builds list comprehension for attribute
        """
        s_list = [{'foo': 'fooVal', 'bar': 'barVal'}, {'foo': 'fooTwoVal', 'bar': 'barTwoVal'}]
        res = manage_sections_tags.list_comp(s_list, 'foo')
        self.assertEqual(['fooVal', 'fooTwoVal'], res, "Result should match dict key values")

    def test_list_comp_empty_list(self):
        """
        Test that a comprehension on an empty list returns an empty list
        """
        s_list = []
        res = manage_sections_tags.list_comp(s_list, 'foo')
        self.assertEqual([], res, "Result should match empty list")

    def test_enrollment_lname_last_comma_first(self):
        """
        Test the normal case where sortable_name is comma separated
        """
        res = manage_sections_tags.enrollment_lname({'user': {'sortable_name': 'Last, First'}})
        self.assertEqual(res, 'Last', 'Result should match last name part of sortable_name')

    def test_enrollment_lname_last(self):
        """
        Test the case where sortable_name contains a single string (just first or last)
        """
        res = manage_sections_tags.enrollment_lname({'user': {'sortable_name': 'Prince'}})
        self.assertEqual(res, 'Prince', 'Result should match sortable_name single string')

    def test_enrollment_lname_no_sortable_name(self):
        """
        Test the case where sortable_name is missing from user dict fields
        """
        res = manage_sections_tags.enrollment_lname({'user': {}})
        self.assertEqual(res, '', 'Result should be an empty string')

    def test_enrollment_lname_no_user(self):
        """
        Test the case where the parameter doesn't even have a user key
        """
        res = manage_sections_tags.enrollment_lname({})
        self.assertEqual(res, '', 'Result should be an empty string')
