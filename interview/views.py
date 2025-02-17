from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib import messages
from django.http import JsonResponse
from .forms import ResumeForm
from .models import Resume, Question, JobPosting, Answer, Evaluation
from .utils import audio_to_text, upload_to_s3, audio_analysis,  evaluate_answer, correct_transcription, summarize_answer
from rest_framework.decorators import api_view, authentication_classes, permission_classes
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
    context = {
        'resume': None  # 기본값으로 None 설정
    }
    
    # 가장 최근의 이력서가 있다면 가져옴
    latest_resume = Resume.objects.order_by('-id').first()
    if latest_resume:
        context['resume'] = latest_resume
    
    return render(request, 'main.html', context)


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
def get_interview_report(request, resume_id):
    try:
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')
        questions_data = []

        for question in questions:
            # Answer와 Evaluation을 가져올 때 exists() 체크 추가
            answer = Answer.objects.filter(question=question).first()
            if not answer:
                print(f"Question {question.id}에 대한 답변이 없습니다.")
                continue
                
            evaluation = Evaluation.objects.filter(answer=answer).first()
            if not evaluation:
                print(f"Answer {answer.id}에 대한 평가가 없습니다.")
                continue

            # 데이터가 제대로 들어있는지 디버깅
            print(f"""
            질문 ID: {question.id}
            질문 내용: {question.text}
            답변 내용: {answer.transcribed_text if answer else 'No answer'}
            평가 점수: {evaluation.total_score if evaluation else 'No evaluation'}
            """)

            evaluation_data = {
                'scores': evaluation.scores,
                'total_score': evaluation.total_score,
                'improvements': evaluation.improvements,
                'nonverbal_improvements': evaluation.nonverbal_improvements
            }

            question_data = {
                'question_text': question.text,
                'answer': {
                    'transcribed_text': answer.transcribed_text,
                    'audio_url': answer.audio_url
                },
                'evaluation': evaluation_data
            }
            questions_data.append(question_data)

        # 최종 데이터 확인
        print("Report Data:", json.dumps(questions_data, indent=2, ensure_ascii=False))

        return Response({
            'status': 'success',
            'data': {
                'questions': questions_data
            }
        })

    except Exception as e:
        print(f"Error in get_interview_report: {e}")
        import traceback
        traceback.print_exc()  # 상세한 에러 트레이스 출력
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)
    

