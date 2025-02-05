import json
import runpod
import openai
from django.conf import settings

def audio_to_text(audio_path):
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



def generate_q(resume_text, responsibilities, qualifications, evaluation_metrics):
    openai.api_key = settings.OPENAI_API_KEY
    prompt = f"""
    아래는 지원자의 이력서 내용과 회사의 담당 업무 및 지원 자격입니다.
    이를 바탕으로 면접 질문을 생성하세요. 각 질문은 실무 관련성과 직무 적합성을 평가할 수 있도록 작성하며, 평가 기준과 담당 업무 및 지원 자격을 반영하여 질문을 생성하세요:

    평가 기준:
    {', '.join(evaluation_metrics)}

    [지원자의 이력서]
    {resume_text}

    [담당 업무]
    {responsibilities}

    [지원 자격]
    {qualifications}

    질문 유형:
    1. 주요 프로젝트 경험 관련 질문: 지원자의 주요 프로젝트 경험을 평가하기 위한 질문
    2. 문제 해결 사례 기반 질문: 문제 해결 능력을 평가하기 위한 질문
    3. 팀워크 및 협업 관련 질문: 팀워크 능력을 평가하기 위한 질문
    4. 자기 개발 노력 관련 질문: 자기 개발 능력과 학습 의지를 평가하기 위한 질문
    5. 지원 자격과 관련된 질문: 예를 들어, 코드 리뷰, 테스트 코드 작성, RDB 모델링 최적화 등 지원 자격에 명시된 항목과 관련된 질문

    각 질문 유형별로 2개의 구체적인 질문을 작성하세요.
    특히 지원 자격과 관련된 항목(예: 코드 리뷰, 테스트 코드 작성, 대규모 트래픽 처리)에 대한 질문을 포함해주세요.
    결과를 JSON 형식으로 반환하세요.
    """

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
        )
    
    return json.loads(response.choices[0].message.content)
