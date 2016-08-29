from django.conf import settings
from os.path import abspath, dirname, join

from selenium_tests.course_admin.course_admin_base_test_case \
    import CourseAdminBaseTestCase
from selenium_tests.course_admin.page_objects\
    .course_admin_dashboard_page_object import CourseAdminDashboardPage
from selenium_tests.manage_sections.page_objects.manage_sections_main_page \
    import MainPageObject


# Common files used for all Manage Sections test case:
MANAGE_SECTION_PERMISSIONS = join(dirname(abspath(__file__)), 'test_data',
                                  'permissions_roles_access.xlsx')


class ManageSectionsBaseTestCase(CourseAdminBaseTestCase):

    def setUp(self):
        """
        Redirects browser to test course URL and login to PIN using
        specified credentials.
        """
        super(CourseAdminBaseTestCase, self).setUp()

        # instantiate
        self.dashboard_page = CourseAdminDashboardPage(self.driver)
        self.manage_sections = MainPageObject(self.driver)

        # initialize
        if not self.dashboard_page.is_loaded():
            self.dashboard_page.get(self.TOOL_URL)

        # navigate to manage sections tool
        self.dashboard_page.select_manage_sections_link()

        # check if page is loaded (which will also set the focus on the tool)
        self.assertTrue(self.manage_sections.is_loaded())
