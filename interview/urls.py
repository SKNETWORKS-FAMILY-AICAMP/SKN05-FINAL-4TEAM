from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('resume/', views.resume_form, name='resume_form'),
    path('generate_questions/', views.generate_questions, name='generate_questions'),
    path('interview/<int:user_id>/', views.interview_page, name='interview'),
    path('next_question/<int:user_id>/', views.next_question, name='next_question'),
    path('api/check_resume/', views.check_resume, name='check_resume'),
    path('api/check_questions/', views.check_questions, name='check_questions'),
    path('api/interview-report/<int:user_id>/', views.get_interview_report, name='get_interview_report'),
    path('interview-report/<int:user_id>/', views.interview_report, name='interview_report'),
    path('upload_chunk/', views.upload_chunk, name='upload_chunk'),
    path('finalize_audio/', views.finalize_audio, name='finalize_audio'),
    path('transcribe_audio/', views.transcribe_audio, name='transcribe_audio'),
    path('save_answers/', views.save_answers, name='save_answers'),
]