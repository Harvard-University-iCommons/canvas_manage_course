from os.path import abspath, dirname, join

from selenium_tests.course_admin.course_admin_base_test_case \
    import CourseAdminBaseTestCase


# Common files used for all Manage Sections test case:
MANAGE_SECTION_PERMISSIONS = join(dirname(abspath(__file__)), 'test_data',
                                  'manage_sections_roles_access.xlsx')


class ManageSectionsBaseTestCase(CourseAdminBaseTestCase):
    pass
