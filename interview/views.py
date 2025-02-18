import os
import json
from .forms import ResumeForm
from .models import JobPosting, Resume, Question, Answer, Evaluation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from . import utils
from .utils import generate_q, audio_to_text, upload_to_s3, audio_analysis,  evaluate_answer, correct_transcription, summarize_answer
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view



def main_page(request):
    """메인 페이지를 렌더링"""

    context = {
        'resume': None  # 기본값
    }
    
    latest_resume = Resume.objects.order_by('-id').first()  # 가장 최근의 이력서
    if latest_resume:
        context['resume'] = latest_resume
    
    return render(request, 'main.html', context)


def resume_form(request):
    """이력서 작성 폼"""

    if request.method == 'POST':
        form = ResumeForm(request.POST)
        if form.is_valid():
            resume = form.save()
            messages.success(request, "이력서 제출이 완료되었습니다! 메인 페이지에서 공고를 선택하세요")

            return redirect('main_page')       

        else:
            messages.error(request,"폼 유효성 검사에 실패했습니다. 입력값을 확인해주세요.")

    else:
        form = ResumeForm()

    return render(request, 'resume_form.html', {'form': form})


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
        return None
    
    except Exception as e:
        print(f"Error in get_resume_text: {e}")
        return None


def parse_questions(questions_json):
    """JSON형식의 질문을 파싱하여 포맷팅된 질문 리스트 반환"""

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
            
        return formatted_questions, None
        
    except Exception as e:
        return None, str(e)


def generate_questions(resume_id, jobposting_id):
    """사용자의 이력서와 채용 공고 정보를 기반으로 질문 생성 및 저장"""

    try:
        with transaction.atomic():
            resume = Resume.objects.get(id=resume_id)
            job_posting = JobPosting.objects.get(id=jobposting_id)
            
            Question.objects.filter(resume=resume).delete()  # 기존 질문 삭제
            
            resume_text = get_resume_text(resume_id)

            evaluation_metrics = [
                "질문 이해도", "논리적 전개", "내용의 구체성", 
                "문제 해결 접근 방식", "핵심 기술 및 직무 수행 능력 평가"
            ]
            
            questions_json = generate_q(
                resume_text, 
                job_posting.responsibilities,
                job_posting.qualifications,
                evaluation_metrics
            )
            
            if not questions_json:
                return None, "Failed to generate questions"
                
            formatted_questions, error = parse_questions(questions_json)

            if not formatted_questions:
                return None, error or "Failed to parse questions"
       
            # 새 질문 데이터 저장
            for i, q in enumerate(formatted_questions, 1): 
                Question.objects.create(
                    resume=resume,
                    text=q['text'],
                    category=q['category'],
                    order=i,
                    job_posting=job_posting
                )
                
            return formatted_questions, None
            
    except Exception as e:
        return None, str(e)


@api_view(['POST'])
def call_generate_questions(request):
    """질문 생성을 요청하는 뷰"""

    try:
        resume_id = request.data.get('resume_id')
        job_id = request.data.get('jobposting_id')
        
        if not resume_id or not job_id:
            return Response({
                "status": "error",
                "message": "Resume ID and JobPosting ID are required"
            }, status=400)

        questions, error = generate_questions(resume_id, job_id)
        
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
        return Response({
            "status": "error",
            "message": str(e)
        }, status=500)


def interview_page(request, resume_id):
    """면접 페이지를 렌더링"""

    try:
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')
        first_question = questions.first()
            
        context = {
            'questions': questions,
            'resume_id': resume_id,
            'total_questions': questions.count(),
            'question': first_question.text,
            'question_id': first_question.id
        }

        return render(request, 'interview.html', context)
        
    except Exception as e:
        return redirect('main_page')


