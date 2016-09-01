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
    pass
