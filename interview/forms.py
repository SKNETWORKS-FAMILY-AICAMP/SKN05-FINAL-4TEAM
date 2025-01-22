from django import forms
from .models import Resume

class ResumeForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['name','phone','email','project_experience','problem_solving','teamwork_experience', 'self_development']
        