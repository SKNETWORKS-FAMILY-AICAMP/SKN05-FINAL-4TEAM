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
        // 이미 선택된 공고를 다시 클릭한 경우
        if (selectedJobId === element.dataset.jobId) {
            element.style.border = '1px solid #ccc';
            element.style.backgroundColor = '#f9f9f9';
            selectedJobId = null;

            // 버튼 비활성화
            document.getElementById('practiceBtn').disabled = true;
            document.getElementById('realBtn').disabled = true;
            return;
        }

        // 이전에 선택된 공고의 스타일 초기화
        document.querySelectorAll('.job-posting').forEach(job => {
            job.style.border = '1px solid #ccc';
            job.style.backgroundColor = '#f9f9f9';
        });

        // 새로운 공고 선택
        element.style.border = '2px solid #003366';
        element.style.backgroundColor = '#e6f3ff';
        selectedJobId = element.dataset.jobId;
        
        // 버튼 활성화
        document.getElementById('practiceBtn').disabled = false;
        document.getElementById('realBtn').disabled = false;
    }

    function startPractice() {
        if (!selectedJobId) {
        alert('먼저 지원할 공고를 선택해주세요.');
        return;
        }

        // django url 가져오기
        const url = document.getElementById('practiceBtn').dataset.url;
        // 선택된 공고 정보 저장
        localStorage.setItem('selectedJobId', selectedJobId);
        window.location.href = url;
    }

    function startReal() {
        if (!selectedJobId) {
        alert('먼저 지원할 공고를 선택해주세요.');
        return;
        }

        //django url 가져오기
        const url = document.getElementById('realBtn').dataset.url;
        // 선택된 공고 정보 저장
        localStorage.setItem('selectedJobId', selectedJobId);

        window.location.href = url;
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