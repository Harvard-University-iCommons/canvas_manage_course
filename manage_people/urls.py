from django.conf.urls import url

from manage_people import views

urlpatterns = [
    url(r'^user_form$', views.user_form, name='user_form'),
    url(r'^results_list$', views.results_list, name='results_list'),
    url(r'^add_users$', views.add_users, name='add_users'),
    url(r'^remove_user$', views.remove_user, name='remove_user'),
    url(r'^find_user$', views.find_user, name='find_user'),
]
