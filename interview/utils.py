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
from pydub.silence import detect_nonsilent
from django.conf import settings



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
  # 음성 파일 불러오기
  if audio_path.startswith("http"):
    response = requests.get(audio_path)
    audio_file = io.BytesIO(response.content)
  else:
    audio_file = audio_path
  # 실제 스피치 시간 구하기
  audio = AudioSegment.from_file(audio_file, format="wav").set_frame_rate(16000).set_channels(1)
  nonsilent_ranges = detect_nonsilent(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
  speech_segments = [end / 1000 - start / 1000 for start, end in nonsilent_ranges]
  total_speech = sum(speech_segments)

  return total_speech



def stutter(text):
  '''말더듬 체크'''
  prompt = f"""
  다음은 말더듬의 유형입니다.
  ==말더듬 유형==
  1. 단어 일부 반복
  예시: 아니, 가..강요한 우리 잘못이래잖아?

  2. 단음절 단어 반복
  예시: 나는 진짜 옷, 옷 안 샀어.

  3. 장음화
  예시: 디자인---까진 모르겠어.

  4. 수정 반복
  예시: 근데 그게 사람에게 열, 약, 결점을 보완하기 위해 준 능력이란 말이야?

  5. 다음절 단어 반복
  예시: 근데 진짜, 진짜 햄 그런 거 하나도 안 주고, 빵이랑 쨈만 줘.

  6. 구 반복
  예시: 중학교 때, 중학교 때 얘가 진짜 뚱뚱했었거든?

  7. 군말 삽입
  예시: 사형수들을 실미도로 데려가서, 진짜 인간들이 할 수 없는 그런, 막~ 그~ 교육을 시키는데...


  주어진 면접자의 답변에 대해서 말더듬 유형을 체크해서 카운팅을 해라.
  면접자 답변: {text}


  ==반환 형식==
  총 카운트와 말더듬 유형을 JSON 형식으로 반환해라.
  한국어만 사용해라.
  (총 카운트와 체크된 말더듬 유형을 제외한 그 어떤 문자열도 반환하지 마라.)
  """

  # 평가 생성
  while True:
    try:
      response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "당신은 유능한 음성 분석 전문가입니다."},
          {"role": "user", "content": prompt}
          ],
        temperature=0.0
        )
        
      result = json.loads(response.choices[0].message.content)
      
      return result

    except json.JSONDecodeError:
        prompt += "\n\n JSON 형식으로 다시 반환해주세요."
        stutter(text)



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
  면접자의 음성에 대한 평가 지표가 다음과 같이 주어진다.
  이를 바탕으로 면접자를 평가하고, 필요하다면 개선사항을 제시해라.
  이때 점수에 따른 평가 내용은 일관성을 유지해라.


  === 평가 지표 ===
  1. 발음 (0~100점)
  면접자의 발음 점수: {round(pronunciation_score)}
  발음 점수를 바탕으로 평가해라.

  2. 빠르기 (0~10점)
  - 10점: SPM이 353~357 범위에 있는 경우 (아주 적당한 말 빠르기)
  - 8~9점: SPM이 348.5~363.5 범위에 있는 경우 (일반적인 말 빠르기)
  - 6~7점: SPM이 263~348.5 범위에 있는 경우 (약간 느린 말 빠르기) 또는 363.5~395 범위에 있는 경우 (약간 빠른 말 빠르기)
  - 0~5점: SPM이 263보다 작은 경우 (매우 느린 말 빠르기) 또는 395보다 큰 경우 (매우 빠른 말 빠르기)
  (특히 0~5점 구간대에 해당한다면, 스스로 합리적으로 판단하여 그 구간 내의 적절한 점수를 부과해라)
  면접자의 SPM: {SPM}
  면접자의 SPM과 위의 평가 기준을 바탕으로 평가해라.

  3. 말더듬 (0~10점)
  - 10점: 말더듬 횟수가 0회인 경우
  - 8~9점: 말더듬 횟수가 1회인 경우
  - 6~7점: 말더듬 횟수가 2회인 경우
  - 0~5점: 말더듬 횟수가 3회 이상인 경우
  (특히 0~5점 구간대에 해당한다면, 스스로 합리적으로 판단하여 그 구간 내의 적절한 점수를 부과해라)
  면접자의 말더듬 횟수: {stutter_result['총 카운트']}
  면접자의 말더듬 유형: {stutter_result['말더듬 유형']}
  면접자의 말더듬과 위의 평가 기준을 바탕으로 평가해라.



  === 평가 결과 ===
  다음 형식을 따라 평가 결과를 JSON 타입으로 반환해라.
  한국어만 사용해라.
  평가에 기술 용어들의 언급은 피하고, 사용자 친화적인 용어들로 평가를 해라.
  (발음, 빠르기, 말더듬을 제외한 그 어떤 문자열도 반환하지 마라.)

  발음: 평가 내용, 점수, (필요한 경우)개선사항
  빠르기: 평가 내용, 점수, (필요한 경우)개선사항
  말더듬: 평가 내용, 점수, (필요한 경우)개선사항
  """

  # 평가 생성
  while True:
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
      
      return final_result, pronunciation_score, SPM, stutter_result['총 카운트'], stutter_result['말더듬 유형'], audio_data['transcription']

    except json.JSONDecodeError:
        prompt += "\n\n JSON 형식으로 다시 반환해주세요."



def generate_q(resume_text, responsibilities, qualifications, evaluation_metrics):
    '''질문 생성 모델'''
    openai.api_key = settings.OPENAI_API_KEY
    
    # 프롬프트 작성
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
    :param file_path: 로컬 파일 경로
    :param s3_key: S3 버킷 내 저장될 파일 경로
    :return: S3 URL
    """
    try:
        s3_client.upload_file(file_path, AWS_STORAGE_BUCKET_NAME, s3_key)
        s3_client.put_object_acl(
           Bucket=AWS_STORAGE_BUCKET_NAME,
           Key=s3_key,
           ACL="public-read"
        )
        return f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{region}.amazonaws.com/{s3_key}"
    except Exception as e:
        print(f"S3 업로드 실패: {e}")
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
    3. 문장은 간결하고 명확하게 작성할 것.
    4. 불필요한 설명(데이터 설명, 일반적인 과정) 제거할 것.
    5. 수치는 유지하되, 내용이 중복되지 않도록 할 것.

    면접 답변:
    {text}

    ==반환 형식==
    총 요약과 핵심 키워드를 JSON 형식으로 반환해라.
    한국어만 사용해라.
    (요약과 키워드를 제외한 그 어떤 문자열도 반환하지 마라.)
    """

    # 요약 생성
    while True:
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
            
            return result

        except json.JSONDecodeError:
            prompt += "\n\n JSON 형식으로 다시 반환해주세요."
            continue
        except Exception as e:
            print(f"Error in summarize_answer: {e}")
            return None

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
    보정된 텍스트를 JSON 형식으로 반환해라.
    한국어만 사용해라.
    (보정된 텍스트를 제외한 그 어떤 문자열도 반환하지 마라.)
    """

    # 보정 생성
    while True:
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
            
            return result

        except json.JSONDecodeError:
            prompt += "\n\n JSON 형식으로 다시 반환해주세요."
            continue
        except Exception as e:
            print(f"Error in correct_transcription: {e}")
            return None
