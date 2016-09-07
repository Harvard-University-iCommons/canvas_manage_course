from os.path import abspath, dirname, join


from selenium_tests.course_admin.course_admin_base_test_case \
    import CourseAdminBaseTestCase

# Common files used for Import Isites Content Tool test cases
IMPORT_ISITES_PERMISSION_ROLES = join(dirname(abspath(__file__)), 'test_data',
                                     'import_isites_roles_access.xlsx')


class ClassRosterBaseTestCase(CourseAdminBaseTestCase):
    pass
