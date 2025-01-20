from django.db import models

# Create your models here.

class AudioFile(models.Model):
    audio_file = models.FileField(upload_to='audio/')  # 음성 파일 업로드
    transcribed_text = models.TextField(blank=False, null=False)  # 변환된 텍스트
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간

    def __str__(self):
        return f"AudioFile {self.id}"
