from os.path import abspath, dirname, join
from django.conf import settings
from urlparse import urljoin

from selenium_tests.course_admin.course_admin_base_test_case \
    import CourseAdminBaseTestCase
from selenium_tests.course_admin.page_objects\
    .course_admin_dashboard_page_object import CourseAdminDashboardPage
from selenium_tests.class_roster.page_objects.class_roster_main_page import \
    MainPageObject

# Common files used for all Class Roster test cases
CLASS_ROSTER_PERMISSION_ROLES = join(dirname(abspath(__file__)), 'test_data',
                                     'class_roster_roles_access.xlsx')


class ClassRosterBaseTestCase(CourseAdminBaseTestCase):

    def setUp(self):
        """
        Redirects browser to test course URL and login to PIN using
        specified credentials.
        """
        super(CourseAdminBaseTestCase, self).setUp()

        # instantiate
        self.dashboard_page = CourseAdminDashboardPage(self.driver)
        self.main_page = MainPageObject(self.driver)
        self.test_settings = settings.SELENIUM_CONFIG['class_roster']

        self.CANVAS_BASE_URL = settings.SELENIUM_CONFIG['canvas_base_url']
        self.TOOL_RELATIVE_URL = self.test_settings['course_link']
        # This gets the URL of a course with a working class roster tool
        self.TOOL_URL = urljoin(self.CANVAS_BASE_URL, self.TOOL_RELATIVE_URL)

        # After setup, override the default URL which uses the automated test
        # site and replace it with this course site.
        self.main_page.get(self.TOOL_URL)
        self.main_page.focus_on_tool_frame()

        # Clicks on the class roster button from the dashboard
        self.dashboard_page.select_class_roster_link()
        self.assertTrue(self.main_page.is_loaded())
