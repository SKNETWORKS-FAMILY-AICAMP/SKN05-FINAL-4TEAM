let lastScroll = 0;
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

let selectedJobId = null;

function selectJob(element) {
    // 이력서 업로드 상태 확인
    const isResumeUploaded = localStorage.getItem('isResumeUploaded');
    
    if (!isResumeUploaded) {
        if (confirm('이력서 업로드가 필요합니다. 이력서 업로드 페이지로 이동하시겠습니까?')) {
            // 이력서 업로드 페이지로 이동
            window.location.href = "{% url 'resume_form' %}";
            // 또는 직접 경로 지정
            // window.location.href = "/resume/upload/";
        }
        return;
    }

    // 이미 선택된 공고를 다시 클릭한 경우
    if (selectedJobId === element.dataset.jobId) {
        element.classList.remove('selected');
        selectedJobId = null;
        document.getElementById('realBtn').disabled = true;
        return;
    }

    // 이전에 선택된 공고의 스타일 초기화
    document.querySelectorAll('.job-posting').forEach(job => {
        job.classList.remove('selected');
    });

    // 새로운 공고 선택
    element.classList.add('selected');
    selectedJobId = element.dataset.jobId;
    document.getElementById('realBtn').disabled = false;
}


function startReal() {
  if (!selectedJobId) {
    alert('먼저 지원할 공고를 선택해주세요.');
    return;
  }
  // 선택된 공고 정보 저장
  localStorage.setItem('selectedJobId', selectedJobId);
  window.location.href = "{% url 'interview' user_id=1 %}";
}

// 부드러운 스크롤 함수 추가
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const section = document.querySelector(this.getAttribute('href'));
        section.scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// 툴팁 토글 함수
function toggleTooltip(icon) {
    const tooltip = icon.nextElementSibling;
    const allTooltips = document.querySelectorAll('.tooltip');
    
    // 다른 모든 툴팁 닫기
    allTooltips.forEach(t => {
        if (t !== tooltip) t.classList.remove('show');
    });
    
    // 클릭된 툴팁 토글
    tooltip.classList.toggle('show');
}

// 툴팁 외부 클릭시 닫기
document.addEventListener('click', (e) => {
    if (!e.target.matches('.info-icon')) {
        document.querySelectorAll('.tooltip').forEach(tooltip => {
            tooltip.classList.remove('show');
        });
    }
});

function scrollJobs(direction) {
    const container = document.querySelector('.job-list');
    const scrollAmount = 320; // 카드 너비 + 간격
    
    if (direction === 'left') {
        container.scrollBy({
            left: -scrollAmount,
            behavior: 'smooth'
        });
    } else {
        container.scrollBy({
            left: scrollAmount,
            behavior: 'smooth'
        });
    }
}

// 스크롤 버튼 표시/숨김 처리
const jobList = document.querySelector('.job-list');
const scrollLeftBtn = document.querySelector('.scroll-left');
const scrollRightBtn = document.querySelector('.scroll-right');

jobList.addEventListener('scroll', () => {
    const isAtStart = jobList.scrollLeft === 0;
    const isAtEnd = jobList.scrollLeft + jobList.clientWidth >= jobList.scrollWidth;
    
    scrollLeftBtn.style.display = isAtStart ? 'none' : 'flex';
    scrollRightBtn.style.display = isAtEnd ? 'none' : 'flex';
});

// 초기 상태 설정
scrollLeftBtn.style.display = 'none';

// 이력서 업로드 함수 추가
function handleResumeUpload() {
    // 이력서 업로드 처리 로직
    // ...
    
    // 업로드 성공 시
    localStorage.setItem('isResumeUploaded', 'true');
    alert('이력서가 성공적으로 업로드되었습니다.');
}

// 페이지 로드 시 이력서 업로드 상태 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 이력서 업로드 상태 확인
    const isResumeUploaded = localStorage.getItem('isResumeUploaded');
    
    // 공고 선택 섹션의 스타일 업데이트
    const jobPostings = document.querySelectorAll('.job-posting');
    jobPostings.forEach(posting => {
        if (!isResumeUploaded) {
            posting.style.opacity = '0.6';
            posting.style.cursor = 'not-allowed';
        } else {
            posting.style.opacity = '1';
            posting.style.cursor = 'pointer';
        }
    });
});

document.getElementById('startButton').addEventListener('click', async function() {
    const loadingModal = document.getElementById('loadingModal');
    loadingModal.style.display = 'flex';

    try {
        // RDS에서 질문 생성 상태 확인
        const response = await fetch('/api/check-questions', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to check questions');
        }

        const data = await response.json();

        if (data.questions && data.questions.length === 10) {
            // 10개의 질문이 모두 생성되어 있으면 바로 면접 페이지로 이동
            window.location.href = 'interview.html';
        } else {
            // 질문이 없거나 10개가 되지 않으면 생성 상태를 주기적으로 확인
            const checkInterval = setInterval(async () => {
                const checkResponse = await fetch('/api/check-questions');
                const checkData = await checkResponse.json();

                if (checkData.questions && checkData.questions.length === 10) {
                    clearInterval(checkInterval);
                    window.location.href = 'interview.html';
                }
                // 로딩 메시지 업데이트
                const loadingMessage = document.querySelector('#loadingModal p');
                if (checkData.questions) {
                    loadingMessage.textContent = `AI가 면접 질문을 생성하고 있습니다... (${checkData.questions.length}/10)`;
                }
            }, 3000); // 3초마다 확인
        }
    } catch (error) {
        console.error('Error:', error);
        loadingModal.style.display = 'none';
        alert('면접 준비 중 오류가 발생했습니다. 다시 시도해주세요.');
    }
});