# 답변 평가
@api_view(['POST'])
def evaluate_answer_view(request):
    try:
        print("Request data:", request.data)
        question_id = request.data.get('question_id')
        answer_id = request.data.get('answer_id')
        
        # Question과 JobPosting 정보 함께 가져오기
        question = Question.objects.get(id=question_id)
        print(f"Found question: {question.text}")
        
        # JobPosting 정보 가져오기 및 디버깅
        job_posting = question.job_posting
        if job_posting is None:
            # 해당 question의 resume_id로 Resume를 찾고, 거기서 job_posting 정보를 가져옴
            resume = Resume.objects.filter(id=question.resume_id).first()
            if resume and resume.job_posting:
                job_posting = resume.job_posting
                print(f"Found job posting from resume: {job_posting.company_name}")
            else:
                raise ValueError("No job posting information found")
        
        print(f"Job Posting Details:")
        print(f"Company: {job_posting.company_name}")
        print(f"Title: {job_posting.job_title}")
        
        answer = Answer.objects.get(id=answer_id)
        print(f"Found answer: {answer.transcribed_text[:100]}")
        
        # 평가 수행
        evaluation_result = evaluate_answer(
            question.text,
            answer.transcribed_text,
            job_posting.responsibilities,
            job_posting.qualifications
        )
        print("Evaluation result:", evaluation_result)
        
        # 점수 계산
        scores = {
            'question_understanding': evaluation_result["질문 이해도"]["점수"],
            'logical_flow': evaluation_result["논리적 전개"]["점수"],
            'content_specificity': evaluation_result["내용의 구체성"]["점수"],
            'problem_solving': evaluation_result["문제 해결 접근 방식"]["점수"],
            'organizational_fit': evaluation_result["핵심 기술 및 직무 수행 능력 평가"]["점수"]
        }
        
        # 총점 계산 (각 항목 10점 만점, 총 50점)
        total_score = sum(scores.values())
        
        # 개선사항 리스트 생성 - 키 이름 주의
        improvements = [
            evaluation_result["질문 이해도"].get("개선사항", ""),  
            evaluation_result["논리적 전개"].get("개선사항", ""),
            evaluation_result["내용의 구체성"].get("개선사항", ""),
            evaluation_result["문제 해결 접근 방식"].get("개선사항", ""),
            evaluation_result["핵심 기술 및 직무 수행 능력 평가"].get("개선사항", "")
        ]
        
        # 빈 문자열 제거
        improvements = [imp for imp in improvements if imp]
        
        print("Scores:", scores)
        print("Improvements:", improvements)
        
        # 평가 결과 저장
        evaluation = Evaluation.objects.create(
            answer=answer,
            total_score=total_score,
            scores=scores,
            improvements=improvements,
            nonverbal_scores={},
            nonverbal_improvements=[]
        )
        
        return Response({
            'status': 'success',
            'message': '평가가 완료되었습니다.',
            'evaluation_id': evaluation.id,
            'job_info': {
                'company_name': job_posting.company_name,
                'job_title': job_posting.job_title,
                'responsibilities': job_posting.responsibilities,
                'qualifications': job_posting.qualifications
            },
            'evaluation_result': {
                'total_score': total_score,
                'scores': scores,
                'improvements': improvements
            }
        })
        
    except Exception as e:
        print(f"Error in evaluate_answer_view: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


# 결과 리포트 페이지 
def interview_report(request, resume_id):
    """
    면접 리포트 페이지를 렌더링하고 자동으로 평가 프로세스를 시작합니다.
    """
    try:
        # 기본 정보 가져오기
        resume = get_object_or_404(Resume, id=resume_id)
        
        # 평가 프로세스 시작
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')  # resume_id로 질문 조회
        evaluation_results = []

        for question in questions:
            answer = Answer.objects.filter(question=question).first()
            if not answer or Evaluation.objects.filter(answer=answer).exists():
                continue

            evaluation = create_evaluation(answer)
            if evaluation:
                evaluation_results.append({
                    'question_id': question.id,
                    'evaluation_id': evaluation.id,
                    'total_score': evaluation.total_score
                })

        if evaluation_results:
            print("평가 프로세스 완료:", evaluation_results)
        
        context = {
            'candidate_name': resume.name,
            'resume_id': resume_id,  
        }
        
        return render(request, 'report.html', context)
        
    except Exception as e:
        print(f"Error in interview_report: {e}")
        messages.error(request, "리포트 생성 중 오류가 발생했습니다.")
        return render(request, 'report.html', {'error': str(e)})


# 이력서 텍스트 변환
def get_resume_text(resume_id):
    """이력서 텍스트 데이터 가져오기"""
    try:
        resume = Resume.objects.get(id=resume_id)
        
        resume_text = f"""
        프로젝트 경험:
        {resume.project_experience}

        문제 해결 경험:
        {resume.problem_solving}

        팀워크 경험:
        {resume.teamwork_experience}

        자기계발:
        {resume.self_development}
        """
        
        return resume_text.strip()
        
    except Resume.DoesNotExist:
        print(f"Resume not found for ID: {resume_id}")
        return None
    except Exception as e:
        print(f"Error in get_resume_text: {e}")
        return None


# 생성 질문 파싱
def parse_questions(questions_json):
    """질문 JSON을 파싱하여 포맷팅된 질문 리스트 반환"""
    try:
        formatted_questions = []
        questions_list = questions_json.get('questions', [])
        
        for question_group in questions_list:
            question_type = question_group.get('question_type', '')
            questions = question_group.get('question_content', [])
            
            for question in questions:
                formatted_questions.append({
                    'text': question,
                    'category': question_type
                })
        
        if not formatted_questions:
            print("Raw questions JSON:", questions_json)
            return None, "Failed to format questions"
            
        print(f"Successfully formatted {len(formatted_questions)} questions")
        return formatted_questions, None
        
    except Exception as e:
        print(f"Error parsing questions: {e}")
        print("Raw questions JSON:", questions_json)
        return None, str(e)

    
# 질문 생성
def generate_questions_from_resume(resume_id, jobposting_id):
    """특정 사용자의 이력서와 채용 공고 정보를 기반으로 질문 생성 및 저장"""
    try:
        with transaction.atomic():
            resume = Resume.objects.get(id=resume_id)
            job_posting = JobPosting.objects.get(id=jobposting_id)
            
            # 기존 질문들 삭제
            Question.objects.filter(resume=resume).delete()
            print(f"Deleted existing questions for resume {resume_id}")
            
            resume_text = f"""
            프로젝트 경험:
            {resume.project_experience}

            문제 해결 경험:
            {resume.problem_solving}

            팀워크 경험:
            {resume.teamwork_experience}

            자기계발:
            {resume.self_development}
            """

            evaluation_metrics = [
                "질문 이해도", "논리적 전개", "내용의 구체성", 
                "문제 해결 접근 방식", "핵심 기술 및 직무 수행 능력 평가"
            ]
            
            questions_json = generate_q(
                resume_text.strip(), 
                job_posting.responsibilities,
                job_posting.qualifications,
                evaluation_metrics
            )
            
            print("Generated questions JSON:", questions_json)
            
            if not questions_json:
                return None, "Failed to generate questions"
                
            formatted_questions, error = parse_questions(questions_json)
            if not formatted_questions:
                return None, error or "Failed to parse questions"

            print(f"Saving {len(formatted_questions)} questions to database")
            
            # 새 질문 저장
            for i, q in enumerate(formatted_questions, 1):
                Question.objects.create(
                    resume=resume,
                    text=q['text'],
                    category=q['category'],
                    order=i,
                    job_posting=job_posting
                )

            print(f"Successfully saved all questions for resume {resume_id}")
            return formatted_questions, None
            
    except Exception as e:
        print(f"Error in generate_questions_from_resume: {e}")
        return None, str(e)
    


# 질문 생성 API
@api_view(['POST'])
def generate_questions(request):
    """질문 생성하는 API 엔드 포인트"""
    try:
        resume_id = request.data.get('resume_id')
        job_id = request.data.get('jobposting_id')
        
        if not resume_id or not job_id:
            return Response({
                "status": "error",
                "message": "Resume ID and JobPosting ID are required"
            }, status=400)

        questions, error = generate_questions_from_resume(resume_id, job_id)
        
        if error:
            return Response({
                "status": "error",
                "message": error
            }, status=500)
            
        return Response({
            "status": "success",
            "message": "Questions generated successfully",
            "questions": questions
        })

    except Exception as e:
        print(f"Error in generate_questions: {e}")
        return Response({
            "status": "error",
            "message": str(e)
        }, status=500)


# 실전 면접 페이지
def interview_page(request, resume_id):
    """면접 페이지"""
    try:
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')
        
        if not questions.exists():
            return redirect('main_page')
        
        # 첫 번째 질문 가져오기
        first_question = questions.first()
            
        context = {
            'questions': questions,
            'resume_id': resume_id,
            'total_questions': questions.count(),
            'question': first_question.text,  # 첫 질문 텍스트
            'question_id': first_question.id  # 첫 질문 ID
        }
        return render(request, 'interview.html', context)
        
    except Exception as e:
        print(f"Error in interview_page: {e}")
        return redirect('main_page')


# 다음 질문 API
def next_question(request, resume_id):  
    """
    녹음 종료 후 다음 질문을 가져오는 API
    """
    if request.method == "POST":
        current_question_id = request.POST.get('question_id')

        # 현재 질문을 사용된 상태로 업데이트
        if current_question_id:
            try:
                current_question = Question.objects.get(id=current_question_id, resume_id=resume_id)
                current_question.is_used = True
                current_question.save()
            except Question.DoesNotExist:
                return JsonResponse({'error': '유효하지 않은 질문 ID 입니다.'}, status=400)
            
        # 다음 질문 가져오기
        next_question = Question.objects.filter(
            resume_id=resume_id, 
            is_used=False
        ).order_by('order').first()

        if not next_question:
            return JsonResponse({
                'status': 'complete',
                'message': '모든 질문이 완료되었습니다.'
            }, status=200)

        return JsonResponse({
            'status': 'success',
            'question': next_question.text,
            'question_id': next_question.id
        }, status=200)

    return JsonResponse({'error': '잘못된 요청 방식입니다.'}, status=400)


# 이력서 존재 확인하는 API
@api_view(['GET'])
def check_resume(request):
    """사용자의 이력서가 존재하는지 확인하는 API"""
    try:
        resume_id = request.GET.get('resume_id')  # 기존 호환성 유지

        if not resume_id:
            return Response({
                "status": "error",
                "message": "Resume ID is required",
                "resume_exists": False
            }, status=400)
        
        try:
            resume_id = int(resume_id)
        except ValueError:
            return Response({
                "status": "error",
                "message": "Invalid Resume ID format",
                "resume_exists": False
            }, status=400)
        
        resume_exists = Resume.objects.filter(id=resume_id).exists()
        
        return Response({
            "status": "success",
            "message": "Resume check completed",
            "resume_exists": resume_exists
        }, status=200)

    except Exception as e:
        print(f"Error in check_resume: {e}")
        return Response({
            "status": "error",
            "message": str(e),
            "resume_exists": False
        }, status=500)



# 면접 질문 존재 확인하는 API
@api_view(["GET"])
def check_questions(request):
    """
    사용자의 면접 질문이 존재하는지 확인하는 API
    """
    resume_id = request.GET.get('resume_id')  

    if not resume_id:
        return Response({"error": "resume_id가 필요합니다."}, status=400)

    try:
        resume_id = int(resume_id)
    except ValueError:
        return Response({"error": "resume_id는 정수여야 합니다."}, status=400)

    questions = Question.objects.filter(resume_id=resume_id).order_by('order')

    if questions.exists():
        question_list = [{"id": q.id, "text": q.text, "order": q.order} for q in questions]
        return Response({
            "status": "ready",
            "questions": question_list
        }, status=200)
    
    return Response({
        "status": "not_ready",
        "questions": []
    }, status=200)


# 답변 평가 생성, 저장
def create_evaluation(answer):
    """답변에 대한 평가를 생성하고 저장하는 함수"""
    try:
        # 관련 데이터 가져오기
        question = answer.question
        job_posting = question.job_posting
        
        # 내용 평가 실행
        evaluation_result = evaluate_answer(
            question_text=question.text,
            answer_text=answer.transcribed_text,
            responsibilities=job_posting.responsibilities,
            qualifications=job_posting.qualifications
        )

        # 비언어적 평가 실행 (audio_url이 있는 경우에만)
        nonverbal_scores = {}
        nonverbal_improvements = []
        if answer.audio_url:
            try:
                nonverbal_result, pronunciation_score, spm, stutter_count, stutter_types, _ = audio_analysis(answer.audio_url)
                
                # 비언어적 점수 데이터 구성
                nonverbal_scores = {
                    'pronunciation': nonverbal_result['발음']['점수'],
                    'speaking_speed': nonverbal_result['빠르기']['점수'],
                    'stuttering': nonverbal_result['말더듬']['점수']
                }

                # 비언어적 개선사항 리스트 구성
                nonverbal_improvements = [
                    nonverbal_result['발음'].get('개선사항', ''),
                    nonverbal_result['빠르기'].get('개선사항', ''),
                    nonverbal_result['말더듬'].get('개선사항', '')
                ]
                nonverbal_improvements = [imp for imp in nonverbal_improvements if imp]
                
            except Exception as e:
                print(f"Error in audio analysis: {e}")

        if evaluation_result:
            # 내용 점수 데이터 구성
            scores = {
                'question_understanding': evaluation_result['질문 이해도']['점수'],
                'logical_flow': evaluation_result['논리적 전개']['점수'],
                'content_specificity': evaluation_result['내용의 구체성']['점수'],
                'problem_solving': evaluation_result['문제 해결 접근 방식']['점수'],
                'organizational_fit': evaluation_result['핵심 기술 및 직무 수행 능력 평가']['점수']
            }

            # 내용 개선사항 리스트 구성
            improvements = [
                evaluation_result['질문 이해도'].get('개선사항', ''),
                evaluation_result['논리적 전개'].get('개선사항', ''),
                evaluation_result['내용의 구체성'].get('개선사항', ''),
                evaluation_result['문제 해결 접근 방식'].get('개선사항', ''),
                evaluation_result['핵심 기술 및 직무 수행 능력 평가'].get('개선사항', '')
            ]
            improvements = [imp for imp in improvements if imp]

            # 총점 계산 (내용 평가 총점)
            total_score = sum(scores.values())

            # Evaluation 객체 생성 또는 업데이트
            evaluation, created = Evaluation.objects.update_or_create(
                answer=answer,
                defaults={
                    'total_score': total_score,
                    'scores': scores,
                    'nonverbal_scores': nonverbal_scores,
                    'improvements': improvements,
                    'nonverbal_improvements': nonverbal_improvements
                }
            )

            return evaluation

    except Exception as e:
        print(f"Error creating evaluation: {e}")
        return None



@api_view(['POST'])
def process_interview_evaluation(request, resume_id):
    """면접이 완료된 후 모든 답변을 평가하고 리포트 생성을 준비하는 API"""
    try:
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')  # resume_id로 질문 조회
        evaluation_results = []

        for question in questions:
            answer = Answer.objects.filter(question=question).first()
            if not answer or Evaluation.objects.filter(answer=answer).exists():
                continue

            evaluation = create_evaluation(answer)
            if evaluation:
                evaluation_results.append({
                    'question_id': question.id,
                    'evaluation_id': evaluation.id,
                    'total_score': evaluation.total_score
                })

        # 리포트 데이터 준비
        report_data = get_interview_report(request, resume_id).data

        return Response({
            'status': 'success',
            'message': '모든 답변 평가가 완료되었습니다.',
            'evaluations': evaluation_results,
            'report_data': report_data,
            'redirect_url': f'/interview/report/{resume_id}/'
        })

    except Exception as e:
        print(f"Error in process_interview_evaluation: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=500)


def upload_chunk(request):
    """ 청크 단위로 오디오 데이터를 서버에 저장하는 뷰 """

    try:        
        chunk = request.FILES.get("chunk")
        question_id = request.POST.get("questionId")

        os.makedirs("chunk_data/", exist_ok=True)
        chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")

        with open(chunk_file_path, "ab") as f:
            f.write(chunk.read())

        return JsonResponse({"status": "success", "message": "청크 저장 완료"})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def finalize_audio(request):
    """ 저장된 파일을 S3에 업로드하고 로컬에서 삭제하는 뷰 """
    
    try:
        question_id = request.POST.get("questionId")
        resume_id = request.POST.get("resumeId")
        chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")
        s3_filename = f"{resume_id}_{question_id}.wav"
        s3_url = upload_to_s3(chunk_file_path, s3_filename)

        os.remove(chunk_file_path)
        return JsonResponse({"s3_url": s3_url})
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    
def transcribe_audio(request):
    '''whisper를 호출해 음성을 텍스트화 하는 뷰'''
    try:
        data = json.loads(request.body.decode("utf-8"))
        s3_urls = data.get("s3_urls")
        transcribed_texts = []

        for s3_url in s3_urls:
            result = audio_to_text(s3_url)
            transcribed_texts.append(result["transcription"])

        return JsonResponse({"transcriptions": transcribed_texts})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def save_answers(request):
    """변환된 텍스트를 Answer 모델에 저장하는 뷰"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        s3_urls = data.get("s3Urls")
        transcriptions = data.get("transcriptions")
        resume_id = data.get("resumeId")
        questions = Question.objects.filter(resume_id=resume_id).order_by("id")

        with transaction.atomic():
            for i in range(10):
                s3_url = s3_urls[i]
                transcribed_text = transcriptions[i]
                question = questions[i]

                Answer.objects.create(
                    resume_id=resume_id,
                    question=question,
                    audio_url=s3_url,
                    transcribed_text=transcribed_text
                )
        
        return JsonResponse({"status": "success", "message": "답변 저장 완료"})
    
    except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)