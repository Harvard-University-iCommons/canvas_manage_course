import unittest

from mock import patch

from manage_sections.views import (
    _get_badge_info_for_users,
    _get_badge_label_for_role_type,
    _add_badge_label_name_to_enrollments
)


class AddBadgeLabelNameToEnrollmentsTest(unittest.TestCase):
    longMessage = True

    def setUp(self):
        # simulates results of a Canvas enrollment call
        self.enrollments = [
            {'user': {'sis_user_id': '123'}},
            {'user': {'sis_user_id': '456'}},
            {'user': {'sis_user_id': '789'}},
        ]
        # simulates results of a call to _get_badge_info_for_users()
        self.badge_info = {
            '123': 'HUID',
            '456': 'XID',
            '789': 'LIBRARY'
        }
        self.enrollments_with_badge_label_names = [
            {'user': {'sis_user_id': '123'}, 'badge_label_name': 'HUID'},
            {'user': {'sis_user_id': '456'}, 'badge_label_name': 'XID'},
            {'user': {'sis_user_id': '789'}, 'badge_label_name': 'LIBRARY'},
        ]

    @patch('manage_sections.views._get_badge_info_for_users')
    def test_matching_input(self, mock_badge_info):
        """
        If input contains one-to-one matches for Person lookup, the function
        should return a comprehensive mapping of input IDs to badge labels.
        """
        mock_badge_info.return_value = self.badge_info
        result = _add_badge_label_name_to_enrollments(self.enrollments)
        self.assertEqual(result, self.enrollments_with_badge_label_names)


class GetBadgeInfoForUsersTests(unittest.TestCase):
    longMessage = True

    def setUp(self):
        # simulates a call to the Person table, role types map to
        # [library ID, HUID, XID, 'other']
        self.person_object_values = [
            ('02123456', 'WIDENER'),
            ('98765432', 'STUDENT'),
            ('ab01yz89', 'XIDHOLDER'),
            ('1234567890', 'SOMETHINGELSE')
        ]
        self.user_id_input_list = dict(self.person_object_values).keys()
        self.badge_types = [
            _get_badge_label_for_role_type(role_type)
            for role_type
            in dict(self.person_object_values).values()
        ]
        self.expected_results = dict(
            zip(self.user_id_input_list, self.badge_types)
        )

        # copy good input and good expected results and add a bad value
        self.bad_input = list(self.user_id_input_list)
        _bad_user_id = 'not a valid ID'
        self.bad_input.append(_bad_user_id)
        self.expected_results_for_bad_input = self.expected_results.copy()
        self.expected_results_for_bad_input[_bad_user_id] = _get_badge_label_for_role_type(_bad_user_id)

    def test_input_empty_and_none(self):
        """
        If input parameter is empty the function
        should return an empty dictionary.
        """
        result_for_empty_list = _get_badge_info_for_users([])
        self.assertDictEqual(result_for_empty_list, {})

    @patch('manage_sections.views.logger.warn')
    @patch('manage_sections.views.Person.objects.filter')
    def test_non_matching_input(self, mock_person, mock_logger_warn):
        """
        If input list contains info that doesn't match the Person lookup,
        the function should return all user_ids in the input list, returning
        a default badge label for any user_ids that do not have a valid
        role_type_cd, and log a warning.
        """
        mock_person.return_value.values_list.return_value = self.person_object_values
        result = _get_badge_info_for_users(self.bad_input)
        self.assertDictEqual(result, self.expected_results_for_bad_input)
        self.assertTrue(mock_logger_warn.called)

    @patch('manage_sections.views.logger.warn')
    @patch('manage_sections.views.Person.objects.filter')
    def test_matching_input(self, mock_person, mock_logger_warn):
        """
        If input contains one-to-one matches for Person lookup, the function
        should return a comprehensive mapping of input IDs to badge labels.
        """
        mock_person.return_value.values_list.return_value = self.person_object_values
        result = _get_badge_info_for_users(self.user_id_input_list)
        self.assertDictEqual(result, self.expected_results)
        self.assertFalse(mock_logger_warn.called)

    @patch('manage_sections.views.Person.objects.filter')
    def test_db_error_raises_exception(self, mock_person):
        """
        If Person lookup fails due to database issue,
        the function will raise the exception up the stack.
        """
        mock_person.return_value.values_list.side_effect = Exception
        with self.assertRaises(Exception):
            _get_badge_info_for_users(self.user_id_input_list)
