// PDF 다운로드 함수를 전역 스코프에 정의
window.downloadPDF = function() {
    console.log('1. PDF 다운로드 함수 시작'); // 디버깅 로그 1
    
    const element = document.querySelector('.container');
    const downloadSection = document.querySelector('.download-section');
    
    if (!element) {
        console.error('컨테이너 요소를 찾을 수 없습니다');
        return;
    }
    console.log('2. 컨테이너 요소 찾음:', element); // 디버깅 로그 2
    
    const downloadButton = document.querySelector('.download-button');
    if (downloadButton) {
        downloadButton.disabled = true;
        downloadButton.textContent = '다운로드 중...';
        console.log('3. 다운로드 버튼 비활성화됨'); // 디버깅 로그 3
    }

    // 다운로드 버튼 영역 임시 숨김
    if (downloadSection) {
        downloadSection.style.display = 'none';
        console.log('4. 다운로드 섹션 숨김'); // 디버깅 로그 4
    }

    // 현재 스크롤 위치 저장
    const scrollPos = window.scrollY;
    console.log('5. 현재 스크롤 위치:', scrollPos); // 디버깅 로그 5

    setTimeout(() => {
        console.log('6. setTimeout 시작'); // 디버깅 로그 6
        
        // PDF 생성 전에 스타일 보존
        const analysisGrid = element.querySelectorAll('.analysis-grid');
        console.log('7. 분석 그리드 요소 수:', analysisGrid.length); // 디버깅 로그 7
        
        // ... 기존 스타일 설정 코드 ...

        console.log('8. PDF 옵션 설정 시작'); // 디버깅 로그 8
        const options = {
            margin: 10,
            filename: `면접_리포트_${getCurrentDate()}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { 
                scale: 2,
                useCORS: true,
                allowTaint: true,
                scrollY: 0,
                logging: true,
                height: Math.ceil(document.documentElement.scrollHeight * 0.80),
                windowHeight: Math.ceil(document.documentElement.scrollHeight * 0.80)
            },
            jsPDF: { 
                unit: 'mm', 
                format: 'a4', 
                orientation: 'portrait',
                compress: true,
                putOnlyUsedFonts: true,
                precision: 16
            },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };
        console.log('9. PDF 옵션:', options); // 디버깅 로그 9

        // 스타일 적용 전 상태 저장
        console.log('10. 현재 스타일 상태:', {
            transform: element.style.transform,
            width: element.style.width,
            maxWidth: element.style.maxWidth
        }); // 디버깅 로그 10

        // ... 스타일 적용 코드 ...

        console.log('11. PDF 생성 시작'); // 디버깅 로그 11
        html2pdf()
            .from(element)
            .set(options)
            .save()
            .then(() => {
                console.log('12. PDF 생성 성공'); // 디버깅 로그 12
                // 원래 스타일 복원
                document.body.style.overflow = '';
                element.style.transform = originalTransform;
                element.style.width = originalWidth;
                element.style.maxWidth = originalMaxWidth;
                
                if (downloadSection) {
                    downloadSection.style.display = '';
                }
                window.scrollTo(0, scrollPos);
                
                if (downloadButton) {
                    downloadButton.disabled = false;
                    downloadButton.textContent = 'PDF로 다운로드';
                }
                console.log('13. 모든 스타일 복원 완료'); // 디버깅 로그 13
            })
            .catch(err => {
                console.error('14. PDF 생성 실패:', err); // 디버깅 로그 14
                if (downloadSection) {
                    downloadSection.style.display = '';
                }
                if (downloadButton) {
                    downloadButton.disabled = false;
                    downloadButton.textContent = 'PDF로 다운로드';
                }
            });
    }, 1000);
};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // 날짜 표시
        updateInterviewDate();

        // URL에서 user_id 추출
        const pathParts = window.location.pathname.split('/');
        const userId = pathParts[pathParts.length - 2];

        // API 호출
        const response = await fetch(`/api/interview-report/${userId}/`);
        if (!response.ok) {
            throw new Error('Failed to fetch interview data');
        }

        const result = await response.json();
        console.log('Received data:', result); // 데이터 확인용 로그

        if (!result.data || result.data.length === 0) {
            throw new Error('No interview data found');
        }

        // 질문 카드 렌더링
const container = document.getElementById('questionContainer');
if (result.data && result.data.length > 0) {
    result.data.forEach((item, index) => {
        // 질문과 답변을 모두 표시하는 카드 생성
        container.innerHTML += `
            <div class="question-card">
                <div class="question-header">
                    <h4>Q${index + 1}. ${item.question.text}</h4>
                    <div class="total-score"></div>
                </div>
                <div class="answer-box">
                    <p class="answer-label">답변 내용</p>
                    <p class="answer-content">${item.answer ? item.answer.transcribed_text : '답변 없음'}</p>
                </div>
                <div class="analysis-container" style="display: flex; gap: 20px;">
                    <div class="metrics-section" style="flex: 1;">
                        <div class="metrics-box" style="height: 300px;">
                            <canvas id="radarChart${item.question.id}"></canvas>
                        </div>
                    </div>
                    <div class="improvement-section" style="flex: 1;">
                        <div class="improvement-box" style="margin-bottom: 5px;"> 
                            <div class="score-feedback">
                                <p class="improvement" style="margin-bottom: 5px;">💡 평가 지표 개선사항:</p> 
                                ${item.evaluation && item.evaluation.improvements ? 
                                    item.evaluation.improvements.map(imp => `<p>- ${imp}</p>`).join('') : 
                                    '<p>개선사항 없음</p>'}
                            </div>
                        </div>
                        <div class="improvement-box">
                            <div class="score-feedback">
                                <p class="improvement" style="margin-bottom: 5px;">💡비언어적 개선사항:</p>
                                ${item.evaluation && item.evaluation.nonverbal_improvements ? 
                                    item.evaluation.nonverbal_improvements.map(imp => `<p>- ${imp}</p>`).join('') : 
                                    '<p>개선사항 없음</p>'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    console.log('질문 및 답변 카드 렌더링 완료');

            try {
                // 레이더 차트 생성 시도
                result.data.forEach(data => {
                    if (data.evaluation && data.evaluation.scores) {
                        const scores = [
                            data.evaluation.scores.question_understanding,
                            data.evaluation.scores.logical_flow,
                            data.evaluation.scores.content_specificity,
                            data.evaluation.scores.problem_solving,
                            data.evaluation.scores.organizational_fit
                        ];
                        createRadarChart(data.question.id, scores);
                    }
                });

                // 전체 평균 점수 계산 및 차트 생성 시도
                const averageScores = calculateAverageScores(result.data);
                createOverallCharts(averageScores);
            } catch (chartError) {
                console.log('차트 생성 중 오류 발생 (무시됨):', chartError);
            }
        } else {
            container.innerHTML = '<div class="no-data">면접 데이터가 없습니다.</div>';
        }

        // PDF 다운로드 버튼 이벤트 리스너 추가
        console.log('이벤트 리스너 추가 시작');
        const downloadButton = document.querySelector('.download-button');
        if (downloadButton) {
            console.log('다운로드 버튼 찾음');
            downloadButton.addEventListener('click', function(e) {
                console.log('다운로드 버튼 클릭됨');
                e.preventDefault();
                window.downloadPDF();
            });
            console.log('이벤트 리스너 추가 완료');
        } else {
            console.log('다운로드 버튼을 찾을 수 없음');
        }

    } catch (error) {
        console.error('Error:', error);
        const container = document.getElementById('questionContainer');
        container.innerHTML = `<div class="error-message">데이터를 불러오는데 실패했습니다: ${error.message}</div>`;
    }
});


// 레이더 차트 생성 함수
function createRadarChart(questionId, scores) {
    const ctx = document.getElementById(`radarChart${questionId}`);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['질문이해도', '논리전개', '구체성', '문제해결', '조직적합도'],
            datasets: [{
                data: scores,
                backgroundColor: 'rgba(0, 51, 102, 0.2)',
                borderColor: '#003366',
                borderWidth: 2,
                pointBackgroundColor: '#003366',
                pointBorderColor: '#fff'
            }]
        },
        options: {
            scales: {
                r: {
                    beginAtZero: true,
                    max: 10,
                    ticks: { stepSize: 2 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// 막대 차트 생성 함수
function createBarChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: '#003366'
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

// 전체 평가 차트 생성 함수
function createOverallCharts(averageScores) {
    createBarChart('evaluationBarChart', 
        ['질문이해도', '논리전개', '구체성', '문제해결', '조직적합도'],
        Object.values(averageScores.evaluation)
    );

    createBarChart('nonverbalBarChart',
        ['말하기 속도', '발음 정확도', '말 더듬'],
        Object.values(averageScores.nonverbal)
    );
}

// 전체 평균 점수 계산 함수
function calculateAverageScores(interviewData) {
    const totals = {
        question_understanding: 0,
        logical_flow: 0,
        content_specificity: 0,
        problem_solving: 0,
        organizational_fit: 0,
        speaking_speed: 0,
        pronunciation: 0,
        stuttering: 0
    };
    
    let count = 0;
    interviewData.forEach(data => {
        const { evaluation } = data;
        if (evaluation && evaluation.scores) {
            totals.question_understanding += evaluation.scores.question_understanding || 0;
            totals.logical_flow += evaluation.scores.logical_flow || 0;
            totals.content_specificity += evaluation.scores.content_specificity || 0;
            totals.problem_solving += evaluation.scores.problem_solving || 0;
            totals.organizational_fit += evaluation.scores.organizational_fit || 0;
            totals.speaking_speed += evaluation.nonverbal_scores?.speaking_speed || 0;
            totals.pronunciation += evaluation.nonverbal_scores?.pronunciation || 0;
            totals.stuttering += evaluation.nonverbal_scores?.stuttering || 0;
            count++;
        }
    });

    return {
        evaluation: {
            question_understanding: count ? totals.question_understanding / count : 0,
            logical_flow: count ? totals.logical_flow / count : 0,
            content_specificity: count ? totals.content_specificity / count : 0,
            problem_solving: count ? totals.problem_solving / count : 0,
            organizational_fit: count ? totals.organizational_fit / count : 0
        },
        nonverbal: {
            speaking_speed: count ? totals.speaking_speed / count : 0,
            pronunciation: count ? totals.pronunciation / count : 0,
            stuttering: count ? totals.stuttering / count : 0
        }
    };
}

// 총점 계산 함수
function calculateTotalScore(scores) {
    return Math.round(scores.reduce((sum, score) => sum + score, 0));
}

// 현재 날짜 표시 함수
function updateInterviewDate() {
    const dateElement = document.querySelector('.interview-date');
    if (dateElement) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        dateElement.innerHTML = `<strong>면접 일시:</strong> ${year}년 ${month}월 ${day}일`;
    }
}

// 현재 날짜를 YYYYMMDD 형식으로 반환하는 함수
function getCurrentDate() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
}