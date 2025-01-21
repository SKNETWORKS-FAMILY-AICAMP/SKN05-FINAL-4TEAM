from django.db import models

# Create your models here.

class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio/')  # 음성 파일 업로드
    transcribed_text = models.TextField(blank=False, null=False)  # 변환된 텍스트
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간

    def __str__(self):
        return f"AudioFile {self.id}"

# Resume
class Resume(models.Model):
    name = models.CharField(max_length=100) # 지원자 이름
    email = models.EmailField() # 이메일
    phone = models.CharField(max_length=15) # 연락처
    resume_file = models.FileField(upload_to='resumnes/') # s3에 저장된 이력서 파일 경로
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class ProjectExperience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='projects')
    project_name = models.CharField(max_length=200)
    tech_stack = models.CharField(max_length=300)
    role = models.CharField(max_length=100)
    result = models.TextField()

    def __str__(self):
        return f"{self.project_name} - {self.resume.name}" # 프로젝트 명과 연결된 지원자 이름 반환

class ProgrammingSkill(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    language = models.CharField(max_length=100)
    level = models.CharField(
        max_length=10,
        choices=(('상','상'), ('중','중'), ('하','하'))
    )

    def __str__(self):
        return f"{self.language} ({self.level})"
    
class AdditionalInfo(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='aditional_info')
    content = models.TextField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"기타 사항 ({self.resume.name})"
    