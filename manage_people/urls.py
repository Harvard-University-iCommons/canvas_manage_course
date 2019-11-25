from django.urls import path, re_path

from manage_people import views

urlpatterns = [
    path('user_form', views.user_form, name='user_form'),
    path('results_list', views.results_list, name='results_list'),
    path('add_users', views.add_users, name='add_users'),
    path('remove_user', views.remove_user, name='remove_user'),
    path('find_user', views.find_user, name='find_user'),
]
