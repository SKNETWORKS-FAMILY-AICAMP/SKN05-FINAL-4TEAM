import re
import io
import json
import boto3
import runpod
import openai
import syllapy
import requests
import numpy as np
from pydub import AudioSegment
from distutils.spawn import find_executable
from pydub.silence import detect_nonsilent
from django.conf import settings
from pydub.utils import which



def audio_to_text(audio_path):
    '''whisper 적용'''
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



def count_syllable(text):
    '''음절 수 카운팅'''
    count = 0
    # 한글 음절 수 세기
    korean_words = re.findall(r'[가-힣]+', text)
    for word in korean_words:
      count += len(word)

    # 영어 음절 수 세기
    english_words = re.findall(r'[a-zA-Z]+', text)
    for word in english_words:
      count += syllapy.count(word)

    return count


def detection(audio_path, silence_thresh=-40, min_silence_len=1000):
    '''실제 스피치 시간을 측정'''
    AudioSegment.converter = which("ffmpeg")
    
    try:
        # 음성 파일 불러오기
        if audio_path.startswith("http"):
            try:
                response = requests.get(audio_path, timeout=10, stream=True)
                response.raise_for_status()
                
                audio_data = io.BytesIO()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        audio_data.write(chunk)
                audio_data.seek(0)
                
                temp_seg = AudioSegment.from_file(audio_data)
                buffer = io.BytesIO()
                temp_seg.export(buffer, format="wav", parameters=["-ac", "1", "-ar", "16000"])
                buffer.seek(0)
                audio_file = buffer
                
            except requests.exceptions.RequestException as e:
                print(f"Error downloading audio: {str(e)}")
                return 0
            except Exception as e:
                print(f"Error processing audio data: {str(e)}")
                return 0
        else:
            audio_file = audio_path

        # 실제 스피치 시간 구하기
        try:
            audio = AudioSegment.from_file(audio_file, format="wav")
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            nonsilent_ranges = detect_nonsilent(
                audio, 
                min_silence_len=min_silence_len, 
                silence_thresh=silence_thresh
            )
            
            if not nonsilent_ranges: 
                return len(audio) / 1000
                
            speech_segments = [end / 1000 - start / 1000 for start, end in nonsilent_ranges]
            total_speech = sum(speech_segments)

            return total_speech

        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            return 0

    except Exception as e:
        print(f"Error in detection: {str(e)}")
        return 0