@api_view(['GET'])
def check_resume(request):
    """사용자의 이력서가 존재하는지 확인하는 뷰"""

    resume_id = request.GET.get('resume_id')

    if not resume_id:
        return Response({
            "status": "error",
            "message": "Resume ID is required",
            "resume_exists": False
            }, status=400)
        
    resume_id = int(resume_id)
    resume_exists = Resume.objects.filter(id=resume_id).exists()

    if resume_exists:
        return Response({
            "status": "success",
            "message": "Resume check completed",
            "resume_exists": resume_exists
        }, status=200)
    else:
        return Response({
            "status": "error",
            "message": "Resume does not exist",
            "resume_exists": resume_exists
        }, status=500)


@api_view(["GET"])
def check_questions(request):
    """사용자의 면접 질문이 존재하는지 확인하는 뷰"""

    resume_id = request.GET.get('resume_id') 
    resume_id = int(resume_id)
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


def upload_chunk(request):
    """청크 단위로 오디오 데이터를 서버에 저장하는 뷰"""

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
    """저장된 청크 파일을 S3에 업로드하고 로컬에서 삭제하는 뷰"""

    try:
        resume_id = request.POST.get("resumeId")
        question_id = request.POST.get("questionId")
        chunk_file_path = os.path.join("chunk_data/", f"{question_id}.wav")
        s3_filename = f"{resume_id}_{question_id}.wav"
        s3_url = upload_to_s3(chunk_file_path, s3_filename)
        os.remove(chunk_file_path)

        return JsonResponse({"s3_url": s3_url})
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def transcribe_audio(request):
    """음성을 텍스트화 하는 뷰"""

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

            
# def save_answers(request):
#     '''변환된 텍스트를 Answer 모델에 저장하는 뷰'''

#     try:
#         data = json.loads(request.body.decode("utf-8"))
#         resume_id = data.get("resumeId")
#         s3_urls = data.get("s3Urls")
#         transcriptions = data.get("transcriptions")
#         questions = Question.objects.filter(resume_id=resume_id).order_by("id")

#         # 디버깅을 위한 로그
#         print("Received data:", {
#             "resumeId": resume_id,
#             "s3_urls": s3_urls,
#             "transcriptions": transcriptions
#         })

#         with transaction.atomic():
#             for i in range(len(s3_urls)):
#                 try:
#                     s3_url = s3_urls[i]
#                     original_text = transcriptions[0][i] if isinstance(transcriptions, list) else transcriptions[i]
#                     question = questions[i]
#                     if original_text.strip():
#                         corrected_result = correct_transcription(original_text)
#                         corrected_text = corrected_result.get("보정된 텍스트", original_text)
#                         summary_result = summarize_answer(corrected_text)
#                         summarized_text = summary_result.get("요약", corrected_text)
#                     else:
#                         corrected_text = "답변이 없습니다."
#                         summarized_text = "답변이 없습니다."

#                     Answer.objects.create(
#                         resume_id=resume_id,
#                         question=question,
#                         audio_url=s3_url,
#                         transcribed_text=original_text,
#                         summarized_text=summarized_text
#                     )

#                 except IndexError as e:
#                     return JsonResponse({
#                         "error": f"Index error at position {i}. Arrays lengths: s3_urls={len(s3_urls)}, transcriptions={len(transcriptions)}"
#                     }, status=500)
#                 except Exception as e:
#                     return JsonResponse({"error": str(e)}, status=500)

#         return JsonResponse({"message": "답변 저장 완료"}, status=200)

#     except Exception as e:
#         print("Error in save_answers:", str(e))  # 서버 로그에 에러 출력
#         return JsonResponse({"error": str(e)}, status=500)

