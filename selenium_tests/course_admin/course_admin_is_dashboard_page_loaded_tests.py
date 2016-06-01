from selenium_tests.course_admin.course_admin_base_test_case import \
    CourseAdminBaseTestCase
from selenium_tests.course_admin.page_objects\
    .course_admin_dashboard_page_object import CourseAdminDashboardPage


class CourseAdminIsDashboardLoadedTest(CourseAdminBaseTestCase):

    def test_is_account_admin_dashboard_page_loaded(self):

        """
        Check if the course dashboard page is loaded
        """
        # initialize
        dashboard_page = CourseAdminDashboardPage(self.driver)
        self.assertTrue(dashboard_page.is_loaded())
        # The Manage People button should be displayed for the selenium
        # user in this test.
        self.assertTrue(dashboard_page.manage_people_button_is_displayed())
