import logging

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from mock import ANY, Mock, call, patch

from icommons_common.models import Section, SectionMember
from icommons_common.tests.test_mock_helpers import set_disappearing_side_effect

from manage_sections.management.commands.sync_canvas_sections import (
    Command,
    add_user_list_to_section,
    create_or_update_section,
    get_account_list_from_canvas,
    get_canvas_sections_list,
    get_enrollments_from_canvas_section,
    remove_sections_from_cm,
)


class CourseInstanceStub:
    """
    Stub for a course instance object
    """
    def __init__(self, course_instance_id):
        self.course_instance_id = course_instance_id


class CommandsTestSyncCanvasSections(TestCase):
    """
    tests for the sync_canvas_sections management command.
    these are unit tests for the helper methods in the command. The command itself
    really needs to be integration tested with the database. 
    """
    def setUp(self):

        self.course_instance = CourseInstanceStub(123456)
        self.cm_section_id = 8888
        self.canvas_course_id = 1111
        self.canvas_section_id = 9999
        self.canvas_enrollments = [{'user' : {'sis_user_id' : '11111111'}},
                                   {'user' : {'sis_user_id' : '22222222'}},
                                   {'user' : {'sis_user_id' : '33333333'}},
                                   {'user' : {'not_id' : '99999999'}},
                                   {'user' : {'sis_user_id' : ''}}]
        self.cm_sections = [{'canvas_section_id': 1}, 
                            {'canvas_section_id': 2}, 
                            {'canvas_section_id': 3},
                            {'canvas_id': '54'},
                            {'canvas_section_id': None}]
        self.canvas_sections = [{'id': 1, 'sis_course_id': 11, 'sis_section_id': 111, 'name': 'sec_one',},
                                {'id': 7, 'sis_course_id': 4444, 'sis_section_id': 4444, 'name': 'this should not go',},
                                {'id': 2, 'sis_course_id': 22, 'sis_section_id': 222, 'name': 'sec_two',},
                                {'id': 3, 'sis_course_id': 33, 'sis_section_id': 333, 'name': 'sec_three',},
                                {'id': '', 'sis_course_id': 44, 'sis_section_id': 444, 'name': '',},
                                {'not_id': 5, 'sis_course_id': 44, 'sis_section_id': 555, }]

    @patch('manage_sections.management.commands.sync_canvas_sections.get_all_list_data')
    def test_get_enrollments_from_canvas_section(self, sdk_mock):
        """
        tests that the method get_enrollments_from_canvas_section returns
        the correct list of sis_user_id's
        """
        sdk_mock.return_value = self.canvas_enrollments
        canvas_enrollments = get_enrollments_from_canvas_section(self.canvas_section_id)
        self.assertEqual(canvas_enrollments, ['11111111', '22222222', '33333333'])

    @patch('manage_sections.management.commands.sync_canvas_sections.get_all_list_data')
    def test_get_canvas_sections_list(self, filter_mock):
        """ 
        test that the method returns the correct list of sections given 
        a list of dict items.
        """
        filter_mock.return_value = self.canvas_sections
        sections_list = get_canvas_sections_list(self.canvas_course_id)
        self.assertEqual(sections_list, [1, 2, 3])

    @patch('manage_sections.management.commands.sync_canvas_sections.get_all_list_data')
    def test_get_account_list_from_canvas(self, filter_mock):
        """
        test that the method returns the correct list of sections given 
        a list of dict items.
        """
        filter_mock.return_value = [{'id' : 1}, {'id' : 2}, {'id' : 3}, {'id' : 4}, {'id' : 5}, {'not_id' : 6}, {'id' : None}]
        account_list = get_account_list_from_canvas()
        self.assertEqual(account_list, [1, 2, 3, 4, 5])


    @patch('manage_sections.management.commands.sync_canvas_sections.Section')
    @patch('manage_sections.management.commands.sync_canvas_sections.logger')
    def test_create_or_update_section_assert_save_called(self, logger_mock,
                                                         section_mock):
        """
        Test that save is called when the course exists, and create isn't.
        """
        course_instance_mock = Mock(name="course_instance")
        create_mock = section_mock.objects.bulk_create
        get_mock = section_mock.objects.get
        mock_section = Mock(spec=Section())
        save_mock = mock_section.save
        get_mock.return_value = mock_section

        sis_course_id = 3030303
        canvas_section_id = 1239
        section_name = 'test section'
        create_or_update_section(course_instance_mock, sis_course_id,
                                 canvas_section_id, section_name)

        self.assertEqual(create_mock.call_count, 0)
        self.assertEqual(save_mock.call_count, 1)


    @patch('manage_sections.management.commands.sync_canvas_sections.Section')
    @patch('manage_sections.management.commands.sync_canvas_sections.logger')
    def test_create_or_update_section_assert_create_called_when_objectdoesnotexist_occurs(self, logger_mock, section_mock):
        """
        Test that create is called when the course does not exist.  When the 
        course does not exist the get call with throw an ObjectDoesNotExist
        exception. We set this as a side_effect of the get mock. 
        """
        get_mock = section_mock.objects.get
        create_mock = section_mock.objects.bulk_create
        set_disappearing_side_effect(get_mock, ObjectDoesNotExist)

        course_instance_mock = Mock(name="course_instance")
        sis_course_id = 3030303
        canvas_section_id = 1239
        section_name = 'test section'
        create_or_update_section(course_instance_mock, sis_course_id,
                                 canvas_section_id, section_name)
        self.assertEqual(create_mock.call_count, 1)

    @patch('manage_sections.management.commands.sync_canvas_sections.logger')
    @patch('manage_sections.management.commands.sync_canvas_sections.remove_all_users_from_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.Section.objects.get')
    def test_remove_sections_from_cm_assert_remove_users_called(self, get_mock, remove_users_mock, logger_mock):
        """
        test that remove_section_from_cm is called with the correct section_id
        """
        section = Mock(name="section")
        section.section_id = 1234
        get_mock.return_value = section
        remove_sections_from_cm([ANY], ANY)
        remove_users_mock.assert_called_once_with(1234)

    @patch('manage_sections.management.commands.sync_canvas_sections.logger')
    @patch('manage_sections.management.commands.sync_canvas_sections.remove_all_users_from_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.Section.objects.get')
    def test_remove_sections_from_cm_assert_exception_works(self, get_mock, remove_users_mock, logger_mock):
        """
        test that logger is called after ObjectDoesNotExist is thrown
        """
        get_mock.side_effect = ObjectDoesNotExist
        remove_sections_from_cm([ANY], ANY)
        logger_mock.info.assert_called_once_with(
            'section with canvas_section_id <ANY> does not exist')

    @patch('manage_sections.management.commands.sync_canvas_sections.add_user_list_to_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.remove_user_list_from_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.logger')
    @patch('manage_sections.management.commands.sync_canvas_sections.create_or_update_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.SectionMember.objects.get')
    @patch('manage_sections.management.commands.sync_canvas_sections.SectionMember.objects.create')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_canvas_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.SectionMember.objects.filter')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_enrollments_from_cm_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_enrollments_from_canvas_section')
    @patch('manage_sections.management.commands.sync_canvas_sections.Section.objects.create')
    @patch('manage_sections.management.commands.sync_canvas_sections.Section.objects.get')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_cm_sections_list')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_canvas_sections_list')
    @patch('manage_sections.management.commands.sync_canvas_sections.CourseInstance.objects.get')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_course_list_from_canvas')
    @patch('manage_sections.management.commands.sync_canvas_sections.get_account_list_from_canvas')
    def test_logic_in_main_body_of_command(self, get_account_list_mock, get_course_list_mock, course_instance_mock,
        get_canvas_sections_mock, get_cm_sections_list_mock, get_cm_section_mock, 
        create_cm_section_mock, get_enrollments_from_canvas_section_mock, 
        get_enrollments_from_cm_section_mock, get_cm_section_members_mock, 
        get_canvas_section_mock, create_section_member_mock, 
        get_section_member_mock, create_or_update_section_mock, logger_mock, 
        remove_user_list_from_section_mock, add_user_list_to_section_mock):
        """
        First, I realize this is a large test but since it's testing the main body of the command and I would 
        have to repeat a lot of this code for each sub test, I've combind them. This test the logic of the main
        body. 
        """
        account_list = [99999]
        get_account_list_mock.return_value = account_list
        course_list = [{'sis_course_id':'89101113', 'id': 2347},
                       {'sis_course_id':'89101112', 'id': 2345}]
        get_course_list_mock.return_value = course_list
        ci = Mock(name="course_instance")
        course_instance_mock.return_value = ci
        get_canvas_sections_mock.return_value = [789]
        canvas_section = Mock(name="Canvas section")
        canvas_section.get.return_value = 'test section'
        get_canvas_section_mock.return_value = canvas_section
        get_cm_sections_list_mock.return_value = [123, 456, 789]
        create_cm_section_mock = Mock(name="new section")
        create_or_update_section_mock.return_value = 790

        """
        the user with id 5 is new and missing from the course manager list and should be added 
        """
        get_enrollments_from_canvas_section_mock.return_value = [1, 2, 3, 5]

        """
        the user with id 4 is missing from canvas and should be removed
        """
        get_enrollments_from_cm_section_mock.return_value = [1, 2, 3, 4]
        get_cm_section_members_mock = []

        cmd = Command()
        opts = {} 
        cmd.handle_noargs(**opts)

        account_mock_calls = [call(a) for a in account_list]

        get_account_list_mock.assert_called_with()
        """
        assert that get_course_list was called with each account_id in the list of the get_account_list_mock
        """        
        self.assertEqual(account_mock_calls, get_course_list_mock.mock_calls)
        
        """
        assert that the course instance get call is using the course_instance_id returned
        from the get_course_list_mock
        """
        course_instance_calls = [call(pk=c['sis_course_id']) for c in course_list]
        self.assertEqual(course_instance_calls, course_instance_mock.mock_calls)

        """
        assert that get_canvas_sections is called with the canvas_course_id of the course_instance
        """
        canvas_course_mock_calls = [call(c['id']) for c in course_list]
        get_canvas_sections_mock.assert_has_calls(canvas_course_mock_calls)

        """
        assert that get_cm_sections_list is called with the course_instance object returned
        by get_course_list
        """
        get_cm_sections_list_mock.assert_called_with(ci)

        """
        assert that create_or_update_section is called with the course_instance object from the 
        course list, the course_instance_id of the course_instance object, the canvas_section_id, and
        the section name.
        """
        create_calls = [call(ci, c['sis_course_id'], 789, 'test section')
                            for c in course_list]
        create_or_update_section_mock.assert_has_calls(create_calls)
        
        """
        assert that get_enrollments_from_canvas_section is called with the canvas_section_id
        from the course_instance object
        """
        get_enrollments_from_canvas_section_mock.assert_called_with(789)

        """
        assert that get_enrollments_from_cm_section is called with the canvas_section_id
        returned from create_or_update_section
        """
        get_enrollments_from_cm_section_mock.assert_called_with(790)

        """
        assert the remove_user_list_from_section call is called with the user to remove and the
        canvas_section_id returned from create_or_update_section
        """
        remove_user_list_from_section_mock.assert_called_with(set([4]), 790)

        """
        assert the add_user_list_to_section call is called with the user to add and the
        canvas_section_id returned from create_or_update_section
        """
        add_user_list_to_section_mock.assert_called_with(set([5]), 790)

    @patch('manage_sections.management.commands.sync_canvas_sections.SectionMember.objects.bulk_create')
    def test_add_user_list_to_section(self, object_create_mock):
        """
        Tests that a list of SectionMembers will be created with
        the correct section_member_ids
        """
        # these mock the 'next' values of the sequence in the SectionMember table
        mock_sequence_values = [3, 4, 5]

        # these are the users that we should add to the Section Member table
        user_id_list = [1, 2, 3]

        add_user_list_to_section(user_id_list, self.cm_section_id)

        # mocks the parameters to create SectionMember objects
        sm_expected_params = [
            SectionMember(section_member_id=mock_sequence_values[i], 
                section_id=self.cm_section_id, 
                user_id=user_id_list[i], 
                role_id=0, 
                source='Canvas')
            for i in range(0, 3)
        ]

        # check that objects were 'created' using the parameters above
        calls = [call(sm_expected_params)]
        object_create_mock.has_calls(calls, any_order=True)

