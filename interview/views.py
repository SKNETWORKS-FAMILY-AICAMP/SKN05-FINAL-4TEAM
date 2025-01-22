from django.shortcuts import render, redirect 
from django.contrib import messages
from .forms import ResumeForm

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