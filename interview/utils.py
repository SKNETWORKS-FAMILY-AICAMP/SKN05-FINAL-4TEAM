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

  # 평가 생성
  while True:
    try:
      response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
          {"role": "user", "content": prompt}
          ],
        temperature=0.7
        )
        
      return json.loads(response.choices[0].message.content)
      
    except json.JSONDecodeError:
        prompt += "\n\n JSON 형식으로 다시 반환해주세요."




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
    :param s3_key: S3 버킷 내 저장될 파일 경로 (예: 'audio/recording.wav')
    :return: S3 URL (업로드된 파일의 URL)
    """
    try:
        s3_client.upload_file(file_path, AWS_STORAGE_BUCKET_NAME, s3_key)
        return f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{region}.amazonaws.com/{s3_key}"
    except Exception as e:
        print(f"S3 업로드 실패: {e}")
        return None
