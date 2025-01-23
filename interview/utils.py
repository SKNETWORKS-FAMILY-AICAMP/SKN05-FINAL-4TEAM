import requests

def call_whisper(audio_file_path):
    """
    Whisper 모델을 호출하여 음성 파일을 텍스트로 변환
    """
    # Runpod Whisper API URL
    url = "https://api.runpod.ai/v2/kyj33jbol8vbm2/run"

    # 파일 업로드
    with open(audio_file_path, "rb") as audio_file:
        payload = {
            "audio": audio_file
            "model": "medium",
            "transcription": "formatted_text",
            "language": "ko"
            }
        response = requests.post(url, json=payload)

    # 응답 처리
    if response.status_code == 200:
        return response.json().get("text")  # 텍스트 결과 반환
    else:
        return f"Error: {response.status_code} - {response.text}"
