function updateCharCount(textarea) {
    const charCount = textarea.value.length;
    const maxChar = 500;
    textarea.nextElementSibling.textContent = `${charCount}/${maxChar}`;
}

function submitForm(event) {
    event.preventDefault(); // 폼 제출로 인한 페이지 새로고침 방지

    // 필수 입력 필드 체크
    const name = document.getElementById('name').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const email = document.getElementById('email').value.trim();
    const project = document.getElementById('project-experience').value.trim();
    const problem = document.getElementById('problem-solving').value.trim();
    const teamwork = document.getElementById('teamwork-experience').value.trim();
    const development = document.getElementById('self-development').value.trim();

    // 빈칸 체크
    if (!name) {
        alert('이름을 입력해주세요.');
        document.getElementById('name').focus();
        return;
    }
    if (!phone) {
        alert('전화번호를 입력해주세요.');
        document.getElementById('phone').focus();
        return;
    }
    if (!email) {
        alert('이메일을 입력해주세요.');
        document.getElementById('email').focus();
        return;
    }
    if (!project) {
        alert('프로젝트 경험을 입력해주세요.');
        document.getElementById('project-experience').focus();
        return;
    }
    if (!problem) {
        alert('문제 해결 사례를 입력해주세요.');
        document.getElementById('problem-solving').focus();
        return;
    }
    if (!teamwork) {
        alert('팀워크 경험을 입력해주세요.');
        document.getElementById('teamwork-experience').focus();
        return;
    }
    if (!development) {
        alert('자기 개발 노력을 입력해주세요.');
        document.getElementById('self-development').focus();
        return;
    }

    // 모든 필드가 입력되었을 때
    alert("이력서가 성공적으로 제출되었습니다.");

    // 폼 제출
    document.getElementById('resumeForm').submit();
}