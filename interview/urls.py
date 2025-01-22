from django.urls import path
from . import views

urlpatterns = [
    path('', views.resume_form, name='resume_form'),
    path('resume/', views.resume_form, name='resume_form'),
]