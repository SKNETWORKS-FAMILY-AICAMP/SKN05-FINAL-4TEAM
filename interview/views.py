from django.shortcuts import render, redirect 
from django.contrib import messages
from django.http import JsonResponse
from .forms import ResumeForm
from .models import Resume, Question, JobPosting
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import generate_q
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction 
import re


# 메인 페이지 렌더링
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

def generate_questions_from_resume(user_id, jobposting_id):
    """
    특정 사용자의 이력서와 채용 공고 정보를 기반으로 질문 생성 및 저장
    """
    # 1. 이력서 데이터 가져오기
    resume_text = get_resume_text(user_id)
    if not resume_text:
        return None, "해당 사용자의 이력서를 찾을 수 없습니다."

    # 2. 사용자가 선택한 채용 공고 데이터 가져오기
    try:
        job_posting = JobPosting.objects.get(id=jobposting_id)
        responsibilities = job_posting.responsibilities
        qualifications = job_posting.qualifications
    except JobPosting.DoesNotExist:
        return None, "해당 기업 공고를 찾을 수 없습니다."
    
    # 3. 평가 기준 설정
    evaluation_metrics = ["질문 이해도", "논리적 전개", "내용의 구체성", "문제 해결 접근 방식", "핵심 기술 및 직무 수행 능력 평가"]
    
    # 4. 질문 생성
    try:
        questions_json = generate_q(resume_text, responsibilities, qualifications, evaluation_metrics)
    except Exception as e:
        return None, f"질문 생성 실패: {str(e)}"
    
    # 5. JSON 응답 확인 및 질문 추출
    print("GPT 질문 응답 (JSON):", questions_json)
    
    if not questions_json or "questions" not in questions_json:
        return None, "질문 생성 실패: 잘못된 JSON 응답"

    # 질문 리스트 추출
    questions_list = questions_json["questions"]  # JSON에서 질문 추출
    if not questions_list or len(questions_list) == 0:
        return None, "질문 생성 실패: 질문이 없습니다."

    # 6. 질문 저장
    try:
        with transaction.atomic():
            for idx, question_text in enumerate(questions_list):
                Question.objects.create(
                    user_id=user_id,
                    text=question_text.strip(),  # 공백 제거
                    category=evaluation_metrics[idx % len(evaluation_metrics)],  # 카테고리 순환
                    order=idx + 1
                )
    except Exception as e:
        return None, f"질문 저장 실패: {str(e)}"

    return questions_list, None



# 질문 생성 API
@csrf_exempt
@api_view(['POST'])
def generate_questions(request):
    """
    질문 생성하는 API 엔드 포인트
    """
    print("요청 데이터:", request.data) 
    
    user_id = request.data.get('user_id')
    jobposting_id = request.data.get('jobposting_id')
    
    if not user_id or not jobposting_id:
        return Response({"error": "user_id와 jobposting_id는 필수입니다."}, status=400)
    
    try:
        user_id = int(user_id) 
        jobposting_id = int(jobposting_id)
    except ValueError:
        return Response({"error": "user_id와 jobposting_id는 정수여야 합니다."}, status=400)
    
    questions, error = generate_questions_from_resume(user_id, jobposting_id)
    if error:
        return Response({"error": error}, status=500)
    
    return Response({"questions": questions}, status=200)


# 연습 면접 페이지
def practice_interview_page(request, user_id):
    """
    연습 면접 페이지를 렌더링하고 질문을 표시
    """
    # 해당 사용자의 질문 가져오기
    question = Question.objects.filter(user_id=user_id, is_used=False).order_by('order').first()

    # 질문이 없는 경우 처리
    if not question:
        return render(request, 'interview_practice.html', {'error': '사용 가능한 질문이 없습니다.'})

    total_questions = Question.objects.filter(user_id=user_id).count()

    # 템플릿에 전달할 데이터
    return render(request, 'interview_practice.html', {
        'question': question.text, 
        'question_id': question.id,
        'user_id': user_id,
        'total_questions': total_questions,
    })


# 실전 면접 페이지
def interview_page(request, user_id):
    """
    실전 면접 페이지를 렌더링합니다.
    """
    question = Question.objects.filter(user_id=user_id, is_used=False).order_by('order').first()
    
    if not question:
        return render(request, 'interview.html', {'error': '사용 가능한 질문이 없습니다.'})

    total_questions = Question.objects.filter(user_id=user_id).count()
    
    return render(request, 'interview.html', {
        'question': question.text, 
        'question_id': question.id,
        'user_id': user_id,
        'total_questions': total_questions,
    })


# 다음 질문 API(실전 면접)
@csrf_exempt
def next_question(request, user_id):
    """
    녹음 종료 후 다음 질문을 가져오는 API
    """
    if request.method == "POST":
        current_question_id = request.POST.get('question_id')

        # 현재 질문을 사용된 상태로 업데이트
        if current_question_id:
            try:
                current_question = Question.objects.get(id=current_question_id)
                current_question.is_used = True
                current_question.save()
            except Question.DoesNotExist:
                return JsonResponse({'error': '유효하지 않은 질문 ID 입니다.'}, status = 400)
            
    # 다음 질문 가져오기
        next_question = Question.objects.filter(user_id=user_id, is_used=False).order_by('order').first()
        if not next_question:
            return JsonResponse({'error': '모든 질문이 완료되었습니다.'})

        return JsonResponse({'question': next_question.text, 'question_id': next_question.id})

    return JsonResponse({'error': '잘못된 요청 방식입니다.'}, status=400)
