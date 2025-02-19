from django.db import models



class JobPosting(models.Model):
    company_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    responsibilities = models.TextField(default="")
    qualifications = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.job_title}"


class Resume(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15) 
    email = models.EmailField()
    
    project_experience = models.TextField(default="")
    problem_solving = models.TextField(default="")
    teamwork_experience = models.TextField(default="")
    self_development = models.TextField(default="")

    job_posting = models.ForeignKey(JobPosting, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Question(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, null=True)
    text = models.TextField(default="")
    category = models.CharField(max_length=100)
    order = models.IntegerField()
    is_used = models.BooleanField(default=False)
    job_posting = models.ForeignKey('JobPosting', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question {self.order}: {self.text[:50]}..."

    def get_job_posting(self):
        """job_posting 정보를 가져오는 메서드"""
        return self.job_posting or self.resume.job_posting


class Answer(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True)
    audio_url = models.URLField(null=True, blank=True) 
    transcribed_text = models.TextField(default="") 
    summarized_text = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer for Question {self.question.order}"


class Evaluation(models.Model):
    answer = models.OneToOneField(Answer, on_delete=models.CASCADE, null=True)
    scores = models.JSONField(default=dict)
    total_score = models.IntegerField(default=0)
    improvements = models.JSONField(default=list)
    nonverbal_scores = models.JSONField(default=dict)
    nonverbal_improvements = models.JSONField(default=list)
    spm = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation for Answer {self.answer.id}"