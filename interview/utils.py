import runpod
from openai import OpenAI
from django.conf import settings

def whisper_call(audio_path:str):
    runpod.api_key = settings.RUNPOD_API_KEY
    whisper_endpoint = runpod.Endpoint(settings.STT_ENDPOINT)
    try:
        run_request = whisper_endpoint.run_sync(
            {
                "input": {
                    "audio": f"{audio_path}",
                    "model": "medium",
                    "transcription": "formatted_text",
                    "language": "ko"
                    }
        }
    )
        return run_request
    
    except Exception as e:
        print(f"에러 유형: {e.__class__.__name__}")
        print(f"에러 메시지: {e}")


def LLM_call(resume_text, evaluation_metrics):

    client = OpenAI(
        api_key=settings.RUNPOD_API_KEY,
        base_url='https://api.runpod.ai/v2/4oskowl4d4lsl3/openai/v1'
        )
    
    prompt = f"""
    아래는 한 사람의 이력서 내용입니다. 이 이력서를 바탕으로 다음 기준에 따라 면접 질문을 생성하세요:

    평가 기준:
    {', '.join(evaluation_metrics)}

    이력서 내용:
    {resume_text}

    질문 유형:
    - 주요 프로젝트 경험 관련 질문: 지원자의 주요 프로젝트 경험을 평가하기 위한 질문
    - 문제 해결 사례 기반 질문: 문제 해결 능력을 평가하기 위한 질문
    - 팀워크 경험 관련 질문: 팀워크 능력을 평가하기 위한 질문
    - 자기 개발 노력 관련 질문: 자기 개발 능력과 학습 의지를 평가하기 위한 질문

    각 질문 유형별로 2개의 새로운 질문을 생성해주세요.
    JSON 형식으로 결과를 출력하세요.
    """

    try:
        response = client.chat.completions.create(
            model="openchat/openchat-3.5-0106",
            messages=[
                {"role": "user", "content": "You are an AI specialized in generating interview questions based on resumes."},
                {"role": "user", "content": prompt}
                ],
            temperature=0.7
            )
        return response

    except Exception as e:
        print(f"에러 유형: {e.__class__.__name__}")
        print(f"에러 메시지: {e}")