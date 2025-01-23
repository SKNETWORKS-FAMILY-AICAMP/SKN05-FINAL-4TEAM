from django.urls import path
from . import views
from .views import generate_questions

urlpatterns = [
    path('', views.resume_form, name='resume_form'),
    path('resume/', views.resume_form, name='resume_form'),
    path('generate_questions/', generate_questions, name='generate_q')
]