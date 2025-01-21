from django.contrib import admin
from .models import Resume, ProjectExperience, ProgrammingSkill, AdditionalInfo 

# Register your models here.

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')

@admin.register(ProjectExperience)
class ProjectExperienceAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'tech_stack', 'role', 'resume')

@admin.register(ProgrammingSkill)
class ProgrammingSkillAdmin(admin.ModelAdmin):
    list_display = ('language', 'level', 'resume')

@admin.register(AdditionalInfo)
class AdditionalInfoAdmin(admin.ModelAdmin):
    list_display = ('content', 'date', 'resume')