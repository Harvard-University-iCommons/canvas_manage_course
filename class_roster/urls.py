from django.urls import path, re_path

from class_roster import views

urlpatterns = [
    url(r'^index$', views.index, name='index'),
]
