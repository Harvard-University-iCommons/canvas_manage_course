from ddt import ddt, data, unpack
from selenium_common.base_test_case import get_xl_data
from selenium_common.decorators import screenshot_on_test_exception
from selenium_tests.manage_people.base_test_case \
    import ManagePeopleBaseTestCase
from selenium_tests.manage_people.base_test_case \
    import MP_TEST_USERS_WITH_ROLES
from selenium_tests.manage_people.page_objects.mp_find_user_page \
    import FindUserPageObject
from selenium_tests.manage_people.page_objects.mp_results_list_page \
    import ResultsListPageObject
from selenium_tests.manage_people.page_objects.mp_user_form_page \
    import UserListPageObject

# todo: Is there any way to avoid the long lists of data unpacked by ddt every time (i.e. get only some arguments)?
@ddt
class AddingTests(ManagePeopleBaseTestCase):

    @data(*get_xl_data(MP_TEST_USERS_WITH_ROLES))
    @unpack
    @screenshot_on_test_exception
    def test_adding_users_by_roles(self, test_case_id,
                                   test_user_id,
                                   test_univ_id,
                                   role,
                                   role_id,
                                   canvas_role,
                                   success_msg_ind,
                                   remove_list_ind,
                                   error_msg_ind,
                                   add_remove_indicator):

        if add_remove_indicator != 'add':
            return

        test_univ_id = self.normalize_xlrd_number(test_univ_id, '{0:08d}')
        test_user_id = self.normalize_xlrd_number(test_user_id, '{0:08d}')
        role_id = self.normalize_xlrd_number(role_id)

        self.start_message(test_user_id, test_univ_id, role, role_id)

        # Note: ICOMMONS_REST_API_HOST environment needs to match the LTI tool
        # environment (because of shared cache interactions)

        # ensure person is not in course before attempting to add using API;
        # remove ALL roles/enrollments for the test user in this course
        # to ensure no incidental data causes conflict when we try to add
        self.api.remove_user(
            self.test_settings['test_course']['cid'], test_univ_id)

        self.driver.get(self.base_url)

        user_list_page = UserListPageObject(self.driver)
        search_page = FindUserPageObject(self.driver)
        results_page = ResultsListPageObject(self.driver)

        # from Main/User list page: click links to add people to course
        user_list_page.add_user()
        # from Search page: find a user and submit form
        search_page.find_user(test_user_id)
        # verify that we are now on the results page from search
        self.assertTrue(results_page.is_loaded(),
                        "Problem finding user %s: results page not loaded"
                        % test_user_id)

        results_page.add_id_to_course(test_univ_id, role)

        self.assertTrue(results_page.user_confirmation_visible(),
                        'User %s with role %s could not be added to the '
                        'course; another conflicting role may exist for '
                        'the user already.' % (test_univ_id, role_id))

        results_page.return_to_manage_people()
        self.assertTrue(
            user_list_page.user_present_with_role(test_univ_id, role))

        # ensure person is removed from course as cleanup
        self.api.remove_user(
            self.test_settings['test_course']['cid'], test_univ_id, role_id)

    @classmethod
    def start_message(cls, test_user_id, test_univ_id, role, role_id):
        row_log = "Attempting to add user for search term {}, " \
                  "univ_id {}, role {} (in dropdown list), role_id {}..."
        print row_log.format(test_user_id, test_univ_id, role, role_id)
