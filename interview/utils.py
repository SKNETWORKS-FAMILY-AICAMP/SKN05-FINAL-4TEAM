import requests
import openai
from django.conf import settings

def call_whisper(audio_file_path):
    """
    Whisper 모델을 호출하여 음성 파일을 텍스트로 변환
    """
    url = "http://213.173.110.107:17709"  # RUNPOD Whisper API URL

    with open(audio_file_path, 'rb') as audio:
        files = {'audio': audio}
        response = requests.post(url, files=files)

    if response.status_code == 200:
        return response.json().get('text')
    else:
        return f"Error: {response.status_code} - {response.text}"
    
openai.api_key = settings.OPENAI_API_KEY

def generate_q(resume_text, evaluation_metrics):
    prompt = f"""
    아래는 한 사람의 이력서 내용입니다. 이 이력서를 바탕으로 다음 기준에 따라 질문을 생성하세요:

    평가 기준:
    {', '.join(evaluation_metrics)}

    이력서 내용:
    {resume_text}

    질문 유형:
    - 주요 프로젝트 경험 관련 질문: 지원자의 주요 프로젝트 경험을 평가하기 위한 구체적인 질문(예:"이 프로젝트에서 당신의 역할과 가장 큰 성과는 무엇인가요?")
    - 문제 해결 사례 기반 질문: 문제 해결 능력을 평가하기 위한 질문(예: "가장 큰 도전 과제를 해결했던 경험과 그 과정에서 배운 점은 무엇인가요?")
    - 팀워크 경험 관련 질문: 팀워크 능력을 평가하기 위한 질문(예:"팀 협업 중 발생한 갈등을 어떻게 해결했는지 설명해주세요.")
    - 자기 개발 노력 관련 질문: 자기 개발 능력과 학습 의지를 평가하기 위한 질문(예: "최근 1년 동안 스스로 발전시키기 위해 가장 집중한 활동은 무엇인가요?")

    각 질문 유형별로 2개의 새로운 질문을 생성해주세요.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI specialized in generating interview questions based on resumes."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        questions = response['choices'][0]['message']['content']
        return questions
    except Exception as e:
        return f"Error: {str(e)}"
    