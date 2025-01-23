from django.urls import path
from . import views
from .views import generate_q

urlpatterns = [
    path('', views.resume_form, name='resume_form'),
    path('resume/', views.resume_form, name='resume_form'),
    path('generate_questions/', generate_q, name='generate_q')
]