from django.urls import path
from . import views
from .views import generate_questions

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('resume/', views.resume_form, name='resume_form'),
    path('generate_questions/', views.generate_questions, name='generate_questions'),
    path('practice_interview/<int:user_id>/', views.practice_interview_page, name='practice_interview'),
    path('interview/<int:user_id>/', views.interview_page, name='interview'),
    path('next_question/<int:user_id>/', views.next_question, name='next_question'),
]