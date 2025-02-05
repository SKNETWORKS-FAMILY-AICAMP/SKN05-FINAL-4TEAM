let questions = [];
let currentQuestionIndex = 0;
let timeLeft = 90;
let totalTimeElapsed = 0;
let isRecording = false;
let questionTimerInterval;
let totalTimerInterval;

const timerElement = document.getElementById("timer");
const totalTimerElement = document.getElementById("totalTimer");
const questionTextElement = document.getElementById("questionText");
const startButton = document.getElementById("startRecording");
const stopButton = document.getElementById("stopRecording");

const questionIdInput = document.getElementById("questionId");  // 현재 질문의 ID
const userIdInput = document.getElementById("userId");            // user_id
const totalQuestionsInput = document.getElementById("totalQuestions");  // 총 질문 수


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
    const totalQuestions = parseInt(document.getElementById("totalQuestions").value);
    const questionNumberElement = document.getElementById("questionNumber");
    // 질문 번호 업데이트
    questionNumberElement.textContent = `Q${currentQuestionIndex + 1}/${totalQuestions}`;
}

// AJAX를 이용해 다음 질문을 서버에서 가져오는 함수
function nextQuestion() {
    const userId = userIdInput.value;
    const currentQuestionId = questionIdInput.value;

    // 서버에 POST 요청으로 다음 질문 가져오기
    fetch(`/next_question/${userId}/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
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
                questionIdInput.value = data.question_id; // 새로운 질문 ID 업데이트
                currentQuestionIndex++;
                updateQuestionNumber(); // 질문 번호 UI 업데이트

                timeLeft = 90; // 타이머 초기화
                updateTimerDisplay();

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

    // 인터뷰 관련 UI 숨기기
    const interviewLayout = document.querySelector(".interview-layout");
    const voiceControls = document.getElementById("voiceControls");
    if(interviewLayout) interviewLayout.style.display = "none";
    if(voiceControls) voiceControls.style.display = "none";

    // 모달에 총 면접 시간 업데이트
    const totalMinutes = Math.floor(totalTimeElapsed / 60);
    const totalSeconds = totalTimeElapsed % 60;
    document.getElementById("modalTotalTime").textContent = `${totalMinutes}분 ${totalSeconds}초`;
    document.getElementById("completionModal").style.display = "block";
}

function stopRecording() {
    if (isRecording) {
        isRecording = false;
        clearInterval(questionTimerInterval);
        document.getElementById("startRecording").disabled = false;
        document.getElementById("stopRecording").disabled = true;
        timeLeft = 90; // 타이머 리셋
        updateTimerDisplay();
        nextQuestion();
    }
}

startButton.addEventListener("click", () => {
    if (!isRecording) {
        isRecording = true;
        startButton.disabled = true; // "녹음 시작" 버튼 비활성화
        stopButton.disabled = false; // "녹음 종료" 버튼 활성화
        startQuestionTimer();  // 녹음 시작과 함께 타이머 시작
    }
});

stopButton.addEventListener("click", () => {
    if (isRecording) {
        stopRecording();
    }
});

document.addEventListener("DOMContentLoaded", async () => {
    const userId = userIdInput.value;
    console.log("userId:",userId);

    try {
        const response = await fetch(`/get_questions/${userId}/`);
        console.log("Response status:", response.status);
        const data = await response.json();
        console.log("Response data:", data);
        if (data.questions) {
            questions = data.questions;
            updateQuestionNumber();
            startTotalTimer();
        } else {
            console.error("질문 데이터를 불러오는 데 실패했습니다.");
        }
    } catch (error) {
        console.error("서버와의 연결 중 오류 발생:", error);
    }
});

function endInterview() {
    if(confirm("정말 종료하시겠습니까? AI 리포트를 확인할 수 없게 됩니다.")) {
        window.location.href = "{% url 'main' %}";
    }
}

function viewReport() {
    window.location.href = "{% url 'report' %}";
}

function confirmExit() {
    // HTML 요소에서 data-url 속성 값을 가져옴
    const homeButton = document.getElementById('homeButton');
    const url = homeButton.getAttribute('data-url');

    // 사용자 확인 메시지 표시
    const confirmed = confirm("면접을 중단하시겠습니까?\n중단 시 지금까지의 진행 내용이 저장되지 않습니다.");
    if (confirmed) {
        // 확인을 눌렀을 때 해당 URL로 이동
        window.location.href = url;
    }
    return false; // 기본 동작 방지
}

// 브라우저 뒤로가기 방지 수정
window.history.pushState(null, '', window.location.href);
window.onpopstate = function(event) {
    event.preventDefault();
    window.history.pushState(null, '', window.location.href);
    confirmExit();
};

// HOME 링크 수정
document.querySelector('.nav a').onclick = function(e) {
    e.preventDefault();
    confirmExit();
};