def save_answers(request):
    '''변환된 텍스트를 Answer 모델에 저장하는 뷰'''

    try:
        data = json.loads(request.body.decode("utf-8"))
        resume_id = data.get("resumeId")
        s3_urls = data.get("s3Urls")
        transcriptions = data.get("transcriptions")
        questions = Question.objects.filter(resume_id=resume_id).order_by("id")

        if len(s3_urls) != 10:
            return JsonResponse({"error": "10개의 답변이 필요합니다."}, status=400)
        
        # 디버깅을 위한 로그
        print("Received data:", {
            "resumeId": resume_id,
            "s3_urls": s3_urls,
            "transcriptions": transcriptions
        })

        with transaction.atomic():
            for i in range(len(s3_urls)):
                try:
                    s3_url = s3_urls[i]
                    original_text = transcriptions[i]

                    # 빈 문자열 처리
                    if not original_text.strip():
                        original_text = "답변이 녹음되지 않았습니다."

                    question = questions[i]

                    # 빈 답변이 아닐 경우에만 보정 및 요약 진행
                    if original_text != "답변이 녹음되지 않았습니다.":
                        corrected_result = correct_transcription(original_text)
                        corrected_text = corrected_result.get("보정된 텍스트", original_text)
                        summary_result = summarize_answer(corrected_text)
                        summarized_text = summary_result.get("요약", corrected_text)
                    else:
                        corrected_text = original_text
                        summarized_text = original_text

                    Answer.objects.create(
                        resume_id=resume_id,
                        question=question,
                        audio_url=s3_url,
                        transcribed_text=original_text,
                        summarized_text=summarized_text
                    )

                except IndexError as e:
                    return JsonResponse({
                        "error": f"Index error at position {i}. Arrays lengths: s3_urls={len(s3_urls)}, transcriptions={len(transcriptions)}"
                    }, status=500)
                except Exception as e:
                    return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse({"message": "답변 저장 완료"}, status=200)

    except Exception as e:
        print("Error in save_answers:", str(e))  # 서버 로그에 에러 출력
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
def next_question(request, resume_id):  
    """녹음 종료 후 다음 질문을 가져오는 뷰"""

    try:
        current_question_id = request.data.get('question_id')
        questions = Question.objects.filter(resume_id=resume_id).order_by('id')
        current_question = questions.get(id=current_question_id)
        next_questions = questions.filter(id__gt=current_question.id)
        if next_questions.exists():
            next_question = next_questions.first()
        else:
            return Response({
                "status": "complete",
                "message": "모든 질문이 완료되었습니다."
                })

        return Response({
            "question": next_question.text,
            "question_id": next_question.id
            })

    except Exception as e:
        return Response({"error": str(e)})
    
# 헬퍼함수
def create_evaluation(answer):
    """면접에 대한 평가를 생성하고 저장하는 함수"""
    try:
        # audio_url 디버깅
        if answer.audio_url:
            print(f"Audio URL: {answer.audio_url}")  # 실제 저장된 경로 확인
            print(f"File exists: {os.path.exists(answer.audio_url)}")  # 파일 존재 여부 확인
            
        question = answer.question
        job_posting = question.job_posting
        
        evaluation_result = evaluate_answer(
            question_text=question.text,
            answer_text=answer.transcribed_text,
            responsibilities=job_posting.responsibilities,
            qualifications=job_posting.qualifications
        )

        scores = {
            'question_understanding': evaluation_result['질문 이해도']['점수'],
            'logical_flow': evaluation_result['논리적 전개']['점수'],
            'content_specificity': evaluation_result['내용의 구체성']['점수'],
            'problem_solving': evaluation_result['문제 해결 접근 방식']['점수'],
            'organizational_fit': evaluation_result['핵심 기술 및 직무 수행 능력 평가']['점수']
        }

        improvements = [
            evaluation_result['질문 이해도'].get('개선사항', ''),
            evaluation_result['논리적 전개'].get('개선사항', ''),
            evaluation_result['내용의 구체성'].get('개선사항', ''),
            evaluation_result['문제 해결 접근 방식'].get('개선사항', ''),
            evaluation_result['핵심 기술 및 직무 수행 능력 평가'].get('개선사항', '')
        ]
        improvements = [imp for imp in improvements if imp]

        total_score = sum(scores.values())

        # 비언어적 평가 부분 수정
        nonverbal_scores = {
            'pronunciation': 0,
            'speaking_speed': 0,
            'stuttering': 0
        }
        nonverbal_improvements = []
        spm = 0

        if answer.audio_url:
            try:
                print(f"Processing audio from URL: {answer.audio_url}")
                # URL을 직접 audio_analysis 함수에 전달
                nonverbal_result, spm = audio_analysis(answer.audio_url)

                nonverbal_scores = {
                    'pronunciation': nonverbal_result['발음']['점수'],
                    'speaking_speed': nonverbal_result['빠르기']['점수'],
                    'stuttering': nonverbal_result['말더듬']['점수'],
                }

                nonverbal_improvements = [
                    nonverbal_result['발음'].get('개선사항', ''),
                    nonverbal_result['빠르기'].get('개선사항', ''),
                    nonverbal_result['말더듬'].get('개선사항', '')
                ]
                nonverbal_improvements = [imp for imp in nonverbal_improvements if imp]
                
            except Exception as e:
                print(f"Error in audio analysis: {e}")
                print(f"Audio URL was: {answer.audio_url}")

        evaluation = Evaluation.objects.create(
            answer=answer,
            scores=scores,
            total_score=total_score,
            improvements=improvements,
            nonverbal_scores=nonverbal_scores,
            nonverbal_improvements=nonverbal_improvements,
            spm=spm
        )

        return evaluation

    except Exception as e:
        print(f"Error in create_evaluation: {e}")
        return None


