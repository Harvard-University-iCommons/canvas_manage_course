from django.urls import path, re_path

from manage_sections import views

urlpatterns = [
    path('create_section_form', views.create_section_form, name='create_section_form'),
    path('create_section', views.create_section, name='create_section'),
    path('edit_section/<str:sis_section_id>/<int:section_id>', views.edit_section, name='edit_section'),
    path('section_details/<str:sis_section_id>/<int:section_id>', views.section_details, name='section_details'),
    path('remove_section/<str:sis_section_id>/<int:section_id>', views.remove_section, name='remove_section'),
    path('remove_from_section', views.remove_from_section, name='remove_from_section'),
    re_path(r'^sections/(?P<section_id>\d+)/classlist$', views.section_class_list, name='section_class_list'),
    path('section_user_list/<int:section_id>', views.section_user_list, name='section_user_list'),
    path('add_to_section', views.add_to_section, name='add_to_section'),
    path('monitor', views.MonitorResponseView.as_view()),
]
