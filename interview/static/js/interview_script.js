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


    // 평가리포트 페이지 url 받아오기
    async function generateReport() {
        reportBtn.style.display = "none";
        reportButton.style.display = "inline-block";
        const resumeId = resumeIdInput.value

        try {
            const response = await fetch("/api/generate-report/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken(),
                },
                body: JSON.stringify({ resume_id: resumeId }),
            });

            if (!response.ok) {
                throw new Error(`HTTP 오류: ${response.status}`);
            }

            const data = await response.json();
            window.location.href = data.report_url;
        } catch (error) {
            buttonText.textContent = "리포트 생성 실패";
            loadingSpinner.style.display = "none";
        }
    }


    // reportBtn 누를 시
    reportBtn.addEventListener("click", generateReport);


    // AJAX를 이용해 다음 질문을 서버에서 가져오는 함수
    async function nextQuestion() {
        try {
            const resumeId = resumeIdInput.value;
            const currentQuestionId = questionIdInput.value;

            const response = await fetch(`/next_question/${resumeId}/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": getCSRFToken(),
                },
                body: `question_id=${currentQuestionId}`,
            });
            
            if (!response.ok) {  
                throw new Error(`HTTP 오류: ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                completeInterview();
            } else {
                questionTextElement.textContent = data.question;
                questionIdInput.value = data.question_id;
                currentQuestionIndex++;
                clearInterval(questionTimerInterval);
                updateQuestionNumber();
                timeLeft = 90;
                updateTimerDisplay();
            }
        } catch (error) {
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


    // CSRF 토큰 가져오는 함수
    function getCSRFToken() {
        const cookieValue = document.cookie
            .split("; ")
            .find(row => row.startsWith("csrftoken="))
            ?.split("=")[1];
        return cookieValue || "";
    }


    // 면접 도중에 메인 페이지로 이동
    homeButton.addEventListener("click", (event) => {
        const confirmed = confirm("면접을 중단하시겠습니까?\n중단 시 지금까지의 진행 내용이 저장되지 않습니다.");
        if (!confirmed) {
            event.preventDefault();
        }
    });


    startTotalTimer();
});