def interview_report(request, resume_id):
    """평가 프로세스를 시작하고 면접 리포트 페이지를 렌더링하는 뷰"""
    try:
        resume = get_object_or_404(Resume, id=resume_id)
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')
        evaluation_results = []

        for question in questions:
            answer = Answer.objects.filter(question=question).first()
            if not Evaluation.objects.filter(answer=answer).exists():
                evaluation = create_evaluation(answer)
                if evaluation:
                    evaluation_results.append({
                        'question_id': question.id,
                        'evaluation_id': evaluation.id,
                        'total_score': evaluation.total_score
                    })
        
        # POST 요청일 경우 JSON 응답
        if request.method == 'POST':
            return JsonResponse({
                "message": "평가 생성 완료",
                "evaluations": evaluation_results
            })
            
        # GET 요청일 경우 페이지 렌더링
        context = {
            'candidate_name': resume.name,
            'resume_id': resume_id,
        }
        return render(request, 'report.html', context)
        
    except Exception as e:
        if request.method == 'POST':
            return JsonResponse({"error": str(e)}, status=500)
        messages.error(request, "리포트 생성 중 오류가 발생했습니다.")
        return render(request, 'report.html', {'error': str(e)})


def get_interview_report(request, resume_id):
    """면접 리포트 데이터를 반환하는 API"""
    try:
        # 이력서와 관련 데이터 조회
        resume = get_object_or_404(Resume, id=resume_id)
        questions = Question.objects.filter(resume_id=resume_id).order_by('order')
        
        # 응답 데이터 구성
        report_data = {
            'candidate_name': resume.name,
            'questions': []
        }
        
        # has_evaluations = False  # 평가 데이터 존재 여부 확인
        
        # 각 질문에 대한 데이터 수집
        for question in questions:
            answer = Answer.objects.filter(question=question).first()
            if not answer:
                continue
                
            evaluation = Evaluation.objects.filter(answer=answer).first()
            if not evaluation:
                continue
                
            # has_evaluations = True  # 평가 데이터가 하나라도 있음
            
            question_data = {
                'question_id': question.id,
                'question_text': question.text,
                'answer_text': answer.transcribed_text,
                'scores': evaluation.scores,
                'total_score': evaluation.total_score,
                'improvements': evaluation.improvements,
                'nonverbal_scores': evaluation.nonverbal_scores,
                'nonverbal_improvements': evaluation.nonverbal_improvements,
                'spm': evaluation.spm
            }
            report_data['questions'].append(question_data)
        
        # if not has_evaluations:
        #     return JsonResponse({
        #         "error": "평가 데이터가 아직 생성되지 않았습니다. API 할당량을 확인해주세요.",
        #         "needs_evaluation": True
        #     }, status=404)
        
        return JsonResponse(report_data)
        
    except Exception as e:
        print(f"Error in get_interview_report: {str(e)}")
        return JsonResponse({
            "error": "리포트 데이터를 가져오는 중 오류가 발생했습니다.",
            "detail": str(e)
        }, status=500)