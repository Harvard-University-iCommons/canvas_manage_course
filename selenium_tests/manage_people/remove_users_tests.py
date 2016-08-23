from ddt import ddt, data, unpack
from selenium_common.base_test_case import get_xl_data
from selenium_common.decorators import screenshot_on_test_exception
from selenium_tests.manage_people.base_test_case \
    import ManagePeopleBaseTestCase
from selenium_tests.manage_people.base_test_case \
    import MP_TEST_USERS_WITH_ROLES
from selenium_tests.manage_people.page_objects.mp_user_form_page \
    import UserListPageObject


@ddt
class RemovePeopleTests(ManagePeopleBaseTestCase):

    @screenshot_on_test_exception
    @data(*get_xl_data(MP_TEST_USERS_WITH_ROLES))
    @unpack
    def test_remove_users(self, test_case_id,
                          test_user_id,
                          test_univ_id,
                          role,
                          role_id,
                          canvas_role,
                          success_msg_ind,
                          remove_list_ind,
                          error_msg_ind,
                          add_remove_ind):

        if add_remove_ind != 'remove':
            return

        test_univ_id = self.normalize_xlrd_number(test_univ_id, '{0:08d}')
        role_id = self.normalize_xlrd_number(role_id)

        self.start_message(test_user_id, test_univ_id, role, role_id)

        # Note: ICOMMONS_REST_API_HOST environment needs to match the LTI tool
        # environment (because of shared cache interactions)

        # ensure person is in course before attempting to remove using API
        # 1. remove ALL roles/enrollments for the test user in this course
        #    to ensure no incidental data causes conflict when we try to add
        # 2. add via API the role we want to test removing through the UI
        self.api.remove_user(
            self.test_settings['test_course']['cid'], test_univ_id)
        self.api.add_user(
            self.test_settings['test_course']['cid'], test_univ_id, role_id)

        user_list_page = UserListPageObject(self.driver)

        # Note: the refresh has been added due to issues with remove.  If
        # user is added via the api but the page isn't reload, the tests will
        # sporadically fail out with NoSuchElementException.
        self.driver.refresh()
        self.setUp()

        # Delete the user in Canvas
        user_list_page.delete_user(test_univ_id, role_id)

        self.assertTrue(user_list_page.is_loaded())
        # Note: the refresh has been added due to issues with remove. If the
        # user has been deleted via the UI, but the page isn't reloaded,
        # it would sporadically fail out with an assertion error.  We have
        # yet to find a more graceful solution.
        self.driver.refresh()
        self.setUp()

        # Assert that the deleted user does not appear in Manage People
        self.assertFalse(
            user_list_page.user_present_with_role(test_univ_id, role_id))

    @classmethod
    def start_message(cls, test_user_id, test_univ_id, role, role_id):
        row_log = "Attempting to remove user for search term {}, " \
                  "univ_id {}, role {} (in dropdown list), role_id {}..."
        print row_log.format(test_user_id, test_univ_id, role, role_id)
