from unittest import TestCase

from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, ANY, DEFAULT, Mock, MagicMock

from manage_sections.views import edit_section


@patch.multiple('manage_sections.views', render=DEFAULT)
@patch.multiple('manage_sections.views.canvas_api_helper_sections',
                get_section=DEFAULT, update_section=DEFAULT)
class EditSectionViewTest(TestCase):
    longMessage = True

    def setUp(self):
        self.resource_link_id = 'abc123'
        self.canvas_course_id = 1234
        self.section_id = 567
        self.section_name = 'New Section Name'

    def edit_section_request_stub(self, **post_kwargs):
        request = RequestFactory().post('/fake-path', data=post_kwargs)
        request.user = Mock(name='user_mock')
        request.user.is_authenticated.return_value = True
        request.LTI = {
            'resource_link_id': self.resource_link_id,
            'custom_canvas_course_id': self.canvas_course_id,
            'roles': [const.INSTRUCTOR]
        }
        return request

    @patch('manage_sections.views.logger.error')
    def test_error_status_on_whitespace_section_name(self, error_log, render, **mock_kwargs):
        """Edit Section should return 400 if the section name contains only whitespace"""
        request = self.edit_section_request_stub(section_name_input='     ')
        edit_section(request, self.section_id)
        render.assert_called_once_with(request, ANY, ANY, status=400)

    @patch('manage_sections.views.logger.error')
    def test_error_template_on_whitespace_section_name(self, error_log, render, **mock_kwargs):
        """Edit Section should render correct template if the section name contains only whitespace"""
        request = self.edit_section_request_stub(section_name_input='     ')
        edit_section(request, self.section_id)
        render.assert_called_with(request, 'manage_sections/create_section_form.html', ANY, status=ANY)

    @patch('manage_sections.views.logger.error')
    def test_render_on_whitespace_section_name(self, error_log, render, **mock_kwargs):
        """Edit Section should render correct template if the section name contains only whitespace"""
        request = self.edit_section_request_stub(section_name_input='     ')
        edit_section(request, self.section_id)
        render.assert_called_with(request, ANY, {}, status=ANY)

    @patch('manage_sections.views.logger.error')
    def test_error_status_on_missing_section_name(self, error_log, render, **mock_kwargs):
        """Edit Section should return return 400 if section name missing"""
        request = self.edit_section_request_stub()
        edit_section(request, self.section_id)
        render.assert_called_once_with(request, 'manage_sections/create_section_form.html', ANY, status=400)

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.logger.error')
    def test_error_status_on_exception_retrieving_section(self, error_log,
            is_editable_section, get_section, update_section, render,
            **mock_kwargs):
        """Ensure template renders a 500 status when update_section raises an exception"""
        get_section.return_value = MagicMock(name=self.section_name)
        update_section.side_effect = RuntimeError
        is_editable_section.return_value = True
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        render.assert_called_once_with(request,
            'manage_sections/create_section_form.html', ANY, status=500)

    @patch('manage_sections.views.is_editable_section')
    def test_update_section_util_params(self, is_editable_section, get_section,
            update_section, **mock_kwargs):
        """Ensure that the canvas util method to update a section is called with
        expected params"""
        get_section.return_value = MagicMock(name=self.section_name)
        is_editable_section.return_value = True
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        update_section.assert_called_once_with(
            self.canvas_course_id, self.section_id, course_section_name=self.section_name
        )

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.logger.error')
    def test_error_template_on_failed_section_update(self, error_log,
            is_editable_section, get_section, update_section, render,
            **mock_kwargs):
        """Ensure right template is rendered when call to update section returns
        None"""
        get_section.return_value = MagicMock(name=self.section_name)
        is_editable_section.return_value = True
        update_section.return_value = None
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        render.assert_called_once_with(request, 'manage_sections/create_section_form.html',
                                       ANY, status=ANY)

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.logger.error')
    def test_error_status_on_failed_section_update(self, error_log,
            is_editable_section, get_section, update_section, render,
            **mock_kwargs):
        """Ensure status code of 500 when call to update section returns None"""
        get_section.return_value = MagicMock(name=self.section_name)
        is_editable_section.return_value = True
        update_section.return_value = None
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        render.assert_called_once_with(ANY, ANY, ANY, status=500)

    @patch('manage_sections.views.is_editable_section')
    def test_enrollment_count_set_on_updated_section(self,
            is_editable_section, get_section, update_section, **mock_kwargs):
        """Ensure enrollment count that is posted gets set on updated section"""
        get_section.return_value = MagicMock(name=self.section_name)
        is_editable_section.return_value = True
        section_mock = MagicMock(name='updated_section')
        update_section.return_value = section_mock
        enrollment_count = '150'  # Post params get converted to strings
        request = self.edit_section_request_stub(
                      section_name_input=self.section_name,
                      enrollment_count=enrollment_count)
        edit_section(request, self.section_id)
        section_mock.__setitem__.assert_called_once_with(
            'enrollment_count', enrollment_count)

    @patch('manage_sections.views.is_editable_section')
    def test_enrollment_count_defaults_to_zero_on_updated_section(self,
            is_editable_section, get_section, update_section, **mock_kwargs):
        """Ensure if no enrollment_count is passed in with post params, it's
        set to 0 on updated section"""
        get_section.return_value = MagicMock(name=self.section_name)
        is_editable_section.return_value = True
        section_mock = MagicMock(name='updated_section')
        update_section.return_value = section_mock
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        section_mock.__setitem__.assert_called_once_with('enrollment_count', 0)

    @patch('manage_sections.views.is_editable_section')
    def test_success_template(self, is_editable_section, get_section, render,
            **mock_kwargs):
        """ Ensure that correct template name rendered on success """
        section_mock = MagicMock(name=self.section_name)
        get_section.return_value = section_mock
        is_editable_section.return_value = True
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        render.assert_called_once_with(request, 'manage_sections/section_list.html', ANY)

    @patch('manage_sections.views.is_editable_section')
    def test_success_template_context_section(self, is_editable_section,
            get_section, update_section, render, **mock_kwargs):
        """ Ensure that updated section is passed in to template context """
        section_mock = MagicMock(name=self.section_name)
        get_section.return_value = section_mock
        is_editable_section.return_value = True
        request = self.edit_section_request_stub(section_name_input=self.section_name)
        edit_section(request, self.section_id)
        render.assert_called_once_with(ANY, ANY,
            {'section': update_section.return_value})

    @patch('manage_sections.views.is_editable_section')
    @patch('manage_sections.views.JsonResponse')
    def test_non_editable_section_returns_error(self, JsonResponse,
            is_editable_section, get_section, **mock_kwargs):
        """ Ensure a 422 status code is returned on an attempt to edit an
        uneditable section. """
        section_mock = MagicMock(name=self.section_name)
        get_section.return_value = section_mock
        is_editable_section.return_value = False
        request = self.edit_section_request_stub(
                      section_name_input=self.section_name)
        edit_section(request, self.section_id)
        JsonResponse.assert_called_once_with(ANY, status=422)
