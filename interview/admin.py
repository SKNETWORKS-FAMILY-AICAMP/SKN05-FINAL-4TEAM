from django.contrib import admin
from .models import Resume

# Register your models here.

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'created_at')
