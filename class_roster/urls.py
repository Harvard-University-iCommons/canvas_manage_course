from django.urls import path

from class_roster import views

urlpatterns = [
    path('index', views.index, name='index'),
]
