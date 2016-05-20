import copy
import random
import uuid

import oauthlib
from unittest import skip

import requests
from django.test import LiveServerTestCase, RequestFactory, TestCase
from mock import patch, DEFAULT, Mock, MagicMock, ANY, call
from requests_oauthlib import OAuth1Session

from canvas_sdk.methods import enrollments
from django_auth_lti import const
from icommons_common.models import (
    CourseEnrollee,
    CourseGuest,
    CourseStaff,
)

from manage_people.views import (
    add_member_to_course,
    get_badge_info_for_users,
    get_badge_label_name,
    get_enrollments_added_through_tool,
    remove_user
)


SQLITE_MAXINT = pow(2, 63)


# TODO: check db/api error handling
# TODO: verify shared cache is cleared
# TODO: verify audit logger is called
# TODO: regression for TLT-2390?
@patch.multiple('django_auth_lti.decorators', is_allowed=Mock(return_value=True))
@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class RemoveUserTests(TestCase):
    longMessage = True

    def setUp(self):
        self.canvas_course_id = str(uuid.uuid4().int)
        self.course_instance_id = uuid.uuid4().int
        self.role_to_remove = 'TeacherEnrollment'
        self.user_id = uuid.uuid4().hex

        self.request = RequestFactory().post('/fake-path')
        self.request.user = Mock(is_authenticated=Mock(return_value=True))
        self.request.POST = {
            'canvas_course_id': self.canvas_course_id,
            'canvas_role': self.role_to_remove,
            'sis_user_id': self.user_id,
        }
        self.request.LTI = {
            'lis_course_offering_sourcedid': self.course_instance_id,
        }

    @patch('manage_people.views.get_course_member_class')
    @patch('manage_people.views.UserRole.objects.get')
    @patch('manage_people.views.enrollments.conclude_enrollment')
    @patch('manage_people.views.get_all_list_data')
    @patch('manage_people.views.ManagePeopleRole.objects.get')
    def test_canvas_enrollments_removed(
            self, mock_mpr_get, mock_sdk_get_all, mock_conclude_enrollment,
            mock_ur_get, mock_get_member_class, *args, **kwargs):
        # get_all_list_data(CTX, enrollments.list_enrollments_users, user_id)
        mock_sdk_get_all.return_value = [
            {'id': 1, 'course_id': self.canvas_course_id,
                'role': self.role_to_remove},
            {'id': 2, 'course_id': self.canvas_course_id,
                'role': 'Course Head'},
            {'id': 5, 'course_id': '1234567890', 'role': 'TaEnrollment'},
        ]

        # call the view
        response = remove_user(self.request)

        # we should only be removing the TeacherEnrollment
        self.assertEqual(mock_conclude_enrollment.call_count, 1)

        # and we should be doing that correctly
        expected_call = call(ANY, self.canvas_course_id, 1, task='delete')
        self.assertIn(expected_call, mock_conclude_enrollment.call_args_list)

        # and the response should be success
        self.assertEqual(response.status_code, 200)

    @patch('manage_people.views.get_course_member_class')
    @patch('manage_people.views.UserRole.objects.get')
    @patch('manage_people.views.enrollments.conclude_enrollment')
    @patch('manage_people.views.get_all_list_data')
    @patch('manage_people.views.ManagePeopleRole.objects.get')
    def test_coursemanger_membership_removed(
            self, mock_mpr_get, mock_sdk_get_all, mock_conclude_enrollment,
            mock_ur_get, mock_get_member_class, *args, **kwargs):
        response = remove_user(self.request)

        # the member class' get method should get called once, with the
        # correct args
        mock_member_class = mock_get_member_class.return_value
        self.assertEqual(mock_member_class.objects.get.call_count, 1)
        self.assertEqual(mock_member_class.objects.get.call_args_list,
                         [call(course_instance_id=self.course_instance_id,
                               user_id=self.user_id)]
        )

        # and the instance's delete method should get called
        mock_member_instance = mock_member_class.objects.get.return_value
        self.assertEqual(mock_member_instance.delete.call_count, 1)

        # and the response should be success
        self.assertEqual(response.status_code, 200)


