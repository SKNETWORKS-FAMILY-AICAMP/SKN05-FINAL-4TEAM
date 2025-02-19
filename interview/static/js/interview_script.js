document.addEventListener("DOMContentLoaded", () => {
    
    const reportBtn = document.getElementById("reportBtn");
    const homeButton = document.getElementById("homeButton");

    const timerElement = document.getElementById("timer");
    const totalTimerElement = document.getElementById("totalTime");
    const questionTextElement = document.getElementById("questionText");
    const startButton = document.getElementById("startRecording");
    const stopButton = document.getElementById("stopRecording");

    const questionIdInput = document.getElementById("questionId");
    const resumeIdInput = document.getElementById("resumeId");
    const totalQuestionsInput = document.getElementById("totalQuestions");

    let currentQuestionIndex = 0;
    let timeLeft = 90;
    let totalTimeElapsed = 0;
    let isRecording = false;
    let questionTimerInterval;
    let totalTimerInterval;
    let s3Urls = [];
    let transcriptions = [];

    let mediaRecorder;
    let audioStream;
    let audioBlob;
    let audioUrl;
    let stream;
    let hasMediaPermission = false;

    // 모달 관련 요소 초기화 추가
    const completionModal = document.getElementById("completionModal");
    const modalContent = document.querySelector('.modal-content');
    let progressTextElement;

    function updateTimerDisplay() {
        timerElement.textContent = timeLeft;

        // 원형 프로그레스 바 업데이트
        const circle = document.querySelector('.timer-progress');
        if(circle) {
            const circumference = 2 * Math.PI * 45;
            const offset = circumference - (timeLeft / 90) * circumference;
            circle.style.strokeDasharray = `${circumference} ${circumference}`;
            circle.style.strokeDashoffset = offset;
        }
        
    }

    function updateTotalTimerDisplay() {
        if (!totalTimerElement) {
            console.error("총 면접 시간을 표시할 DOM 요소를 찾을 수 없습니다.");
            return;
        }

        const totalMinutes = Math.floor(totalTimeElapsed / 60);
        const totalSeconds = totalTimeElapsed % 60;
        totalTimerElement.textContent = `${String(totalMinutes).padStart(2, "0")}:${String(totalSeconds).padStart(2, "0")}`;
    }


    function startQuestionTimer() {
        clearInterval(questionTimerInterval);
        timeLeft = 90; // 타이머 시작 시 90초로 초기화
        updateTimerDisplay(); // 초기 상태 표시
        
        questionTimerInterval = setInterval(() => {
            if (timeLeft > 0) {
                timeLeft--;
                updateTimerDisplay();
                if (timeLeft === 0) {  // 시간이 0이 되면
                    clearInterval(questionTimerInterval);
                    if (isRecording) {  // 녹음 중이었다면
                        stopRecording();
                    } else{
                        nextQuestion();  // 타이머가 0이면 자동으로 다음 질문으로 이동
                    }
                    
                }
            }
        }, 1000);
    }

    function startTotalTimer() {
        totalTimerInterval = setInterval(() => {
            totalTimeElapsed++;
            updateTotalTimerDisplay();
        }, 1000);
    }

    function updateQuestionNumber() {
        // 총 질문 수와 현재 질문 인덱스를 가져옴
        const totalQuestions = parseInt(totalQuestionsInput.value);
        const questionNumberElement = document.getElementById("questionNumber");
        questionNumberElement.textContent = `Q${currentQuestionIndex + 1}/${totalQuestions}`;
    }

    async function requestMediaPermission() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            hasMediaPermission = true;
            stream.getTracks().forEach(track => track.stop());
        } catch (error) {
            console.error('마이크 권한 획득 실패:', error);
            alert('마이크 권한이 필요합니다.');
        }
    }

    async function startRecording() {
        const resumeId = resumeIdInput.value;
        try {
            currentQuestionId = questionIdInput.value;
    
            // 마이크 권한 확인 후 요청
            if (!hasMediaPermission) {
                await requestMediaPermission();
            }
            
            // 녹음 준비
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
    
            // 녹음 데이터(청크)를 서버에 전송
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    await sendChunkToServer(event.data, currentQuestionId);
                }
            };

            // 1초마다 데이터 청크 생성 후 서버 전송
            mediaRecorder.start(1000);

        } catch (error) {
            console.error("녹음 시작 실패:", error);
            alert("녹음을 시작할 수 없습니다.");
            hasMediaPermission = false;
        }
    }
    
    // 녹음 종료
    async function stopRecording() {
        if (mediaRecorder && isRecording) {
            currentQuestionId = questionIdInput.value;
            const resumeId = resumeIdInput.value;
            mediaRecorder.stop();
            isRecording = false;
            await finalizeAudio(currentQuestionId, resumeId);

            // 마이크 스트림 정리
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        }
    }
    
    // CSRF 토큰을 쿠키에서 가져오는 함수
    function getCSRFToken() {
        const csrfInput = document.getElementById('csrf_token');
        return csrfInput ? csrfInput.value : '';
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
                    'X-CSRFToken': getCSRFToken()
                },
                body: formData,
                credentials: 'same-origin' 
            });
        } catch (error) {
            console.error("청크 업로드 실패:", error);
            alert("청크 업로드 중 오류가 발생했습니다.");
        }
    }
    

    // 서버에서 모든 청크를 합쳐 S3로 업로드 요청
    async function finalizeAudio(questionId, resumeId) {
        try {
            let formData = new FormData();
            formData.append("questionId", questionId);
            formData.append("resumeId", resumeId);
    
            const response = await fetch("/finalize_audio/", {
                method: "POST",
                headers: {
                    'X-CSRFToken': getCSRFToken(),  // CSRF 토큰 추가
                },
                body: formData
            });
    
            if (!response.ok) {
                throw new Error(`HTTP 오류: ${response.status}`);
            }
    
            const result = await response.json();
    
            if (result.s3_url) {
                s3Urls.push(result.s3_url);
                console.log(`✅ S3 업로드 완료: ${result.s3_url}`);
            } else {
                console.warn("⚠ S3 URL이 응답에 없습니다.");
            }
    
        } catch (error) { 
            console.error("S3 업로드 실패:", error);
            alert("음성 파일을 S3에 업로드하는 중 오류가 발생했습니다.");
        }
    }


    startButton.addEventListener("click", async () => {
        if (!isRecording) {
            startButton.disabled = true;
            stopButton.disabled = false;
            isRecording = true;
            startQuestionTimer();  
            await startRecording();
        }
    });

    stopButton.addEventListener("click", async () => {
        await stopRecording();
        startButton.disabled = false;
        stopButton.disabled = true;
        clearInterval(questionTimerInterval);
        timeLeft = 90; // 타이머 리셋
        updateTimerDisplay();
        nextQuestion();
    });


    async function transcribeAll(progressCallback) {
        try {
            const response = await fetch("/transcribe_audio/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ 
                    s3_urls: s3Urls,
                    total_files: s3Urls.length
                }),
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('음성 변환 요청 실패');
            }
        
            const result = await response.json();
            
            // 서버에서 진행 상황 업데이트를 받았다면
            if (result.current && result.total && progressCallback) {
                progressCallback(result.current, result.total);
            }
        
            // transcriptions.push(result.transcriptions);
            transcriptions = result.transcriptions; // 직접 배열에 넣기
            return transcriptions;
        
        } catch (error) {
            console.error("transcribeAll() 실패:", error);
            throw error;
        }
    }
    

    async function saveAnswers() {
        try {
            if (transcriptions.length === 0) {
                console.warn("⚠ 변환된 데이터가 없습니다. 저장하지 않습니다.");
                return;
            }

            const resumeId = resumeIdInput.value;
            
            // transcriptions가 이중 배열인 경우 첫 번째 요소만 사용
            let formattedTranscriptions = Array.isArray(transcriptions[0]) ? transcriptions[0] : transcriptions;

            console.log('Transcriptions 변환:', {
                before: transcriptions,
                after: formattedTranscriptions
            });

            const requestData = {
                resumeId: resumeId,
                s3Urls: s3Urls,
                transcriptions: formattedTranscriptions
            };

            console.log('전송할 최종 데이터:', requestData);

            const response = await fetch('/save_answers/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(requestData),
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP 오류! 상태: ${response.status}, 메시지: ${JSON.stringify(errorData)}`);
            }

            const result = await response.json();
            console.log('답변 저장 성공:', result);
            return result;

        } catch (error) {
            console.error('DB 저장 실패:', error);
            console.error('오류 상세정보:', {
                message: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async function viewReport(event) {
        try {
            const button = event.currentTarget;
            const originalText = button.textContent;
            const resumeId = resumeIdInput.value;

            
            if (!resumeId) {
                throw new Error('Resume ID를 찾을 수 없습니다.');
            }

            console.log("Resume ID:", resumeId);

            button.disabled = true;
            button.innerHTML = `
                <span>AI 리포트 생성 중...</span>
                <div class="spinner"></div>
            `;

            // 평가 프로세스 API 호출
            const response = await fetch(`/interview-report/${resumeId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
            },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('서버 응답 오류');
            }

            const data = await response.json();
            console.log('평가 완료:', data);

            // report URL로 리다이렉트
            window.location.href = `/interview-report/${resumeId}/`;
            
        } catch(error) {
            console.error('Error:', error);
            alert('리포트 생성 중 오류가 발생했습니다.');
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
            }

    }

    // 리포트 버튼에 이벤트 리스너 추가
    if (reportBtn) {
        reportBtn.addEventListener("click", viewReport);
    }

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

                // 버튼 상태 초기화
                startButton.disabled = false;
                stopButton.disabled = true;
                isRecording = false;
            }
        })
        .catch((error) => {
            console.error("다음 질문을 불러오는 중 오류 발생:", error);
        });
    }

    async function completeInterview() {
        clearInterval(questionTimerInterval);
        clearInterval(totalTimerInterval);
        
        // 면접 UI 숨기기
        document.querySelector(".interview-layout").style.display = "none";
        document.getElementById("voiceControls").style.display = "none";

        try {
            const resumeId = document.body.dataset.resumeId; 

            // 모달 표시 및 총 면접 시간 업데이트
            const totalMinutes = Math.floor(totalTimeElapsed / 60);
            const totalSeconds = totalTimeElapsed % 60;
            
            // 모달 표시 전에 내용 업데이트
            const modalTotalTime = document.getElementById("modalTotalTime");
            if (modalTotalTime) {
                modalTotalTime.textContent = `${totalMinutes}분 ${totalSeconds}초`;
            }

            // 모달 표시
            if (completionModal) {
                completionModal.style.display = "block";
            }

            progressTextElement = document.createElement('div');
            progressTextElement.className = 'progress-text';
            if (modalContent) {
                modalContent.appendChild(progressTextElement);
            }

            // 음성 변환 진행
            console.log("음성 변환 시작...");
            progressTextElement.textContent = "음성 파일 변환 중... ";
            const transcriptionResult = await transcribeAll((current, total) => {
                progressTextElement.textContent = `음성 파일 변환 중... (${current}/${total})`;
            });
            console.log("변환 결과:", transcriptionResult);

            // 답변 저장
            console.log("답변 저장 시작...");
            progressTextElement.textContent = "답변 데이터 저장 중...";
            const saveResult = await saveAnswers();
            console.log("저장 결과:", saveResult);

            // 완료 후 UI 업데이트
            if (progressTextElement) {
                progressTextElement.remove();
            }
            if (reportBtn) {
                reportBtn.disabled = false;
                reportBtn.innerHTML = "AI 리포트 확인하기";
            }

        } catch (error) {
            console.error('면접 완료 처리 중 오류:', error);
            alert('면접 데이터 처리 중 오류가 발생했습니다.');
            
            if (progressTextElement) {
                progressTextElement.textContent = "처리 중 오류가 발생했습니다.";
                progressTextElement.style.color = "red";
            }
        }
    }

    // CSRF 토큰을 가져오는 함수 (이미 있다면 재사용)
    function getCSRFToken() {
        const csrfInput = document.getElementById('csrf_token');
        return csrfInput ? csrfInput.value : '';
    }

    // 면접 중간메인페이지로 이동하기
    if (homeButton) {
        homeButton.addEventListener("click", (event) => {
            const confirmed = confirm("면접을 중단하시겠습니까?\n중단 시 지금까지의 진행 내용이 저장되지 않습니다.");
            if (!confirmed) {
                event.preventDefault();
            }
        });
    } else{
        console.error("homeButton 요소를 찾을 수 없습니다.");
    }

    startTotalTimer(); // 총 타이머 시작

});
