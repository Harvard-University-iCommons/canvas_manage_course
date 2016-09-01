from datetime import datetime

from ddt import ddt, data, unpack

from selenium_common.base_test_case import get_xl_data
from selenium_tests.manage_people.base_test_case import \
    MP_PERMISSION_ROLES
from selenium_tests.manage_people.page_objects.mp_main_page import MainPageObject
from selenium_tests.course_admin.course_admin_base_test_case import \
    CourseAdminBaseTestCase



@ddt
class MPPermissionTests(CourseAdminBaseTestCase):
    @data(*get_xl_data(MP_PERMISSION_ROLES))
    @unpack
    def test_roles_access(self, user_id, given_access, expected_role):
        # This test masquerades as users in roles in the spreadsheet
        # specified in MP_PERMISSION_ROLES, and then validates the the users
        # are granted/denied access based on their role.

        self.masquerade_page.masquerade_as(user_id)
        # Go back to the Manage Course Dashboard
        self.driver.get(self.TOOL_URL)

        if given_access == 'yes':
            self.assertTrue(
                self.course_admin_dashboard_page
                    .manage_people_button_is_displayed(),
                'User {} with expected role {} should see the manage people '
                'button on page but does not.'.format(user_id, expected_role)
            )

            #  Clicks into tool
            self.course_admin_dashboard_page.select_manage_people_link()
            # Verifies that user can see the manage people tool

            manage_people_page = MainPageObject(self.driver)
            # Switch frame and verify main page is loaded
            manage_people_page.focus_on_tool_frame()
            self.assertTrue(manage_people_page.is_loaded())

        elif given_access == 'no':
            self.assertFalse(
                self.course_admin_dashboard_page
                    .manage_people_button_is_displayed(), 'User {} with '
                'expected role {} should not see the manage_sections button, '
                'but can see it.'.format(user_id, expected_role)
            )

        else:
            raise ValueError(
                'given_access column for user {} with expected role {} must be '
                'either "yes" or "no".'.format(user_id, expected_role)
            )
