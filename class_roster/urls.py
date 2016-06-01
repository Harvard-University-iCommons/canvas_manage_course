from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^index$', 'class_roster.views.index', name='index'),
)
