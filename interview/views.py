from django.shortcuts import render, redirect 
from django.contrib import messages
from .forms import ResumeForm
from .models import Resume
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import generate_q
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
def resume_form(request):
    if request.method == 'POST':
        form = ResumeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "이력서가 성공적으로 제출되었습니다!")
            print("데이터 저장 성공")
            return redirect('resume_form')
        else:
            messages.error(request, "폼 유효성 검사에 실패했습니다. 입력값을 확인해주세요.")
            print("폼 유효성 검사 실패:", form.errors)
    else:
        form = ResumeForm()

    return render(request, 'resume_form.html', {'form': form})


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
    

@csrf_exempt
@api_view(['POST'])
def generate_questions(request):
    """
    질문 생성하는 API 엔드 포인트
    """
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({"error": "user_id는 필수입니다."}, status=400)
    
    evaluation_metrics = ["문제 해결 능력", "팀워크", "기술 깊이"]
    
    try:
        # get_resume_text 함수로 이력서 데이터 가져오기
        resume_text = get_resume_text(user_id)
        if not resume_text:
            return Response({"error": "해당 사용자의 이력서를 찾을 수 없습니다."}, status=404)
    
        # gpt 호출
        questions = generate_q(resume_text, evaluation_metrics)
        return Response({"questions": questions})
    
    except Exception as e:
        return Response({"error": str(e)}, status=500)
    