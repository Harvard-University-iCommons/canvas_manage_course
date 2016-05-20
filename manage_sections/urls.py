from django.conf.urls import patterns, url

from .views import MonitorResponseView

urlpatterns = patterns(
    '',
    url(r'^create_section_form$', 'manage_sections.views.create_section_form', name='create_section_form'),
    url(r'^create_section$', 'manage_sections.views.create_section', name='create_section'),
    url(r'^edit_section/(?P<section_id>\d+)$', 'manage_sections.views.edit_section', name='edit_section'),
    url(r'^section_details/(?P<section_id>\d+)$', 'manage_sections.views.section_details', name='section_details'),
    url(r'^remove_section/(?P<section_id>\d+)$', 'manage_sections.views.remove_section', name='remove_section'),
    url(r'^remove_from_section$', 'manage_sections.views.remove_from_section', name='remove_from_section'),
    url(r'^sections/(?P<section_id>\d+)/classlist$', 'manage_sections.views.section_class_list', name='section_class_list'),
    url(r'^section_user_list/(?P<section_id>\d+)$', 'manage_sections.views.section_user_list', name='section_user_list'),
    url(r'^add_to_section$', 'manage_sections.views.add_to_section', name='add_to_section'),
    url(r'^monitor$', MonitorResponseView.as_view()),
)
