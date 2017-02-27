from django.conf.urls import url

from class_roster import views

urlpatterns = [
    url(r'^index$', views.index, name='index'),
]
