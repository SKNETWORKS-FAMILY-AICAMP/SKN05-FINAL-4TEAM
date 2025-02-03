from django.contrib import admin
from .models import Resume, Question, JobPosting 

# Register your models here.

# JobPosting 모델 등록
@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'job_title','created_at')
    search_fields = ('company_name', 'job_title')
    list_filter = ('company_name',)

# resume 모델 등록
@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'get_job_posting', 'created_at')
    search_fields = ('name', 'email')
    list_filter = ('job_posting',) 
    raw_id_fields = ('job_posting',)

    def get_job_posting(self, obj): # job_posting은 FK이므로 관리자페이지에서 문자열로 표시되지 않음
        return obj.job_posting.company_name if obj.job_posting else "N/A"
    
    get_job_posting.short_description = "지원공고 (회사명)"

# question 모델 등록
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'text', 'category','order', 'is_used', 'created_at')
    list_filter = ('category', 'is_used')
    search_fields = ('text',)
    