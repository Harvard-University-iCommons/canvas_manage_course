from django.urls import path, re_path

from isites_migration import views


urlpatterns = [
    url(r'^index$', views.index, name='index'),
]
