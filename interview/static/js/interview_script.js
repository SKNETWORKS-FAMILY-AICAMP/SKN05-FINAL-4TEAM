document.addEventListener("DOMContentLoaded", () => {
    
    const reportBtn = document.getElementById("reportBtn");
    const reportButton = document.getElementById("reportButton");
    const buttonText = document.getElementById("buttonText");
    const loadingSpinner = document.getElementById("loadingSpinner");
    const homeButton = document.getElementById("homeButton");
    const timerElement = document.getElementById("timer");
    const totalTimerElement = document.getElementById("totalTime");
    const questionTextElement = document.getElementById("questionText");
    const startButton = document.getElementById("startRecording");
    const stopButton = document.getElementById("stopRecording");
    const questionIdInput = document.getElementById("questionId");  // 현재 질문의 ID
    const resumeIdInput = document.getElementById("resumeId");
    const totalQuestionsInput = document.getElementById("totalQuestions");  // 총 질문 수
    const s3Urls = [];
    const transcriptions = [];

    let currentQuestionIndex = 0;
    let timeLeft = 90;
    let totalTimeElapsed = 0;
    let isRecording = false;
    let questionTimerInterval;
    let totalTimerInterval;
    let mediaRecorder;
    let stream;
    let hasMediaPermission = false;

    
    // 원형 프로그레스 바 업데이트
    function updateTimerDisplay() {
        timerElement.textContent = timeLeft;
        const circle = document.querySelector('.timer-progress');
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (timeLeft / 90) * circumference;
        circle.style.strokeDasharray = `${circumference} ${circumference}`;
        circle.style.strokeDashoffset = offset;
    }


    // 전체 경과 시간 시각화 업데이트
    function updateTotalTimerDisplay() {
        const totalMinutes = Math.floor(totalTimeElapsed / 60);
        const totalSeconds = totalTimeElapsed % 60;
        totalTimerElement.textContent = `${String(totalMinutes).padStart(2, "0")}:${String(totalSeconds).padStart(2, "0")}`;
    }


    // 질문 당 타이머 설정
    function startQuestionTimer() {
        questionTimerInterval = setInterval(() => {
            timeLeft--;
            updateTimerDisplay();

            if (timeLeft === 0) {
                stopRecording();
                nextQuestion();
            }
        }, 1000);
    }


    // 전체 경과 시간 타이머 설정
    function startTotalTimer() {
        totalTimerInterval = setInterval(() => {
            totalTimeElapsed++;
            updateTotalTimerDisplay();
        }, 1000);
    }


    // 총 질문 수와 현재 질문 인덱스를 가져와서 보여줌
    function updateQuestionNumber() {
        const totalQuestions = parseInt(totalQuestionsInput.value);
        const questionNumberElement = document.getElementById("questionNumber");
        questionNumberElement.textContent = `Q${currentQuestionIndex + 1}/${totalQuestions}`;
    }


    // 마이크 권한 요청 함수
    async function requestMediaPermission() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            hasMediaPermission = true;
            stream.getTracks().forEach(track => track.stop());
        } catch (error) {
            alert('마이크 권한이 필요합니다.');
        }
    }


    // 녹음 시작
    async function startRecording() {
        const currentQuestionId = questionIdInput.value;

        if (!hasMediaPermission) {
            await requestMediaPermission();
        }
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
    
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    await sendChunkToServer(event.data, currentQuestionId);
                }
            };

            mediaRecorder.start(1000);

        } catch (error) {
            alert("녹음 중 오류가 발생했습니다.");
            hasMediaPermission = false;
        }
    }


    // 작은 청크 단위로 서버에 전송
    async function sendChunkToServer(chunk, questionId) {
        let formData = new FormData();
        formData.append("chunk", chunk);
        formData.append("questionId", questionId);

        try {
            await fetch("/upload_chunk/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                },
                body: formData
            });
        } catch (error) {
            alert("청크 업로드 중 오류가 발생했습니다.");
        }
    }
    
    
    // 녹음 종료
    async function stopRecording() {
        try {
            if (mediaRecorder && isRecording) {
                const resumeId = resumeIdInput.value;
                const currentQuestionId = questionIdInput.value;

                let lastChunkSent = new Promise((resolve) => {
                    mediaRecorder.ondataavailable = async (event) => {
                        if (event.data.size > 0) {
                            await sendChunkToServer(event.data, currentQuestionId);
                            resolve();
                        }
                    };
                });

                mediaRecorder.stop();
                await lastChunkSent;
                await finalizeAudio(currentQuestionId, resumeId);
            }
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        } catch (error) {
            alert("녹음 종료 시 오류가 발생했습니다.");
        }
    }
    
    
    // S3 업로드 요청
    async function finalizeAudio(questionId, resumeId) {
        let formData = new FormData();
        formData.append("questionId", questionId);
        formData.append("resumeId", resumeId);

        try {
            const response = await fetch("/finalize_audio/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCSRFToken(),
                },
                body: formData
            }); 
            const S3_result = await response.json();
            s3Urls.push(S3_result.s3_url);
        } catch (error) {
            alert("음성 파일 업로드 중 오류가 발생했습니다.");
        }    
    }


    // 녹음 시작 버튼 누를 시
    startButton.addEventListener("click", async () => {
        if (!isRecording) {
            startButton.disabled = true;
            stopButton.disabled = false;
            startQuestionTimer();
            await startRecording();
            isRecording = true;
        }
    });


    // 녹음 종료 버튼 누를 시
    stopButton.addEventListener("click", async () => {
        startButton.disabled = false;
        stopButton.disabled = true;
        await stopRecording();
        isRecording = false;
        nextQuestion();
    });


    // whisper 요청
    async function callWhisper() {
        try {
            const response = await fetch("/transcribe_audio/", {
                method: "POST",
                body: JSON.stringify({ s3_urls: s3Urls }),
                headers: { 
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken(),
                }
            });
    
            const whisper_result = await response.json();
            transcriptions.push(whisper_result.transcriptions);
        } catch (error) {
            alert("음성의 텍스트 변환이 제대로 이루어지지 않았습니다.");
        }
    }
    

    // Answer 테이블에 저장할 데이터 보내기
    async function saveAnswers() {
        try {
            const resumeId = resumeIdInput.value;
            await fetch("/save_answers/", {
                method: "POST",
                body: JSON.stringify({ s3Urls, transcriptions, resumeId }), 
                headers: { 
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken(),
                }
            });
        } catch (error) {
            alert("DB 저장 실패.");
        }
    }

    function viewReport() {
        try {
            // 모달의 버튼을 로딩 상태로 변경
            const originalText = this.textContent;
            this.disabled = true;
            this.innerHTML = `
                <span>AI 리포트 생성 중...</span>
                <div class="spinner"></div>
            `;

            const resumeId = document.getElementById('resumeIdInput').value;
            
            // 리포트 페이지로 직접 이동 (평가 프로세스 호출 없이)
            window.location.href = `/interview-report/${resumeId}/`;

        } catch (error) {
            console.error('Error:', error);
            alert('리포트 생성 중 오류가 발생했습니다.');
            this.disabled = false;
            this.innerHTML = originalText;
        }
    }
    reportBtn.addEventListener("click", viewReport);

    // AJAX를 이용해 다음 질문을 서버에서 가져오는 함수
    function nextQuestion() {
        const resumeId = resumeIdInput.value;
        const currentQuestionId = questionIdInput.value;
        
        console.log("다음 질문 요청:", resumeId, currentQuestionId);

        // 서버에 POST 요청으로 다음 질문 가져오기
        fetch(`/next_question/${resumeId}/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                'X-CSRFToken': getCSRFToken(),
            },
            body: `question_id=${currentQuestionId}`,
        })
        .then((response) => response.json())
        .then((data) => {
            console.log("받은 데이터:", data);
            
            if (data.error || data.status === 'complete') {
                console.log("질문 없음 - 인터뷰 종료");
                completeInterview();
            } else {
                console.log("다음 질문 표시:", data.question);
                // 다음 질문을 화면에 표시
                questionTextElement.textContent = data.question;
                questionIdInput.value = data.question_id;
                currentQuestionIndex++;
                updateQuestionNumber();
                timeLeft = 90;
                updateTimerDisplay();
            }
        }).catch (error) {
            alert("다음 질문을 불러오는 중 오류가 발생했습니다.");
        }
    }


    // 마지막 질문 종료
    async function completeInterview() {
        clearInterval(questionTimerInterval);
        clearInterval(totalTimerInterval);
        
        document.querySelector(".interview-layout").style.display = "none";
        document.getElementById("voiceControls").style.display = "none";

        const totalMinutes = Math.floor(totalTimeElapsed / 60);
        const totalSeconds = totalTimeElapsed % 60;
        document.getElementById("modalTotalTime").textContent = `${totalMinutes}분 ${totalSeconds}초`;
        document.getElementById("completionModal").style.display = "block";
        
        await callWhisper();
        await saveAnswers();
        reportBtn.disabled = false;
    }


    // CSRF 토큰을 가져오는 함수 (이미 있다면 재사용)
    function getCSRFToken() {
        const csrfInput = document.getElementById('csrf_token');
        return csrfInput ? csrfInput.value : '';
    }


    startTotalTimer(); // 총 타이머 시작

    // 리포트 버튼에 이벤트 리스너 추가
    const reportButtonModal = document.querySelector('.report-button');
    if (reportButtonModal) {
        reportButtonModal.addEventListener('click', function() {
            try {
                // 모달의 버튼을 로딩 상태로 변경
                const originalText = this.textContent;
                this.disabled = true;
                this.innerHTML = `
                    <span>AI 리포트 생성 중...</span>
                    <div class="spinner"></div>
                `;

                const resumeId = document.getElementById('resumeIdInput').value;
                
                // 평가 프로세스 API 호출
                fetch(`/api/process-interview-evaluation/${resumeId}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    }
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('서버 응답 오류');
                    }
                    return response.json();
                })
                .then(data => {
                    // URL 패턴 수정 (올바른 URL로 리다이렉트)
                    window.location.href = `/interview-report/${resumeId}/`;
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('리포트 생성 중 오류가 발생했습니다.');
                    // 에러 시 버튼 복구
                    this.disabled = false;
                    this.innerHTML = originalText;
                });

            } catch (error) {
                console.error('Error:', error);
                alert('리포트 생성 중 오류가 발생했습니다.');
                this.disabled = false;
                this.innerHTML = originalText;
            }
        });
    }
});