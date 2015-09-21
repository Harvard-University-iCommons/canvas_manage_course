from django.conf.urls import url

from isites_migration import views


urlpatterns = [
    url(r'^index$', views.index, name='index'),
]