# TODO: more exception handling tests
# TODO: cache invalidation tests
class AddMemberToCourseTests(TestCase):
    fixtures = ['user_role', 'manage_people_role']
    longMessage = True
    test_data = (
        (0, 'StudentEnrollment', CourseEnrollee),
        (1, 'Course Head', CourseStaff),
        (10, 'Guest', CourseGuest),
    )


    @patch('manage_people.views.add_canvas_course_enrollee')
    @patch('manage_people.views.get_canvas_course_section',
            return_value=None)
    @patch('manage_people.views.Person.objects.filter')
    def test_add_member_to_course(self, mock_person_filter,
            mock_get_canvas_course_section, mock_add_canvas_course_enrollee):
        for user_role_id, canvas_role_label, member_class in self.test_data:
            # ensure we have unique ids for this run, since we're not resetting
            # the db between them
            canvas_course_id = random.randint(1, SQLITE_MAXINT)
            course_instance_id = random.randint(1, SQLITE_MAXINT)
            user_id = random.randint(1, SQLITE_MAXINT)

            # set up mocks
            mock_person = Mock()
            mock_person_filter.return_value = [mock_person]

            # run it
            existing_enrollment, person = add_member_to_course(
                                              user_id, user_role_id,
                                              course_instance_id,
                                              canvas_course_id)

            # validate the results
            self.assertFalse(existing_enrollment)
            self.assertIs(person, mock_person)

            # validate the Person lookup, since we mocked the result
            self.assertEqual(mock_person_filter.call_args_list,
                             [call(univ_id=user_id)])

            # verify the db entry was created
            membership = member_class.objects.filter(
                             user_id=user_id,
                             course_instance_id=course_instance_id,
                             role_id=user_role_id)
            self.assertEqual(membership.count(), 1)

            # verify the canvas enrollment was created
            self.assertEqual(mock_add_canvas_course_enrollee.call_args_list,
                             [call(canvas_course_id, canvas_role_label, user_id)])

            # reset the mocks for the next run
            mock_person_filter.reset_mock()
            mock_add_canvas_course_enrollee.reset_mock()

    @patch('manage_people.views.add_canvas_course_enrollee')
    @patch('manage_people.views.get_course_member_class')
    @patch('manage_people.views.Person.objects.filter')
    def test_add_member_to_course_existing_enrollment(self, mock_person_filter,
            mock_get_course_member_class, mock_add_canvas_course_enrollee):
        # always throw an exception from enrollment.save() to trigger the
        # "existing enrollment" behavior
        mock_member_instance = \
            mock_get_course_member_class.return_value.return_value
        mock_member_instance.save.side_effect = RuntimeError

        for user_role_id, canvas_role_label, member_class in self.test_data:
            # ensure we have unique ids for this run, since we're not resetting
            # the db between them
            canvas_course_id = random.randint(1, SQLITE_MAXINT)
            course_instance_id = random.randint(1, SQLITE_MAXINT)
            user_id = random.randint(1, SQLITE_MAXINT)

            # set up mocks
            mock_person = Mock()
            mock_person_filter.return_value = [mock_person]

            # run it
            existing_enrollment, person = add_member_to_course(
                                              user_id, user_role_id,
                                              course_instance_id,
                                              canvas_course_id)

            # validate the results
            self.assertTrue(existing_enrollment)
            self.assertIs(person, mock_person)

            # validate the Person lookup, since we mocked the result
            self.assertEqual(mock_person_filter.call_args_list,
                             [call(univ_id=user_id)])

            # verify the db entry was not created
            membership = member_class.objects.filter(
                             user_id=user_id,
                             course_instance_id=course_instance_id,
                             role_id=user_role_id)
            self.assertEqual(membership.count(), 0)

            # verify the canvas enrollment was not created
            self.assertEqual(mock_add_canvas_course_enrollee.call_count, 0)

            # reset the mocks for the next run
            mock_person_filter.reset_mock()


