from django.urls import path

from fa_info import views

urlpatterns = [
    path('index', views.index, name='index'),
]