def stutter(text):
    '''말더듬 체크'''
    prompt = f"""
    면접자의 답변에서 말더듬 유형을 분석하여 정확히 아래 JSON 형식으로만 응답하세요.

    === 말더듬 유형 분류 기준 ===
    1. 단어 일부 반복: "가..강요한" 처럼 단어의 일부분을 반복
    2. 단음절 단어 반복: "옷, 옷" 처럼 한 음절 단어를 반복
    3. 장음화: "디자인---" 처럼 음절을 길게 늘임
    4. 수정 반복: "열, 약" 처럼 단어를 바꾸어 말함
    5. 다음절 단어 반복: "진짜, 진짜" 처럼 두 음절 이상 단어를 반복
    6. 구 반복: "중학교 때, 중학교 때" 처럼 구절을 반복
    7. 군말 삽입: "그~", "막~" 같은 군말을 삽입

    === 분석할 면접자 답변 ===
    {text}

    === 응답 형식 ===
    다음 JSON 형식으로 정확히 응답하세요:
    {{
        "총 카운트": 발견된 말더듬 총 횟수(정수),
        "말더듬 유형": [발견된 말더듬 유형들의 배열]
    }}

    다른 설명이나 추가 텍스트 없이 JSON만 반환하세요.
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 말더듬 분석 전문가입니다. 정확한 JSON 형식으로만 응답합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 응답 형식 검증
            if isinstance(result, dict) and "총 카운트" in result and "말더듬 유형" in result:
                return result

            raise json.JSONDecodeError("Invalid JSON structure", "", 0)

        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                return {"총 카운트": 0, "말더듬 유형": []}
            prompt += "\n\n JSON 형식으로 다시 반환해주세요."



def audio_analysis(audio_path):
    '''비언어적 요소 평가 모델'''
    openai.api_key = settings.OPENAI_API_KEY

    audio_data = audio_to_text(audio_path)
    total_speech = detection(audio_path)

    # 발음
    logprob, compression = [], []
    for seg in audio_data['segments']:
        logprob.append(seg['avg_logprob'])
        compression.append(seg['compression_ratio'])
    logprob, compression = np.mean(logprob), np.mean(compression)
    logprob_score = (logprob+1)*100
    compression_score = 100-(np.abs(compression-1))*50
    pronunciation_score= (logprob_score + compression_score) / 2

    # 빠르기
    syllable_count = count_syllable(audio_data['transcription'])
    SPM = (syllable_count / total_speech) * 60

    # 말더듬
    stutter_result = stutter(audio_data['transcription'])


    # 프롬프트 작성
    prompt = f"""
    면접자의 음성을 평가하고 정확히 아래 JSON 형식으로만 응답하세요.

    === 평가 기준 ===
    1. 발음 점수: {round(pronunciation_score)}/100점
    2. 말하기 속도: {SPM} SPM
    3. 말더듬 횟수: {stutter_result['총 카운트']}회
    4. 말더듬 유형: {stutter_result['말더듬 유형']}

    === 응답 형식 ===
    다음 JSON 형식으로 정확히 응답하세요:
    {{
        "발음": {{
            "점수": 0-100 사이 정수,
            "평가": "한 문장으로 된 평가",
            "개선사항": "한 문장으로 된 개선사항"
        }},
        "빠르기": {{
            "점수": 0-10 사이 정수,
            "평가": "한 문장으로 된 평가",
            "개선사항": "한 문장으로 된 개선사항"
        }},
        "말더듬": {{
            "점수": 0-10 사이 정수,
            "평가": "한 문장으로 된 평가",
            "개선사항": "한 문장으로 된 개선사항"
        }}
    }}

    === 점수 기준 ===
    1. 빠르기 점수:
        - 10점: SPM 353~357
        - 8~9점: SPM 348.5~363.5
        - 6~7점: SPM 263~348.5 또는 363.5~395
        - 0~5점: SPM < 263 또는 SPM > 395

    2. 말더듬 점수:
        - 10점: 0회
        - 8~9점: 1회
        - 6~7점: 2회
        - 0~5점: 3회 이상

    위 형식과 기준을 정확히 따라 평가해주세요.
    다른 설명이나 추가 텍스트 없이 JSON만 반환하세요.
    """

    # 평가 생성 
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 유능한 음성 분석 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            final_result = json.loads(response.choices[0].message.content)
            return final_result, SPM

        except json.JSONDecodeError:
            if attempt == max_retries - 1: 
                return {
                    "발음": {"점수": round(pronunciation_score), "평가": "평가 실패", "개선사항": "재평가 필요"},
                    "빠르기": {"점수": 5, "평가": "평가 실패", "개선사항": "재평가 필요"},
                    "말더듬": {"점수": 5, "평가": "평가 실패", "개선사항": "재평가 필요"}
                }, SPM
            prompt += "\n\n JSON 형식으로 다시 반환해주세요."



def generate_q(resume_text, responsibilities, qualifications, evaluation_metrics):
    '''질문 생성 모델'''
    openai.api_key = settings.OPENAI_API_KEY
    
    prompt = f"""
    아래는 지원자의 이력서 내용과 회사의 담당 업무 및 지원 자격입니다.
    이를 바탕으로 면접 질문을 생성하세요. 

    [지원자의 이력서]
    {resume_text}

    [담당 업무]
    {responsibilities}

    [지원 자격]
    {qualifications}

    다음 형식의 JSON으로 정확히 반환해주세요:
    {{
        "questions": [
            {{
                "question_type": "프로젝트 경험",
                "question_content": [
                    "프로젝트 관련 첫 번째 질문",
                    "프로젝트 관련 두 번째 질문"
                ]
            }},
            {{
                "question_type": "문제 해결",
                "question_content": [
                    "문제 해결 관련 첫 번째 질문",
                    "문제 해결 관련 두 번째 질문"
                ]
            }},
            {{
                "question_type": "팀워크",
                "question_content": [
                    "팀워크 관련 첫 번째 질문",
                    "팀워크 관련 두 번째 질문"
                ]
            }},
            {{
                "question_type": "자기 개발",
                "question_content": [
                    "자기 개발 관련 첫 번째 질문",
                    "자기 개발 관련 두 번째 질문"
                ]
            }},
            {{
                "question_type": "직무 적합성",
                "question_content": [
                    "직무 적합성 관련 첫 번째 질문",
                    "직무 적합성 관련 두 번째 질문"
                ]
            }}
        ]
    }}

    각 질문은:
    1. 실무 관련성과 직무 적합성을 평가할 수 있어야 합니다
    2. 구체적이고 명확해야 합니다
    3. 지원자의 이력서 내용을 반영해야 합니다
    4. 회사의 요구사항과 연관되어야 합니다

    반드시 위의 JSON 형식을 정확하게 지켜주세요.
    """

    # 평가 생성
    while True:
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that always responds in the exact JSON format requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # JSON 형식 검증
            if not isinstance(result, dict) or 'questions' not in result:
                raise json.JSONDecodeError("Invalid JSON format", "", 0)
                
            return result
            
        except json.JSONDecodeError:
            prompt += "\n\n정확히 위의 JSON 형식으로만 응답해주세요."



AWS_STORAGE_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
region = "ap-northeast-2"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=region
)

def upload_to_s3(file_path, s3_key):
    """
    로컬 파일을 AWS S3에 업로드하는 함수
    """
    try:
        extra_args = {
            'ContentType': 'audio/wav',
            'ACL': 'public-read',
            'CacheControl': 'no-cache' 
        }

        s3_client.upload_file(
            file_path, 
            AWS_STORAGE_BUCKET_NAME, 
            s3_key,
            ExtraArgs=extra_args
        )

        url = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{region}.amazonaws.com/{s3_key}"
        response = requests.head(url)
        if response.status_code != 200:
            print(f"Uploaded file is not accessible: {response.status_code}")
            return None
            
        return url
        
    except Exception as e:
        print(f"S3 업로드 실패: {str(e)}")
        return None


# 답변 평가 모델(비언어 평가 제외)
def evaluate_answer(question_text, answer_text, responsibilities, qualifications):
    '''답변 내용 평가 모델'''
    openai.api_key = settings.OPENAI_API_KEY
    
    prompt = f"""
    아래는 면접 질문과 지원자의 응답입니다. 이 응답을 평가 기준에 따라 점수화하고, 각 항목별로 개선사항을 JSON 형식으로 반환하세요.

    === 면접 질문 ===
    {question_text}

    === 지원자 답변 ===
    {answer_text}

    === 평가 기준 및 점수 부여 기준 ===
    1. 질문 이해도 (0~10점):
       - 10점: 질문을 완벽히 이해하고, 논리적으로 답변함.
       - 8~9점: 질문을 이해했으나 일부 부족한 설명이 있음.
       - 6~7점: 질문의 핵심을 이해했으나, 논리적 흐름에서 약간의 오류가 있음.
       - 5점 이하: 질문의 핵심을 충분히 이해하지 못했거나, 명확하지 않은 답변을 제공함.

    2. 논리적 전개 (0~10점):
       - 10점: 서론-본론-결론이 명확하며, 논리적 흐름이 자연스러움.
       - 8~9점: 전체적인 논리는 좋으나 일부 구성이 부족함.
       - 6~7점: 논리적 흐름이 다소 불완전하며, 연결이 부자연스러움.
       - 5점 이하: 논리적 전개가 부족하여 이해하기 어려운 답변임.

    3. 내용의 구체성 (0~10점):
       - 10점: 구체적인 예시와 데이터를 활용하여 풍부한 설명을 제공함.
       - 8~9점: 구체적인 내용이 포함되어 있으나 추가적인 설명이 필요함.
       - 6~7점: 일부 구체성이 부족하며, 답변이 다소 일반적임.
       - 5점 이하: 추상적인 답변으로 인해 이해하기 어려움.

    4. 문제 해결 접근 방식 (0~10점):
       - 10점: 문제 해결 프로세스를 체계적으로 설명하고, 적절한 해결책을 제시함.
       - 8~9점: 문제 해결 과정이 명확하지만, 구체적인 예시가 부족함.
       - 6~7점: 문제 해결 과정이 부분적으로 설명되었으며, 흐름이 다소 불완전함.
       - 5점 이하: 문제 해결 과정이 명확하게 설명되지 않음.

    5. 핵심 기술 및 직무 수행 능력 평가 (0~10점):
       - 10점: 지원자의 기술 역량과 실무 경험이 담당 업무 및 지원 자격 요건과 완벽히 부합함.
       - 8~9점: 기술적 역량과 실무 경험이 대부분 부합하지만, 일부 추가 설명이 필요함.
       - 6~7점: 기술적 역량은 있지만, 실무 경험이 다소 부족하거나 직접적인 연관성이 적음.
       - 5점 이하: 기술적 역량이 담당 업무 및 지원 자격 요건과 크게 부합하지 않음.

    === 회사의 담당 업무 및 지원 자격 ===
    [담당 업무]
    {responsibilities}

    [지원 자격]
    {qualifications}

    === 응답 형식 ===
    다음과 같은 정확한 JSON 형식으로만 응답하세요:
    {{
        "질문 이해도": {{
            "점수": 점수값,
            "개선사항": "개선사항 내용"
        }},
        "논리적 전개": {{
            "점수": 점수값,
            "개선사항": "개선사항 내용"
        }},
        "내용의 구체성": {{
            "점수": 점수값,
            "개선사항": "개선사항 내용"
        }},
        "문제 해결 접근 방식": {{
            "점수": 점수값,
            "개선사항": "개선사항 내용"
        }},
        "핵심 기술 및 직무 수행 능력 평가": {{
            "점수": 점수값,
            "개선사항": "개선사항 내용"
        }}
    }}

    위의 JSON 형식만 반환하고 다른 텍스트는 포함하지 마세요.
    """

    # 평가 생성
    while True:
        try:
            response = openai.chat.completions.create(
                # model="gpt-4",
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 전문 면접관입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            result = json.loads(response.choices[0].message.content)
            return result

        except json.JSONDecodeError:
            prompt += "\n\n JSON 형식으로 다시 반환해주세요."
            continue
        except Exception as e:
            print(f"Error in evaluate_answer: {e}")
            return None

            
# 답변 요약 모델
def summarize_answer(text):
    '''답변 요약 모델'''
    openai.api_key = settings.OPENAI_API_KEY

    prompt = f"""
    당신은 면접 답변을 초압축하여 요약하는 AI임.
    50자 내외, 음슴체 스타일로 핵심만 요약할 것.

    요약 규칙:
    1. 50자 내외로 짧게 작성할 것.
    2. 답변자의 역할, 사용 기술, 성과를 강조할 것.
    3. 문장은 간결하고 명확하게 키워드로 작성할 것.
    4. 불필요한 설명 제거할 것.
    5. 수치는 유지하되, 내용이 중복되지 않도록 할 것.

    면접 답변:
    {text}

    ==반환 형식==
    {{"요약": "요약된 내용"}}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 전문 면접 답변 요약가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        result = json.loads(response.choices[0].message.content)
        if not isinstance(result, dict) or "요약" not in result:
            return {"요약": text}
        
        return result

    except Exception as e:
        print(f"Error in summarize_answer: {e}")
        return {"요약": text}

# 답변 보정 모델
def correct_transcription(text):
    '''Whisper 변환 텍스트 보정'''
    openai.api_key = settings.OPENAI_API_KEY

    prompt = f"""
    Whisper로 변환된 텍스트를 문맥에 맞게 자동 수정해야 함.

    📌 보정 규칙:
    1. 문맥이 이상한 부분을 자연스럽게 수정.
    2. 기술 용어 (AWS, Terraform, CI/CD, DevOps 등) 유지.
    3. 문장이 깨진 경우 자연스럽게 연결.
    4. 핵심 내용을 유지하며 의미를 보완.

    Whisper 변환 텍스트:
    {text}

    ==반환 형식==
    {{"보정된 텍스트": "보정된 내용"}}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "당신은 전문 텍스트 교정가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        result = json.loads(response.choices[0].message.content)
        if not isinstance(result, dict) or "보정된 텍스트" not in result:
            return {"보정된 텍스트": text}
        
        return result

    except Exception as e:
        print(f"Error in correct_transcription: {e}")
        return {"보정된 텍스트": text}
