from unittest import TestCase

from django.test import RequestFactory
from django_auth_lti import const
from mock import patch, ANY, DEFAULT, Mock

from manage_sections.views import section_details


@patch.multiple('manage_sections.views', is_editable_section=DEFAULT, render=DEFAULT)
@patch.multiple('manage_sections.views.canvas_api_helper_sections', get_section=DEFAULT)
@patch.multiple('lti_permissions.decorators', is_allowed=Mock(return_value=True))
class SectionDetailsViewTest(TestCase):
    longMessage = True

    def setUp(self):
        self.canvas_course_id = 6402
        self.resource_link_id = 1234
        self.section_id = 5678
        self.sis_section_id = 8989
        self.request = RequestFactory().get('/fake-path')
        self.request.user = Mock(name='user_mock')
        self.request.user.is_authenticated.return_value = True
        self.request.LTI = {
            'custom_canvas_course_id': self.canvas_course_id,
            'resource_link_id': self.resource_link_id,
            'roles': [const.INSTRUCTOR]
        }

    def get_render_context_value(self, render_mock, context_key):
        """ Returns the value of the context dictionary key associated with the render mock object """
        context = render_mock.call_args[0][2]
        return context.get(context_key)

    def test_retrieve_section_by_id(self, get_section, is_editable_section, render):
        """ Ensure that get_section was called with id passed into view """
        section_details(self.request, self.section_id)
        get_section.assert_called_once_with(self.canvas_course_id, self.section_id)

    def test_is_editable_section_called(self, get_section, is_editable_section, render):
        """ Ensure is_editable_section is called using return value from get_section """
        section_details(self.request, self.section_id)
        is_editable_section.assert_called_once_with(get_section.return_value)

    def test_rendered_template_name(self, get_section, is_editable_section, render):
        """ Ensure name of rendered section is expected """
        section_details(self.request, self.section_id)
        render.assert_called_once_with(ANY, 'manage_sections/section_details.html', ANY)
        
    def test_rendered_template_context_contains_section_id(self, get_section, is_editable_section, render):
        """ Ensure expected section_id contained in template context """
        section_details(self.request, self.section_id)
        self.assertEqual(self.get_render_context_value(render, 'section_id'), self.section_id)

    def test_rendered_template_context_contains_section_name(self, get_section, is_editable_section, render):
        """ Ensure expected section name contained in template context """
        section_name = 'test-section-name'
        get_section.return_value = {'name': section_name}
        section_details(self.request, self.section_id)
        self.assertEqual(self.get_render_context_value(render, 'section_name'), section_name)

    def test_rendered_template_context_allows_edit_when_section_is_not_primary(self, get_section, is_editable_section, render):
        """ Ensure sections that are not primary are allowed to be edited per context variable """
        is_editable_section.return_value = True
        section_details(self.request, self.section_id)
        self.assertEqual(self.get_render_context_value(render, 'allow_edit'), True)

    def test_rendered_template_context_disallows_edit_when_section_is_primary(self, get_section, is_editable_section, render):
        """ Ensure sections that are primary are not allowed to be edited per context variable """
        is_editable_section.return_value = False
        section_details(self.request, self.section_id)
        self.assertEqual(self.get_render_context_value(render, 'allow_edit'), False)
