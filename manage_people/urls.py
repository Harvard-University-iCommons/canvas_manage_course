from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^user_form$', 'manage_people.views.user_form', name='user_form'),
    url(r'^results_list$', 'manage_people.views.results_list', name='results_list'),
    url(r'^add_users$', 'manage_people.views.add_users', name='add_users'),
    url(r'^remove_user$', 'manage_people.views.remove_user', name='remove_user'),
    url(r'^find_user$', 'manage_people.views.find_user', name='find_user'),
)
