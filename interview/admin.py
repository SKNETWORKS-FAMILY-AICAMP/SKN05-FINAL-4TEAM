from django.contrib import admin
from .models import Resume, Question, JobPosting, Answer, Evaluation

# JobPosting 모델 등록
@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'job_title', 'created_at')
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
    list_display = ('user_id', 'text', 'category', 'order', 'is_used', 'created_at')
    search_fields = ('text',)
    list_filter = ('category', 'is_used')
    
# answer 모델 등록
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'get_question', 'transcribed_text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('question__text', 'transcribed_text')

    def get_question(self, obj):
        return obj.question.text[:50]
    
    get_question.short_description = "Question"

# evaluation 모델 등록
@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_answer', 'total_score', 'created_at')
    list_filter = ('total_score', 'created_at')
    search_fields = ('answer__question__text',)

    def get_answer(self, obj):
        return f"Answer for Q{obj.answer.question.order}"
    
    get_answer.short_description = "Answer"

