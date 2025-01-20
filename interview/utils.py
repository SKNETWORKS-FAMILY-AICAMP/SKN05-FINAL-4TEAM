import requests

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