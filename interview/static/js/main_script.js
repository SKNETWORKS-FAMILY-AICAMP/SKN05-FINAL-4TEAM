let lastScroll = 0;
let selectedJobId = null;
let jobPostings;


function getCSRFToken() {
    const csrfInput = document.getElementById('csrf_token');
    return csrfInput ? csrfInput.value : '';
}


document.addEventListener('DOMContentLoaded', () => {
    // 스크롤 시 헤더 숨기기 기능
    window.addEventListener('scroll', () => {
        const header = document.querySelector('.header');
        const currentScroll = window.pageYOffset;

        if (currentScroll > lastScroll && currentScroll > 100) {
            header.classList.add('hidden');
        } else {
            header.classList.remove('hidden');
        }

        lastScroll = currentScroll;
    });


    // 공고 선택 함수
    jobPostings = document.querySelectorAll('.job-posting');
    console.log('jobPostings:', jobPostings);

    jobPostings.forEach(posting => {
        posting.addEventListener('click', function () {
            jobPostings.forEach(job => job.classList.remove('selected'));
            this.classList.add('selected');
            selectedJobId = this.dataset.jobId;

            const realBtn = document.getElementById('realBtn');
            realBtn.disabled = false;
        });
    });

    // 면접 시작 버튼 클릭 시 실행되는 함수
    const realBtn  = document.getElementById('realBtn');
    if (realBtn ) {
        realBtn .addEventListener('click', async function () {
            if (!selectedJobId) {
                alert('먼저 지원할 공고를 선택해주세요.');
                return;
            }

            const resumeId = 1; 
            const loadingModal = document.getElementById('loadingModal');
            
            // 로딩 모달 표시
            loadingModal.style.display = 'flex';

            try {
                // 1. 이력서 확인
                const resumeResponse = await fetch(`/api/check_resume?resume_id=${resumeId}`);  // user_id를 resume_id로 변경
                const resumeData = await resumeResponse.json();
                if (!resumeData.resume_exists) {
                    loadingModal.style.display = 'none';
                    if (confirm('이력서 업로드가 필요합니다. 업로드 페이지로 이동하시겠습니까?')) {
                        window.location.href = '/resume/';
                    }
                    return;
                }

                // 2. 질문 생성 요청
                const generateResponse = await fetch('/generate_questions/', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                    },
                    body: JSON.stringify({ 
                        resume_id: resumeId,  // user_id를 resume_id로 변경
                        jobposting_id: selectedJobId 
                    }),
                });

                const generateData = await generateResponse.json();
                if (generateData.error) {
                    loadingModal.style.display = 'none';
                    alert(`질문 생성 중 오류 발생: ${generateData.error}`);
                    return;
                }

                // 3. 질문 생성 완료 확인
                const checkInterval = setInterval(async () => {
                    const questionsResponse = await fetch(`/api/check_questions?resume_id=${resumeId}`);  // user_id를 resume_id로 변경
                    const questionsData = await questionsResponse.json();

                    if (questionsData.questions && questionsData.questions.length >= 10) {
                        clearInterval(checkInterval);
                        loadingModal.style.display = 'none';
                        window.location.href = `/interview/${resumeId}/`; 
                    } else {
                        const loadingMessage = document.querySelector('#loadingModal p');
                        loadingMessage.textContent = `AI가 면접 질문을 생성 중입니다... (${questionsData.questions.length}/10)`;
                    }
                }, 3000);
            } catch (error) {
                console.error('오류 발생:', error);
                loadingModal.style.display = 'none';
                alert('면접 준비 중 문제가 발생했습니다. 다시 시도해주세요.');
            }
        });
    } else {
        console.error("Error: 'realBtn' not found.");
    }

    // 툴팁 토글 기능
    const tooltips = document.querySelectorAll('.info-icon');
    tooltips.forEach(icon => {
        icon.addEventListener('click', function () {
            const tooltip = this.nextElementSibling;
            document.querySelectorAll('.tooltip').forEach(t => {
                if (t !== tooltip) t.classList.remove('show');
            });
            tooltip.classList.toggle('show');
        });
    });

    document.addEventListener('click', (e) => {
        if (!e.target.matches('.info-icon')) {
            document.querySelectorAll('.tooltip').forEach(tooltip => {
                tooltip.classList.remove('show');
            });
        }
    });

    // 스크롤 버튼 표시/숨김 처리
    const jobList = document.querySelector('.job-list');
    const scrollLeftBtn = document.querySelector('.scroll-left');
    const scrollRightBtn = document.querySelector('.scroll-right');

    if (jobList) {
        jobList.addEventListener('scroll', () => {
            const isAtStart = jobList.scrollLeft === 0;
            const isAtEnd = jobList.scrollLeft + jobList.clientWidth >= jobList.scrollWidth;

            if (scrollLeftBtn) scrollLeftBtn.style.display = isAtStart ? 'none' : 'flex';
            if (scrollRightBtn) scrollRightBtn.style.display = isAtEnd ? 'none' : 'flex';
        });

        if (scrollLeftBtn) scrollLeftBtn.style.display = 'none';
    }
});

// 기존 HTML에서 호출하는 startReal 함수 추가
function startReal() {
    if (!selectedJobId) {
        alert('먼저 지원할 공고를 선택해주세요.');
        return;
    }

    localStorage.setItem('selectedJobId', selectedJobId);
    const resumeId = 1; 
    window.location.href = `/interview/${resumeId}/`; 
}