# TODO: add test for "not registrar-fed" query logic.  maybe split out?
@patch('manage_people.views.get_all_list_data')
class GetEnrollmentsAddedThroughTool(TestCase):
    longMessage = True
    fixtures = ['manage_people_role']

    def test_get_enrollments_added_through_tool(self, mock_get_all_list_data):
        """ Basic sanity-check positive test. """
        # set up the mock data
        user_id = uuid.uuid4().hex
        course_instance_id = uuid.uuid4().int
        canvas_enrollments = [  # result of enrollments.list_enrollments_sections
            {'user': {'sis_user_id': user_id, 'sortable_name': 'Burn, Acid'},
             'role': 'Guest'},
        ]
        course_enrollees = [  # result of query for non-feed enrollments
            (user_id, 10),  # Guest
        ]

        # set up the mocks
        mock_get_all_list_data.return_value = canvas_enrollments
        mock_course_member = Mock(**{
            'objects.filter.return_value.values_list.return_value':
                course_enrollees,
        })
        # since we're prepping the mock_course_member here, we have to resort
        # to the patch().start() syntax here, instead of decorating it
        patch('manage_people.views.COURSE_MEMBER_CLASSES',
              [mock_course_member]).start()

        # run it
        result = get_enrollments_added_through_tool(course_instance_id)

        # we mocked out get_all_list_data, so verify the call
        self.assertEqual(mock_get_all_list_data.call_args_list,
                         [call(ANY, enrollments.list_enrollments_sections,
                               'sis_section_id:{}'.format(course_instance_id))])

        # verify the result
        self.assertEqual(len(result), 1)
        self.assertIn('badge_label_name', result[0])
        self.assertDictContainsSubset(canvas_enrollments[0], result[0])

    def test_registrar_fed_enrollments_not_returned(self, mock_get_all_list_data):
        """ Ensure that registrar-fed enrollments aren't returned. """
        # set up the mock data
        user_id = uuid.uuid4().hex
        course_instance_id = uuid.uuid4().int
        canvas_enrollments = [  # result of enrollments.list_enrollments_sections
            {'user': {'sis_user_id': user_id, 'sortable_name': 'Burn, Acid'},
             'role': 'Guest'},
        ]
        course_enrollees = [  # result of query for non-feed enrollments
        ]

        # set up the mocks
        mock_get_all_list_data.return_value = canvas_enrollments
        mock_course_member = Mock(**{
            'objects.filter.return_value.values_list.return_value':
                course_enrollees,
        })
        # since we're prepping the mock_course_member here, we have to resort
        # to the patch().start() syntax here, instead of decorating it
        patch('manage_people.views.COURSE_MEMBER_CLASSES',
              [mock_course_member]).start()

        # run it
        result = get_enrollments_added_through_tool(course_instance_id)

        # we mocked out get_all_list_data, so verify the call
        self.assertEqual(mock_get_all_list_data.call_args_list,
                         [call(ANY, enrollments.list_enrollments_sections,
                               'sis_section_id:{}'.format(course_instance_id))])

        # verify the result
        self.assertEqual(len(result), 0)

    def test_mismatched_roles_not_returned(self, mock_get_all_list_data):
        """
        Ensure that manually-added enrollments for a different role don't cause
        us to return registrar-fed enrollments as well.  Basically, a
        regression test for TLT-2403.
        """
        # set up the mock data
        user_id = uuid.uuid4().hex
        course_instance_id = uuid.uuid4().int
        canvas_enrollments = [  # result of enrollments.list_enrollments_sections
            {'user': {'sis_user_id': user_id, 'sortable_name': 'Burn, Acid'},
             'role': 'Guest'},
            {'user': {'sis_user_id': user_id, 'sortable_name': 'Burn, Acid'},
             'role': 'ObserverEnrollment'},
        ]
        course_enrollees = [  # result of query for non-feed enrollments
            (user_id, 10),  # Guest
        ]

        # set up the mocks
        mock_get_all_list_data.return_value = canvas_enrollments
        mock_course_member = Mock(**{
            'objects.filter.return_value.values_list.return_value':
                course_enrollees,
        })
        # since we're prepping the mock_course_member here, we have to resort
        # to the patch().start() syntax here, instead of decorating it
        patch('manage_people.views.COURSE_MEMBER_CLASSES',
              [mock_course_member]).start()

        # run it
        result = get_enrollments_added_through_tool(course_instance_id)

        # we mocked out get_all_list_data, so verify the call
        self.assertEqual(mock_get_all_list_data.call_args_list,
                         [call(ANY, enrollments.list_enrollments_sections,
                               'sis_section_id:{}'.format(course_instance_id))])

        # verify the result
        self.assertEqual(len(result), 1)
        self.assertIn('badge_label_name', result[0])
        self.assertDictContainsSubset(canvas_enrollments[0], result[0])


