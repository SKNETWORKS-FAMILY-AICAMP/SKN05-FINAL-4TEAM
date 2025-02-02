const questions = [
    "본인의 장점과 단점을 설명하고, 이를 극복하기 위해 어떤 노력을 하고 있는지 말씀해 주세요.",
    "최근 성취한 가장 큰 성공은 무엇이며, 이를 위해 어떤 과정을 거쳤는지 말씀해 주세요.",
    "팀 프로젝트에서 갈등 상황이 발생했을 때 이를 해결하기 위해 어떤 역할을 했는지 설명해 주세요."
];

let currentQuestionIndex = 0;
let timeLeft = 90;
let totalTimeElapsed = 0;
let isRecording = false;
let questionTimerInterval;
let totalTimerInterval;
let currentRecordingTime = 0;
let recordingTimerInterval;

const timerElement = document.getElementById("timer");
const totalTimerElement = document.getElementById("totalTimer");
const questionTextElement = document.getElementById("questionText");
const questionBox = document.getElementById("questionBox");
const startButton = document.getElementById("startRecording");
const stopButton = document.getElementById("stopRecording");
const completionBox = document.getElementById("completionBox");
const finalTotalTimeElement = document.getElementById("finalTotalTime");

function updateTimerDisplay() {
    document.getElementById("elapsedTimer").textContent = currentRecordingTime;
    
    // 원형 프로그레스 바 업데이트 (3분 = 180초를 최대로 설정)
    const circle = document.querySelector('.timer-progress');
    const circumference = 2 * Math.PI * 45;
    
    if (currentRecordingTime === 0) {  // 타이머가 리셋되었을 때
        circle.style.strokeDasharray = `${circumference} ${circumference}`;
        circle.style.strokeDashoffset = circumference;  // 완전히 비워진 상태로 시작
    } else {  // 타이머가 진행 중일 때
        const maxTime = 180; // 3분을 최대로 설정
        const progress = Math.min(currentRecordingTime / maxTime, 1);
        const offset = circumference - (progress * circumference);
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
        } else {
            clearInterval(questionTimerInterval);
            stopRecording();
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
    const questionNumberElement = document.querySelector('.question-box h3');
    questionNumberElement.textContent = `Q${currentQuestionIndex + 1}/${questions.length}`;
}

function nextQuestion() {
    if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        timeLeft = 90;
        questionTextElement.textContent = questions[currentQuestionIndex];
        updateTimerDisplay();
        updateQuestionNumber();
    } else {
        completeInterview();
    }
}

function completeInterview() {
    clearInterval(questionTimerInterval);
    clearInterval(totalTimerInterval);

    // 면접 UI 숨기기
    document.querySelector(".interview-layout").style.display = "none";
    document.getElementById("voiceControls").style.display = "none";

    // 모달 표시
    const totalMinutes = Math.floor(totalTimeElapsed / 60);
    const totalSeconds = totalTimeElapsed % 60;
    document.getElementById("modalTotalTime").textContent = 
        `${totalMinutes}분 ${totalSeconds}초`;
    document.getElementById("completionModal").style.display = "block";
}

function updateProgress() {
    const progress = (currentQuestionIndex / questions.length) * 100;
    document.getElementById('progressBar').style.width = `${progress}%`;
    document.getElementById('questionNumber').textContent = currentQuestionIndex + 1;
    document.getElementById('totalQuestions').textContent = questions.length;
}

// 페이지 로드 시 바로 총 타이머 시작
document.addEventListener('DOMContentLoaded', () => {
    startTotalTimer();  // 페이지 로드 시 총 타이머 시작
    updateProgress();   // 초기 진행 상태 표시
    updateQuestionNumber();  // 초기 질문 번호 설정
});

function stopRecording() {
    if (isRecording) {
        isRecording = false;
        document.getElementById('recordingIndicator').style.display = 'none';
        clearInterval(questionTimerInterval);
        startButton.disabled = false;
        stopButton.disabled = true;
        timeLeft = 90; // 타이머 리셋
        updateTimerDisplay(); // 타이머 표시 업데이트
        updateProgress();
        nextQuestion();
    }
}

function resetRecordingTimer() {
    currentRecordingTime = 0;
    updateTimerDisplay();
}

startButton.addEventListener("click", () => {
    if (!isRecording) {
        isRecording = true;
        document.getElementById("startRecording").disabled = true;
        document.getElementById("stopRecording").disabled = false;
        resetRecordingTimer();  // 녹음 시작 전 타이머 리셋

        recordingTimerInterval = setInterval(() => {
            currentRecordingTime++;
            updateTimerDisplay();
        }, 1000);

        if (totalTimeElapsed === 0) startTotalTimer();
    }
});

stopButton.addEventListener("click", () => {
    if (isRecording) {
        isRecording = false;
        clearInterval(recordingTimerInterval);
        document.getElementById("startRecording").disabled = false;
        document.getElementById("stopRecording").disabled = true;
        resetRecordingTimer();  // 녹음 종료 시 타이머 리셋
        nextQuestion();
    }
});

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