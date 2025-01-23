import runpod
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