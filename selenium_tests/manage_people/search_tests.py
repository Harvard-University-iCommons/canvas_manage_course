from selenium_tests.manage_people.base_test_case \
    import ManagePeopleBaseTestCase
from selenium_tests.manage_people.page_objects.mp_find_user_page \
    import FindUserPageObject
from selenium_tests.manage_people.page_objects.mp_results_list_page \
    import ResultsListPageObject
from selenium_tests.manage_people.page_objects.mp_user_form_page \
    import UserListPageObject


class SearchTests(ManagePeopleBaseTestCase):
    """ Testing Searching functionality of Manage People"""

    def test_search_by_huid_successful(self):
        """
        This searches for an existing ID and asserts the search results page is
        loaded after search
        """
        self.driver.get(self.base_url)
        user_list_page = UserListPageObject(self.driver)
        search_page = FindUserPageObject(self.driver)
        results_page = ResultsListPageObject(self.driver)
        test_user = self.test_settings['test_users']['1']

        # ensure person isn't in course before attempting to search
        self.api.remove_user(self.test_settings['test_course']['cid'],
                                  test_user['user_id'], test_user['role_id'])

        user_list_page.add_user()
        search_page.find_user(test_user['user_id'])

        self.assertTrue(results_page.is_loaded())

    def test_search_by_huid_unsuccessful(self):
        """
        This searches for an invalid id and asserts that search page is not
        loaded and user is not found
        """
        self.driver.get(self.base_url)
        user_list_page = UserListPageObject(self.driver)
        search_page = FindUserPageObject(self.driver)

        fake_huid = self.test_settings['test_users']['fake']['user_id']
        user_list_page.add_user()
        search_page.find_user(fake_huid)

        self.assertTrue(search_page.is_loaded())
        self.assertTrue(search_page.user_not_found())