class GetBadgeInfoForUsersTests(TestCase):
    longMessage = True

    def setUp(self):
        # simulates a call to the Person table, role types map to [library ID, HUID, XID, 'other']
        self.person_object_values = [
            ('02123456', 'WIDENER'), ('98765432', 'STUDENT'), ('ab01yz89', 'XIDHOLDER'), ('1234567890', 'SOMETHINGELSE')
        ]
        self.user_id_input_list = dict(self.person_object_values).keys()
        self.badge_types = [get_badge_label_name(role_type)
                            for role_type in dict(self.person_object_values).values()]
        self.expected_results = dict(zip(self.user_id_input_list, self.badge_types))

        # copy good input and good expected results and add a bad value
        self.bad_input = list(self.user_id_input_list)
        _bad_user_id = 'not a valid ID'
        self.bad_input.append(_bad_user_id)
        self.expected_results_for_bad_input = self.expected_results.copy()
        self.expected_results_for_bad_input[_bad_user_id] = get_badge_label_name(_bad_user_id)

    def test_input_empty_and_none(self):
        """
        If input parameter is empty or None, the function should return an empty dictionary.
        """
        result_for_none = get_badge_info_for_users()
        result_for_empty_list = get_badge_info_for_users([])
        self.assertDictEqual(result_for_none, {})
        self.assertDictEqual(result_for_empty_list, {})

    @patch('manage_people.views.logger.warn')
    @patch('manage_people.views.Person.objects.filter')
    def test_non_matching_input(self, mock_person, mock_logger_warn):
        """
        If input list contains info that doesn't match the Person lookup,
        the function should return all user_ids in the input list, returning a default
        badge label for any user_ids that do not have a role_type_cd, and log a warning.
        """
        mock_person.return_value.values_list.return_value = self.person_object_values
        result = get_badge_info_for_users(self.bad_input)
        self.assertDictEqual(result, self.expected_results_for_bad_input)
        self.assertTrue(mock_logger_warn.called)

    @patch('manage_people.views.logger.warn')
    @patch('manage_people.views.Person.objects.filter')
    def test_matching_input(self, mock_person, mock_logger_warn):
        """
        If input list contains one-to-one matches for Person lookup,
        the function should return a comprehensive mapping of input IDs to badge labels.
        """
        mock_person.return_value.values_list.return_value = self.person_object_values
        result = get_badge_info_for_users(self.user_id_input_list)
        self.assertDictEqual(result, self.expected_results)
        self.assertFalse(mock_logger_warn.called)

    @patch('manage_people.views.Person.objects.filter')
    def test_db_error_raises_exception(self, mock_person):
        """
        If Person lookup fails due to database issue, the function will raise the exception up the stack.
        """
        mock_person.return_value.values_list.side_effect = Exception
        with self.assertRaises(Exception):
            result = get_badge_info_for_users(self.user_id_input_list)


