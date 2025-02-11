document.addEventListener("DOMContentLoaded", () => {
    
    const reportBtn = document.getElementById("reportBtn");
    const reportButton = document.getElementById("reportButton");
    const buttonText = document.getElementById("buttonText");
    const loadingSpinner = document.getElementById("loadingSpinner");
    
    const timerElement = document.getElementById("timer");
    const totalTimerElement = document.getElementById("totalTime");
    const questionTextElement = document.getElementById("questionText");
    const startButton = document.getElementById("startRecording");
    const stopButton = document.getElementById("stopRecording");

    const questionIdInput = document.getElementById("questionId");  // 현재 질문의 ID
    const userIdInput = document.getElementById("userId");            // user_id
    const totalQuestionsInput = document.getElementById("totalQuestions");  // 총 질문 수

    let questions = [];
    let currentQuestionIndex = 0;
    let timeLeft = 90;
    let totalTimeElapsed = 0;
    let isRecording = false;
    let questionTimerInterval;
    let totalTimerInterval;

    let mediaRecorder;
    let audioStream;
    let audioBlob;
    let audioUrl;
    let stream;
    let hasMediaPermission = false;
    

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
        try {
            audioChunks = [];
            currentQuestionId = questionIdInput.value;
    
            // 마이크 권한 확인 후 요청
            if (!hasMediaPermission) {
                await requestMediaPermission();
            }
    
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
    
            // 🔹 1초마다 녹음 데이터(청크)를 서버에 전송
            mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    await sendChunkToServer(event.data, currentQuestionId);
                }
            };
    
            // 🔹 녹음이 종료될 때 마지막 청크 강제 전송 + S3 업로드 요청
            mediaRecorder.onstop = async () => {
                await finalizeAudio(currentQuestionId);
            };
    
            // 🔹 1초마다 데이터 청크 생성 후 서버 전송
            mediaRecorder.start(1000);
    
            // 버튼 상태 변경
            startButton.disabled = true;
            stopButton.disabled = false;
            isRecording = true;
        } catch (error) {
            console.error("녹음 시작 실패:", error);
            alert("녹음을 시작할 수 없습니다.");
            hasMediaPermission = false;
        }
    }
    
    // 🔥 녹음 종료
    async function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
    
            // 마이크 스트림 정리
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
    
            // 버튼 상태 변경
            startButton.disabled = false;
            stopButton.disabled = true;
        }
    }
    
    // 🔥 작은 청크 단위로 서버에 전송
    async function sendChunkToServer(chunk, questionId) {
        let formData = new FormData();
        formData.append("chunk", chunk);
        formData.append("questionId", questionId);
    
        try {
            await fetch("/upload_chunk/", {
                method: "POST",
                body: formData
            });
        } catch (error) {
            console.error("청크 업로드 실패:", error);
        }
    }
    
    // 🔥 서버에서 모든 청크를 합쳐 S3로 업로드 요청
    async function finalizeAudio(questionId) {
        try {
            const response = await fetch("/finalize_audio/", {
                method: "POST",
                body: JSON.stringify({ questionId }),
                headers: {
                    "Content-Type": "application/json"
                }
            });
    
            if (!response.ok) {
                throw new Error("S3 업로드 실패");
            }
        } catch (error) {
            console.error("최종 업로드 실패:", error);
            alert("음성 파일을 S3에 업로드하는 중 오류가 발생했습니다.");
        }
    }

    startButton.addEventListener("click", async () => {
        await startRecording();
        startQuestionTimer();
    });
    
    stopButton.addEventListener("click", async () => {
        await stopRecording();
    });

    async function generateReport() {
        reportBtn.style.display = "none";
        reportButton.style.display = "inline-block";

        try {
            const response = await fetch("/api/generate-report/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken(),
                },
                body: JSON.stringify({ user_id: userIdInput.value }),
            });

            if (!response.ok) {
                throw new Error("리포트 생성 실패");
            }

            const data = await response.json();
            if (data.report_url) {
                window.location.href = data.report_url;
            } else {
                throw new Error("리포트 URL이 없음");
            }
        } catch (error) {
            console.error("리포트 생성 중 오류:", error);
            buttonText.textContent = "리포트 생성 실패";
            loadingSpinner.style.display = "none";
        }
    }
    reportBtn.addEventListener("click", generateReport);

    // AJAX를 이용해 다음 질문을 서버에서 가져오는 함수
    function nextQuestion() {
        const userId = userIdInput.value;
        const currentQuestionId = questionIdInput.value;

        // 서버에 POST 요청으로 다음 질문 가져오기
        fetch(`/next_question/${userId}/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                'X-CSRFToken': getCSRFToken(), // CSRF 토큰 추가
            },
            body: `question_id=${currentQuestionId}`,
        })
        .then((response) => response.json())
        .then((data) => {
            if (data.error) {
                // 더 이상 질문이 없는 경우 인터뷰 종료 처리
                completeInterview();
            } else {
                // 다음 질문을 화면에 표시
                questionTextElement.textContent = data.question;
                    questionIdInput.value = data.question_id;
                currentQuestionIndex++;
                updateQuestionNumber(); // 질문 번호 UI 업데이트
                timeLeft = 90; // 타이머 초기화
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

    function completeInterview() {
        clearInterval(questionTimerInterval);
        clearInterval(totalTimerInterval);
    
        document.querySelector(".interview-layout").style.display = "none";
        document.getElementById("voiceControls").style.display = "none";

        // 모달에 총 면접 시간 업데이트
        const totalMinutes = Math.floor(totalTimeElapsed / 60);
        const totalSeconds = totalTimeElapsed % 60;
        document.getElementById("modalTotalTime").textContent = `${totalMinutes}분 ${totalSeconds}초`;
        document.getElementById("completionModal").style.display = "block";

        // let reportBtn = document.getElementById("reportBtn");
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


    // 리포트 보기 함수
    // function viewReport() {
    //     window.location.href = "{% url 'report' %}";
    // }
    function viewReport() {
        let reportBtn = document.getElementById("reportBtn");
        let reportUrl = reportBtn.getAttribute("data-url");
    
        if (reportUrl) {
            window.location.href = reportUrl;
        } else {
            console.error("리포트 URL을 찾을 수 없습니다.");
        }
        window.viewReport = viewReport;
    }

    // 홈으로 이동 시 확인
    function confirmExit() {
        const homeButton = document.getElementById("homeButton");
        const url = homeButton.getAttribute("data-url");

        const confirmed = confirm("면접을 중단하시겠습니까?\n중단 시 지금까지의 진행 내용이 저장되지 않습니다.");
        if (confirmed) {
            // window.location.href = url;
            window.location.href = "{% url 'main %}";
        }
        return false;
    }

    // 브라우저 뒤로가기 방지
    window.history.pushState(null, "", window.location.href);
    window.onpopstate = function (event) {
        event.preventDefault();
        window.history.pushState(null, "", window.location.href);
        confirmExit();
    };

    document.querySelector(".nav a").addEventListener("click", e => {
        e.preventDefault();
        confirmExit();
    });

    startTotalTimer(); // 총 타이머 시작
});