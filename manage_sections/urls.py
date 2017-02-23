from django.conf.urls import url

from manage_sections import views


urlpatterns = [
    url(r'^create_section_form$', views.create_section_form, name='create_section_form'),
    url(r'^create_section$', views.create_section, name='create_section'),
    url(r'^edit_section/(?P<section_id>\d+)$', views.edit_section, name='edit_section'),
    url(r'^section_details/(?P<section_id>\d+)$', views.section_details, name='section_details'),
    url(r'^remove_section/(?P<section_id>\d+)$', views.remove_section, name='remove_section'),
    url(r'^remove_from_section$', views.remove_from_section, name='remove_from_section'),
    url(r'^sections/(?P<section_id>\d+)/classlist$', views.section_class_list, name='section_class_list'),
    url(r'^section_user_list/(?P<section_id>\d+)$', views.section_user_list, name='section_user_list'),
    url(r'^add_to_section$', views.add_to_section, name='add_to_section'),
    url(r'^monitor$', views.MonitorResponseView.as_view()),
]
