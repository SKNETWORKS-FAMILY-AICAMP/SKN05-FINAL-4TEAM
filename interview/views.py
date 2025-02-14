from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib import messages
from django.http import JsonResponse
from .forms import ResumeForm
from .models import Resume, Question, JobPosting, Answer, Evaluation
# import utils
from .utils import audio_to_text, upload_to_s3
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import generate_q
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json


# 메인 페이지
def main_page(request):
    """
    메인 페이지를 렌더링합니다.
    """
    return render(request, 'main.html')


# 이력서 작성 페이지
def resume_form(request):
    """
    이력서 작성 폼
    """
    if request.method == 'POST':
        form = ResumeForm(request.POST)
        if form.is_valid():
            # 1. 이력서 저장
            resume = form.save()

            # 성공 메시지 표시
            messages.success(request, "이력서 제출 및 질문 생성이 완료되었습니다! 메인 페이지에서 공고를 선택하세요")
            return redirect('main_page')
        else:
            messages.error(request,"폼 유효성 검사에 실패했습니다. 입력값을 확인해주세요.")

    else:
        form = ResumeForm()

    return render(request, 'resume_form.html', {'form': form})


# 리포트 생성을 위한 데이터 가져오기 API
@api_view(['GET'])
def get_interview_report(request, user_id):
    try:
        print(f"Requesting interview report for user_id: {user_id}")
        
        # 질문 데이터 가져오기
        questions = Question.objects.filter(user_id=user_id)
        
        print(f"Found {questions.count()} questions")
        
        interview_data = []
        for question in questions:
            # 해당 질문에 대한 답변 가져오기
            answer = Answer.objects.filter(question_id=question.id).first()
            
            question_data = {
                'question': {
                    'id': question.id,
                    'text': question.text,
                    'order': getattr(question, 'order', 0)
                },
                'answer': {
                    'transcribed_text': answer.transcribed_text if answer else '답변 데이터가 아직 없습니다.'
                }
            }
            interview_data.append(question_data)
        
        print(f"Returning {len(interview_data)} items")
        
        return Response({
            'status': 'success',
            'data': interview_data
        })
        
    except Exception as e:
        print(f"Error in get_interview_report: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


# 결과 리포트 페이지 
def interview_report(request, user_id):
    """
    면접 리포트 페이지를 렌더링 합니다.
    """
    resume = get_object_or_404(Resume, id=user_id)

    questions = Question.objects.filter(user_id=user_id).order_by('order')

    context = {
        'candidate_name': resume.name,
        'user_id': user_id,
    }
    return render(request, 'report.html', context)


# 이력서 텍스트 변환
def get_resume_text(user_id):
    """
    데이터베이스에서 특정 사용자의 이력서 데이터를 가져와 텍스트로 변환합니다.
    """
    try:
        resume = Resume.objects.get(id=user_id)
        resume_text = f"""
        이름 : {resume.name}
        전화번호: {resume.phone}
        이메일: {resume.email}

        주요 프로젝트 경험:
        {resume.project_experience}

        문제 해결 사례:
        {resume.problem_solving}

        팀워크 경험:
        {resume.teamwork_experience}

        자기 개발 노력:
        {resume.self_development}
        """
        return resume_text
    except Resume.DoesNotExist:
        return None


# 생성 질문 파싱
def parse_questions(questions_raw):
    formatted_questions = []
    if isinstance(questions_raw, list):
        for item in questions_raw:
            if isinstance(item, dict) and "유형" in item and "내용" in item:
                content = item["내용"]
                if isinstance(content, list):
                    for question_text in content:
                        formatted_questions.append({
                            "category": item["유형"],
                            "text": str(question_text).strip()
                        })
                else:
                    formatted_questions.append({
                        "category": item["유형"],
                        "text": str(content).strip()
                    })
            else:
                print(f"잘못된 질문 형식: {item}")

    elif isinstance(questions_raw, dict):
        for category, questions in questions_raw.items():
            if isinstance(questions, list):
                for question_text in questions:
                    if isinstance(question_text, list):
                        # 중첩 리스트가 있을 경우 각 항목 별도 저장
                        for sub_question in question_text:
                            formatted_questions.append({
                                "category": category,
                                "text": str(sub_question).strip()
                            })
                    else:
                        formatted_questions.append({
                            "category": category,
                            "text": str(question_text).strip()
                        })
            else:
                print(f"잘못된 질문 형식 for category '{category}': {questions}")
    else:
        return None, f"질문 데이터 형식이 올바르지 않습니다. (type: {type(questions_raw)})"
    return formatted_questions, None


# 질문 저장
def save_questions(user_id, formatted_questions):
    try:
        with transaction.atomic():
            for idx, question in enumerate(formatted_questions):
                Question.objects.create(
                    user_id=user_id,
                    text=question["text"],
                    category=question["category"],
                    order=idx + 1
                )
    except Exception as e:
        return None, f"질문 저장 실패: {str(e)}"
    

# 질문 생성
def generate_questions_from_resume(user_id, jobposting_id):
    """
    특정 사용자의 이력서와 채용 공고 정보를 기반으로 질문 생성 및 저장
    """
    # 1. 이력서 데이터 가져오기
    resume_text = get_resume_text(user_id)
    if not resume_text:
        return None

    # 2. 사용자가 선택한 채용 공고 데이터 가져오기
    job_posting = JobPosting.objects.get(id=jobposting_id)
    if not job_posting:
        return None
    
    responsibilities = job_posting.responsibilities
    qualifications = job_posting.qualifications
    
    # 3. 평가 기준 설정
    evaluation_metrics = [
        "질문 이해도", "논리적 전개", "내용의 구체성", 
        "문제 해결 접근 방식", "핵심 기술 및 직무 수행 능력 평가"
        ]
    
    # 4. 질문 생성
    questions_json = generate_q(resume_text, responsibilities, qualifications, evaluation_metrics)
    questions_raw = questions_json["질문"]

    # JSON 응답 확인 및 질문 추출
    print("GPT 질문 응답 (JSON):", questions_json)
    
    # 5. 질문 파싱
    formatted_questions, _ = parse_questions(questions_raw)
    if not formatted_questions:
        return None

    # 6. 질문 저장
    save_questions(user_id, formatted_questions)

    return formatted_questions, None
    
    
# 질문 생성 API
@api_view(['POST'])
def generate_questions(request):
    """
    질문 생성하는 API 엔드 포인트
    """
    print("요청 데이터:", request.data) 
    
    user_id = request.data.get('user_id')
    jobposting_id = request.data.get('jobposting_id')
    
    if not user_id or not jobposting_id:
        return Response(status=400)
    
    try:
        user_id = int(user_id) 
        jobposting_id = int(jobposting_id)
    except ValueError:
        return Response(status=400)
    
    print(f"user_id: {user_id} / jobposting_id:{jobposting_id}")

    # 질문 생성 로직 실행
    questions= generate_questions_from_resume(user_id, jobposting_id)
    if not questions:
        return Response(status=204)  # No Content

    return Response({"questions": questions}, status=200)


# 실전 면접 페이지
def interview_page(request, user_id):
    """
    실전 면접 페이지를 렌더링합니다.
    """
    # report활용 위해 user_id의 이력서 정보 가져오기
    resume = get_object_or_404(Resume, id=user_id)

    # 질문 가져오기
    question = Question.objects.filter(user_id=user_id, is_used=False).order_by('order').first()
    
    if not question:
        return render(request, 'interview.html', {'error': '사용 가능한 질문이 없습니다.'})

    total_questions = Question.objects.filter(user_id=user_id).count()

    return render(request, 'interview.html', {
        'question': question.text, 
        'question_id': question.id,
        'user_id': user_id,
        'total_questions': total_questions,
        'user_name': resume.name, # 리포트에 쓰이기 위해 지원자의 이름도 추가 반환
    })


# 다음 질문 API
def next_question(request, user_id):
    """
    녹음 종료 후 다음 질문을 가져오는 API
    """
    if request.method == "POST":
        current_question_id = request.POST.get('question_id')

        # 현재 질문을 사용된 상태로 업데이트
        if current_question_id:
            try:
                current_question = Question.objects.get(id=current_question_id, user_id=user_id)
                current_question.is_used = True
                current_question.save()
            except Question.DoesNotExist:
                return JsonResponse({'error': '유효하지 않은 질문 ID 입니다.'}, status = 400)
            
    # 다음 질문 가져오기
        next_question = Question.objects.filter(user_id=user_id, is_used=False).order_by('order').first()
        if not next_question:
            return JsonResponse({'error': '모든 질문이 완료되었습니다.'}, status=200)

        return JsonResponse({'question': next_question.text, 'question_id': next_question.id}, status=200)

    return JsonResponse({'error': '잘못된 요청 방식입니다.'}, status=400)


# 이력서 존재 확인하는 API
@api_view(['GET'])
def check_resume(request):
    """
    사용자의 이력서가 존재하는지 확인하는 API
    """
    user_id = request.GET.get('user_id')

    if not user_id:
        return Response({"error": "user_id가 필요합니다."}, status=400)
    
    try:
        user_id = int(user_id)
    except ValueError:
        return Response({"error": "user_id는 정수여야 합니다."}, status=400)
    
    resume_exists = Resume.objects.filter(id=user_id).exists()
    return Response({"resume_exists": resume_exists}, status=200)


# 면접 질문 존재 확인하는 API
@api_view(["GET"])
def check_questions(request):
    """
    사용자의 면접 질문이 존재하는지 확인하는 API
    """
    user_id = request.GET.get('user_id')  # GET 요청에서 user_id 받음

    if not user_id:
        return Response({"error": "user_id가 필요합니다."}, status=400)

    try:
        user_id = int(user_id)
    except ValueError:
        return Response({"error": "user_id는 정수여야 합니다."}, status=400)

    questions = Question.objects.filter(user_id=user_id).order_by('order')

    if questions.exists():
        question_list = [{"id": q.id, "text": q.text, "order": q.order} for q in questions]
    else:
        question_list = []

    return Response({"questions": question_list}, status=200)


# 답변 평가 생성, 저장
# def create_evaluation(answer):
#     """답변에 대한 평가를 생성하고 저장하는 함수"""
#     try:
#         # 관련 데이터 가져오기
#         question = answer.question
#         job_posting = question.job_posting  # JobPosting과의 관계 필요

#         # 평가 실행
#         evaluation_result = evaluate_answer(
#             question_text=question.text,
#             answer_text=answer.transcribed_text,
#             responsibilities=job_posting.responsibilities,
#             qualifications=job_posting.qualifications
#         )

#         if evaluation_result:
#             # 점수 데이터 구성
#             scores = {
#                 'question_understanding': evaluation_result['질문 이해도']['점수'],
#                 'logical_flow': evaluation_result['논리적 전개']['점수'],
#                 'content_specificity': evaluation_result['내용의 구체성']['점수'],
#                 'problem_solving': evaluation_result['문제 해결 접근 방식']['점수'],
#                 'organizational_fit': evaluation_result['핵심 기술 및 직무 수행 능력 평가']['점수']
#             }

#             # 개선사항 리스트 구성
#             improvements = [
#                 evaluation_result['질문 이해도']['개선 사항'],
#                 evaluation_result['논리적 전개']['개선 사항'],
#                 evaluation_result['내용의 구체성']['개선 사항'],
#                 evaluation_result['문제 해결 접근 방식']['개선 사항'],
#                 evaluation_result['핵심 기술 및 직무 수행 능력 평가']['개선 사항']
#             ]

#             # 총점 계산
#             total_score = evaluation_result.get('총점', sum(scores.values()))

#             # Evaluation 객체 생성 또는 업데이트
#             evaluation, created = Evaluation.objects.update_or_create(
#                 answer=answer,
#                 defaults={
#                     'total_score': total_score,
#                     'scores': scores,
#                     'improvements': improvements
#                 }
#             )

#             return evaluation

#     except Exception as e:
#         print(f"Error creating evaluation: {e}")
#         return None


@csrf_exempt
def upload_chunk(request):
    """ 청크 단위로 오디오 데이터를 서버에 저장하는 뷰 """
    # chunk = request.FILES["chunk"]
    # question_id = request.POST.get("questionId") # 질문 ID를 사용하여 파일 구분

    # # 로컬 chunk 파일 경로 설정 및 저장
    # os.makedirs("chunk_data/", exist_ok=True)
    # chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")

    # # 청크 데이터를 추가 모드("ab")로 저장
    # with open(chunk_file_path, "ab") as f:
    #     f.write(chunk.read())
    try: # ✅ POST 요청이 아닌 경우 405 오류 반환
        if request.method != "POST":
            return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

        # ✅ 파일(chuck)이 요청에 포함되어 있는지 확인
        chunk = request.FILES.get("chunk")
        if not chunk:
            return JsonResponse({"error": "파일(chuck)이 요청에 포함되지 않았습니다."}, status=400)

        # ✅ questionId가 없는 경우 오류 반환
        question_id = request.POST.get("questionId")
        if not question_id:
            return JsonResponse({"error": "questionId가 없습니다."}, status=400)

        # ✅ 파일 저장 경로 설정 및 디렉터리 생성
        os.makedirs("chunk_data/", exist_ok=True)
        chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")

        # ✅ 청크 데이터를 추가 모드("ab")로 저장
        with open(chunk_file_path, "ab") as f:
            f.write(chunk.read())

        # ✅ 정상적으로 저장되었음을 반환
        return JsonResponse({"status": "success", "message": "청크 저장 완료"})

    except Exception as e:
        # ✅ 오류 발생 시 500 응답 반환
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def finalize_audio(request):
    """ 저장된 청크 파일을 S3에 업로드하고 로컬에서 삭제하는 뷰 """
    if request.method == "POST":
        try:
            # ✅ FormData에서 데이터 가져오기
            question_id = request.POST.get("questionId")
            user_id = request.POST.get("userId")

            if not question_id or not user_id:
                return JsonResponse({"error": "questionId 또는 userId가 누락되었습니다."}, status=400)

            chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")

            # ✅ S3 업로드
            s3_filename = f"{user_id}_{question_id}.wav"
            s3_url = upload_to_s3(chunk_file_path, s3_filename)

            if not s3_url:
                return JsonResponse({"error": "S3 업로드 실패"}, status=500)

            # ✅ 로컬 파일 삭제
            try:
                os.remove(chunk_file_path)
            except Exception as e:
                print(f"⚠ 로컬 파일 삭제 실패: {e}")

            return JsonResponse({"s3_url": s3_url})

        except Exception as e:
            print(f"❌ finalize_audio 오류: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "POST 요청만 허용됩니다."}, status=405)

@csrf_exempt
def transcribe_audio(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            s3_urls = data.get("s3_urls")

            transcribed_texts = []

            for s3_url in s3_urls:
                result = audio_to_text(s3_url)
                transcribed_texts.append(result["transcription"])

            return JsonResponse({
                "transcriptions": transcribed_texts
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def save_answers(request):
    """
    변환된 텍스트를 Answer 모델에 저장하는 API
    """
    if request.method == "POST":
        try:
            # ✅ 요청 데이터 확인
            print("📌 요청 데이터:", request.body.decode("utf-8"))

            data = json.loads(request.body.decode("utf-8"))
            user_id = data.get("userId")
            s3_urls = data.get("s3Urls")
            transactions = data.get("transcriptions")

            # ✅ 질문 데이터 가져오기 (`filter()` 사용)
            questions = Question.objects.filter(user_id=user_id).order_by("id")
            print(f"📌 user_id={user_id}의 질문 개수: {len(questions)}개")

            # ✅ 데이터 개수가 맞는지 확인
            if len(questions) != len(s3_urls):
                return JsonResponse({"error": "질문의 개수와 답변 개수가 일치하지 않습니다."}, status=400)

            # ✅ 트랜잭션을 사용하여 Answer 저장
            print("OK!!!!!!")
            with transaction.atomic():
                for i in range(10):
                    s3_url = s3_urls[i]
                    transcribed_text = transactions[i]
                    question = questions[i]

                    print(f"✅ 저장 중: {user_id}, 질문: {question.text}, URL: {s3_url}")

                    Answer.objects.create(
                        user_id=user_id,
                        question=question,
                        audio_url=s3_url,
                        transcribed_text=transcribed_text
                    )

            print("✅ 답변 저장 완료")
            return JsonResponse({"message": "✅ 답변 저장 완료!"}, status=200)

        except Exception as e:
            print(f"❌ 서버 오류 발생: {e}")  # ✅ 오류 로그 출력
            return JsonResponse({"error": str(e)}, status=500)


