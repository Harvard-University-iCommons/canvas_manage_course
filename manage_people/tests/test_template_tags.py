from django.test import TestCase



from manage_people.templatetags import manage_people_tags



class GetRoleNameTestCase(TestCase):
    fixtures = ['manage_people_role.json', 'user_role.json']
    longMessage = True
    display_names_loaded = False

    def setUp(self):
        self.timestamp = "DO"

    def _assert_expected_role_name(self, canvas_role_name, expected):
        result = manage_people_tags.get_role_display_name(canvas_role_name)
        return self.assertEqual(result, expected, 'Expected the string %s' % expected)

    def test_teacher(self):
        self._assert_expected_role_name('TeacherEnrollment', 'Teacher')

    def test_ta(self):
        self._assert_expected_role_name('TaEnrollment', 'TA')

    def test_designer(self):
        self._assert_expected_role_name('DesignerEnrollment', 'Designer')

    def test_guest(self):
        self._assert_expected_role_name('Guest', 'Guest')

    def test_enrollment(self):
        self._assert_expected_role_name('SomeRoleEnrollment', 'SomeRole')

    def test_custom_role(self):
        self._assert_expected_role_name('CustomRole', 'CustomRole')
