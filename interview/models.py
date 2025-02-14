from django.db import models
    
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

    job_posting = models.ForeignKey(JobPosting, on_delete=models.SET_NULL, null=True, blank=True) # 지원공고 연결
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# questions
class Question(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, null=True)  # null=True 추가
    text = models.TextField()
    category = models.CharField(max_length=100)
    order = models.IntegerField() # 질문 순서
    is_used = models.BooleanField(default=False) # 사용 여부
    job_posting = models.ForeignKey('JobPosting', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question {self.order}: {self.text[:50]}..."

    def get_job_posting(self):
        """job_posting 정보를 가져오는 메서드"""
        return self.job_posting or self.resume.job_posting

# 답변
class Answer(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, null=True)  # null=True 추가
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    audio_url = models.URLField(null=True, blank=True)  # S3에 저장된 음성 파일 URL 
    transcribed_text = models.TextField()  # Whisper로 변환된 텍스트
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer for Question {self.question.order}"

# 평가
class Evaluation(models.Model):
    answer = models.OneToOneField(Answer, on_delete=models.CASCADE)
    total_score = models.IntegerField(default=0)  # 총점 (50점 만점)
    
    # 평가 점수들 (각각 10점 만점)
    scores = models.JSONField(default=dict)  
    
    # 비언어적 평가 점수들 (각각 10점 만점)
    nonverbal_scores = models.JSONField(default=dict) 
    
    # 개선사항 피드백
    improvements = models.JSONField(default=list)  # ["개선사항1", "개선사항2", ...]
    nonverbal_improvements = models.JSONField(default=list)  # ["비언어적 개선사항1", ...]
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation for Answer {self.answer.id}"

