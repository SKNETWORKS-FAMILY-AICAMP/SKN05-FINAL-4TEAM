from django.urls import path
from . import views
from .views import generate_questions,interview_page, next_question, check_resume, check_questions, interview_report

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('resume/', views.resume_form, name='resume_form'),
    path('generate_questions/', views.generate_questions, name='generate_questions'),
    path('interview/<int:user_id>/', views.interview_page, name='interview'),
    path('next_question/<int:user_id>/', views.next_question, name='next_question'),
    path('api/check_resume/', views.check_resume, name='check_resume'),
    path('api/check_questions/', views.check_questions, name='check_questions'),
    path('report/<int:user_id>/', views.interview_report, name='interview_report'),
]