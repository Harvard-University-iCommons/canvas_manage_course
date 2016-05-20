from django.conf import settings
from os.path import abspath, dirname, join
from urlparse import urljoin

from selenium_tests.course_admin.course_admin_base_test_case \
    import CourseAdminBaseTestCase
from selenium_tests.course_admin.page_objects\
    .course_admin_dashboard_page_object import CourseAdminDashboardPage
from selenium_tests.manage_people.page_objects.mp_user_form_page \
    import UserListPageObject


# Common files used for all Manage People test cases
MP_TEST_USERS_WITH_ROLES = join(dirname(abspath(__file__)), 'test_data',
                                'mp_test_users_with_roles.xlsx')


class ManagePeopleBaseTestCase(CourseAdminBaseTestCase):

    def setUp(self):
        """
        Redirects browser to test course URL and login to PIN using
        specified credentials.
        """
        super(CourseAdminBaseTestCase, self).setUp()

        # instantiate
        self.dashboard_page = CourseAdminDashboardPage(self.driver)
        self.manage_people = UserListPageObject(self.driver)
        self.test_settings = settings.SELENIUM_CONFIG['manage_people']

        # initialize
        if not self.dashboard_page.is_loaded():
            self.dashboard_page.get(self.TOOL_URL)

        # navigate to cross-list tool
        self.dashboard_page.select_manage_people_link()

        # check if page is loaded (which will also set the focus on the tool)
        self.assertTrue(self.manage_people.is_loaded())
