from django.db import models

# Create your models here.

class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio/')  # 음성 파일 업로드
    transcribed_text = models.TextField(blank=False, null=False)  # 변환된 텍스트
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간

    def __str__(self):
        return f"AudioFile {self.id}"
    
# jobposting 
class JobPosting(models.Model):
    company_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    responsibilities = models.TextField(default="") # 담당 업무
    qualifications = models.TextField(default="") # 지원 자격
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.job_title}"

# Resume
class Resume(models.Model):
    name = models.CharField(max_length=100) # 지원자 이름
    phone = models.CharField(max_length=15) # 연락처
    email = models.EmailField() # 이메일
    
    project_experience = models.TextField(default="")
    problem_solving = models.TextField(default="")
    teamwork_experience = models.TextField(default="")
    self_development = models.TextField(default="")

    job_posting = models.ForeignKey(JobPosting, on_delete=models.SET_NULL,null=True, blank=True) # 지원공고 연결

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# questions
class Question(models.Model):
    user_id = models.IntegerField()
    text = models.TextField()
    category = models.CharField(max_length=100)
    order = models.IntegerField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"User {self.user_id} | {self.category} | Order {self.order}"

