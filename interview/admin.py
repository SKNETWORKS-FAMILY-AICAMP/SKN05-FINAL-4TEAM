from django.contrib import admin
from .models import Resume, Question

# Register your models here.

# resume 모델 등록
@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
    search_fields = ('name', 'email')

    
# question 모델 등록
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'text', 'category','order', 'is_used', 'created_at')
    list_filter = ('category', 'is_used')
    search_fields = ('text',)
    