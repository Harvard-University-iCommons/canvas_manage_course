from ddt import ddt, data, unpack

from selenium_common.base_test_case import get_xl_data
from selenium_tests.manage_sections.manage_sections_base_test_case import \
    MANAGE_SECTION_PERMISSIONS
from selenium_tests.manage_sections.manage_sections_base_test_case import \
    ManageSectionsBaseTestCase
from selenium_tests.manage_sections.page_objects.manage_sections_main_page \
    import MainPageObject


@ddt
class ManageSectionsPermissionTests(ManageSectionsBaseTestCase):

    @data(*get_xl_data(MANAGE_SECTION_PERMISSIONS))
    @unpack
    def test_roles_access(self, user_id, given_access, expected_role):
        # This test masquerades as users in the spreadsheet
        # specified in MANAGE_SECTION_PERMISSIONS, and then validates that
        # the users are granted/denied access based on their role.
        # Their role in our test instance of Canvas is expected to match
        # what's in the expected_role column of the test spreadsheet.

        #  Instantiate
        main_page = MainPageObject(self.driver)

        #  Masquerade as test user
        self.masquerade_page.masquerade_as(user_id)

        # Go back to the Manage Course Dashboard
        self.driver.get(self.TOOL_URL)

        # test user should be able to access the dashboard, so we can test if
        # the manage sections app is visible
        self.assertTrue(self.course_admin_dashboard_page.is_loaded())

        if given_access == 'yes':
            # If user should have access to Manage Sections tool, verify that
            # the user sees the manage sections button
            self.assertTrue(
                self.course_admin_dashboard_page
                    .manage_sections_button_is_displayed(),
                'User {} with expected role {} should see the manage_sections '
                'button on page but does not.'.format(user_id, expected_role)
            )

            # Clicks into tool
            self.course_admin_dashboard_page.select_manage_sections_link()

            # Verifies that user can click into and see the manage sections tool
            self.assertTrue(main_page.is_loaded())

        elif given_access == 'no':
            self.assertFalse(
                self.course_admin_dashboard_page
                    .manage_sections_button_is_displayed(),
                'User {} with expected role {} should not see the '
                'manage_sections button, but can see it.'.format(user_id,
                                                                 expected_role)
            )

        else:
            raise ValueError(
                'given_access column for user {} with expected role {} must be '
                'either "yes" or "no".'.format(user_id, expected_role)
            )
