from ddt import ddt, data, unpack

from selenium_common.base_test_case import get_xl_data
from selenium_tests.import_isites_content.import_isites_base_test_case import \
    IMPORT_ISITES_PERMISSION_ROLES
from selenium_tests.course_admin.course_admin_base_test_case import \
    CourseAdminBaseTestCase


@ddt
class ImportiSitesPermissionTests(CourseAdminBaseTestCase):

    @data(*get_xl_data(IMPORT_ISITES_PERMISSION_ROLES))
    @unpack
    def test_roles_access(self, user_id, given_access, expected_role):
        # This test masquerades as users in roles in the spreadsheet
        # specified in IMPORT_ISITES_PERMISSION_ROLES, and then validates the
        # the users are granted/denied access based on their role.

        #  Masquerade as test user
        self.masquerade_page.masquerade_as(user_id)

        # Go back to the Manage Course Dashboard
        self.driver.get(self.TOOL_URL)

        if given_access == 'yes':
            # Verifying that the user can see the import isites card on the
            # manage_course dashboard
            self.assertTrue(
                self.course_admin_dashboard_page
                    .import_isites_content_is_displayed(),
                'User {} with expected role {} should see the import '
                'isites content tool on page but does not'
                    .format(user_id, expected_role)
            )

        elif given_access == 'no':
            self.assertFalse(
                self.course_admin_dashboard_page
                    .import_isites_content_is_displayed(),
                'User {} with expected role {} does not see the import isites '
                'content tool, but should.'.format(user_id, expected_role)
            )

        else:
            raise ValueError(
                'given_access column for user {} must be either "yes" or '
                '"no"'.format(user_id, expected_role)
            )
