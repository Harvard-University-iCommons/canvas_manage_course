# -*- coding: utf-8 -*-


from ddt import ddt, data, unpack

from selenium_common.base_test_case import get_xl_data
from selenium_tests.course_admin.course_admin_base_test_case import (
    CourseAdminBaseTestCase,
    MANAGE_COURSE_PERMISSIONS)


@ddt
class CourseAdminDashboardPermissionTests(CourseAdminBaseTestCase):

    @data(*get_xl_data(MANAGE_COURSE_PERMISSIONS))
    @unpack
    def test_roles_access(self, user_id, given_access, expected_role):
        """This test masquerades as users in the spreadsheet
        specified in MANAGE_COURSE_PERMISSIONS, and then validates that
        the users are granted/denied access based on their role.
        Their role in our test instance of Canvas is expected to match
        what's in the expected_role column of the test spreadsheet."""

        # initialize
        dashboard = self.course_admin_dashboard_page

        #  Masquerade as test user
        self.masquerade_page.masquerade_as(user_id)

        # Go back to the Manage Course Dashboard
        dashboard.get(self.TOOL_URL)

        if given_access == 'yes':
            # test user should be able to access the dashboard
            self.assertTrue(dashboard.is_loaded(),
                'User {} with expected role {} should be able to access the '
                'Manage Course dashboard but cannot.'.format(
                    user_id, expected_role))
        elif given_access == 'no':
            self.assertFalse(dashboard.is_loaded(),
                'User {} with expected role {} should not have access to the '
                'Manage Course dashboard, but can access it.'.format(
                    user_id, expected_role))
        else:
            raise ValueError(
                'given_access column for user {} with expected role {} must be '
                'either "yes" or "no".'.format(user_id, expected_role))