@skip('oauth-related tests failing after porting app to new project')
@patch.multiple('lti_permissions.decorators', is_allowed=MagicMock(return_value=True))
class LTIResourceLinkTests(LiveServerTestCase):
    '''
    Runs against a live server instance so we can use requests to test how
    the server behaves when interacting with multiple tabs in the same session.

    For now, we're patching coursemanager objects because sqlite doesn't like
    schema-scoped tables.

    NOTE: The 'session.auth = None' lines are used to prevent the Oauth1Session
    objects from continuing to sign further requests.  LTI only calls for the
    launch to be signed.

    NOTE: The foo/bar oauth credentials are added in unit_test settings.
    '''
    longMessage = True

    def setUp(self):
        self.resource_link_id = uuid.uuid4().hex
        self.test_user = uuid.uuid4().hex
        self.params = {
            'custom_canvas_api_domain': 'canvas.harvard.edu',
            'custom_canvas_course_id': '5',
            'lis_course_offering_sourcedid': '5',
            'lti_message_type': 'basic-lti-launch-request',
            'lti_version': 'LTI-1p0',
            'resource_link_id': self.resource_link_id,
            'roles': ','.join([const.INSTRUCTOR, const.TEACHING_ASSISTANT,
                               const.ADMINISTRATOR, const.CONTENT_DEVELOPER]),
            'user_id': self.test_user,
        }


    @patch('manage_people.views.CourseInstance.objects.filter')
    def test_lti_launch(self, mock_CourseInstance_filter):
        mock_CourseInstance_filter.returns = []

        # run the launch, verify we get redirected to a url ending in our
        # resource_link_id
        session = OAuth1Session(client_key='foo', client_secret='bar',
                                signature_type=oauthlib.oauth1.SIGNATURE_TYPE_BODY)
        url = self.live_server_url + '/lti_tools/manage_people/lti_launch'
        response = session.post(url, data=self.params, allow_redirects=False)
        self.assertEqual(response.status_code, requests.codes.found)
        self.assertIn('sessionid', response.cookies)
        self.assertTrue(
            response.headers['location'].endswith(self.resource_link_id))

        # try following the redirect, we should get a 200
        session.auth = None
        response2 = session.get(response.headers['location'])
        mock_CourseInstance_filter.assert_called_with(
            pk=self.params['lis_course_offering_sourcedid'])
        self.assertEqual(response2.status_code, requests.codes.ok)

    @patch('manage_people.views.CourseInstance.objects.filter')
    def test_multiple_lti_launch(self, mock_CourseInstance_filter):
        mock_CourseInstance_filter.returns = []

        # run the launch, verify we get redirected to a url ending in our
        # resource_link_id
        session = OAuth1Session(client_key='foo', client_secret='bar',
                                signature_type=oauthlib.oauth1.SIGNATURE_TYPE_BODY)
        url = self.live_server_url + '/lti_tools/manage_people/lti_launch'

        # launch "tab 1" and verify success
        response1 = session.post(url, data=self.params, allow_redirects=False)
        self.assertEqual(response1.status_code, requests.codes.found)
        self.assertIn('sessionid', response1.cookies)
        self.assertTrue(
            response1.headers['location'].endswith(self.resource_link_id))

        # launch "tab 2" and verify success
        params2 = copy.deepcopy(self.params)
        params2['resource_link_id'] = uuid.uuid4().hex
        response2 = session.post(url, data=params2, allow_redirects=False)
        self.assertEqual(response2.status_code, requests.codes.found)
        self.assertIn('sessionid', response2.cookies)
        self.assertTrue(
            response2.headers['location'].endswith(params2['resource_link_id']))

        # follow the "tab 2" redirect and verify 200
        session.auth = None
        response3 = session.get(response2.headers['location'])
        mock_CourseInstance_filter.assert_called_with(
            pk=self.params['lis_course_offering_sourcedid'])
        self.assertEqual(response3.status_code, requests.codes.ok)

        # follow the "tab 1" redirect and verify 200
        response4 = session.get(response1.headers['location'])
        self.assertEqual(response3.status_code, requests.codes.ok)
