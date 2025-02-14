# Generated by Django 5.1.5 on 2025-02-14 19:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0004_answer_evaluation_delete_audiofile_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='answer',
            name='user_id',
        ),
        migrations.RemoveField(
            model_name='question',
            name='user_id',
        ),
        migrations.AddField(
            model_name='answer',
            name='resume',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='interview.resume'),
        ),
        migrations.AddField(
            model_name='question',
            name='job_posting',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='interview.jobposting'),
        ),
        migrations.AddField(
            model_name='question',
            name='resume',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='interview.resume'),
        ),
        migrations.AlterField(
            model_name='answer',
            name='audio_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='evaluation',
            name='total_score',
            field=models.IntegerField(default=0),
        ),
    ]
