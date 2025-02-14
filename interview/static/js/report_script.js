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

// 피드백 데이터 객체 정의
const feedbackData = {
    '질문 이해도': {
        best: {
            points: [
                '질문 의도를 정확히 파악하고 핵심을 짚어 답변함',
                '논리적이고 명확한 구조로 답변하여 면접관이 이해하기 쉬움'
            ],
            improvement: '다양한 질문 유형에 대해서도 같은 수준의 이해도를 유지하면 더욱 좋을 것 같습니다.'
        },
        worst: {
            points: [
                '질문의 핵심을 놓치거나 본질과 다른 답변을 함',
                '면접관이 의도한 질문에 대한 정확한 이해가 부족함'
            ],
            improvement: '질문을 다시 정리하고 핵심을 파악하는 연습을 하면 더욱 좋을 것 같습니다.'
        }
    },
    '논리적 전개': {
        best: {
            points: [
                '답변이 논리적이고 체계적으로 구성됨',
                '주장과 근거가 명확하게 연결되어 있어 설득력이 높음'
            ],
            improvement: '다양한 사례와 경험을 조금 더 구체적으로 덧붙이면 더욱 강한 인상을 줄 수 있을 것 같습니다.'
        },
        worst: {
            points: [
                '답변이 두서없이 전개되어 논리적인 흐름이 부족함',
                '근거가 부족하거나 주장이 명확하지 않음'
            ],
            improvement: 'STAR 기법(상황-과제-행동-결과) 등을 활용하여 답변을 구조적으로 정리하는 연습이 필요합니다.'
        }
    },
    '내용의 구체성': {
        best: {
            points: [
                '답변이 구체적인 사례를 바탕으로 이루어져 신뢰도가 높음',
                '단순한 원론적인 답변이 아니라 실제 경험과 연결됨'
            ],
            improvement: '핵심 경험을 더욱 강조하고, 직무와 연결 짓는다면 더욱 강한 인상을 줄 수 있을 것 같습니다.'
        },
        worst: {
            points: [
                '답변이 추상적이고 일반적인 내용으로 구성됨',
                '직무와 관련된 구체적인 사례가 부족함'
            ],
            improvement: '자신의 경험을 구체적인 사례와 수치로 표현하는 연습을 하면 더욱 좋을 것 같습니다.'
        }
    },
    '문제 해결 접근': {
        best: {
            points: [
                '문제 해결 과정이 체계적으로 정리되어 있고, 논리적인 사고를 바탕으로 해결책을 제시함',
                '창의적인 접근 방식이 돋보이며, 실무 적용 가능성이 높음'
            ],
            improvement: '문제 해결 과정에서 직무와 관련된 도전적인 과제나 차별화된 접근 방식을 강조하면 더욱 좋을 것 같습니다.'
        },
        worst: {
            points: [
                '문제 해결 과정이 명확하지 않거나, 효과적인 해결책을 제시하지 못함',
                '문제를 분석하는 과정이 부족하거나, 해결책이 비현실적임'
            ],
            improvement: '문제 해결 과정을 단계별로 정리하고, 기존의 경험을 활용하여 해결책을 제시하는 연습이 필요합니다.'
        }
    },
    '말 더듬': {
        best: {
            points: [
                '답변을 빠르고 자연스럽게 이어나가며, 중간에 막힘이 거의 없음',
                '자신감 있는 태도로 논리적인 흐름을 유지함'
            ],
            improvement: '차분하면서도 강약 조절을 하면 더욱 안정적인 전달력이 생길 것 같습니다.'
        },
        worst: {
            points: [
                '답변 중간에 \'음…\', \'어…\' 같은 불필요한 망설임이 많음',
                '답변을 생각하는 시간이 길어져 면접관에게 불안한 인상을 줄 가능성이 있음'
            ],
            improvement: '예상 질문 리스트를 준비하고, 반복 연습을 통해 자연스럽게 답변하는 연습을 하면 좋겠습니다.'
        }
    },
    '말하기 속도': {
        best: {
            points: [
                '적절한 속도로 말하여 청취자가 이해하기 쉬움',
                '강조할 부분에서 속도를 조절하여 전달력을 높임'
            ],
            improvement: '중요 부분에서 살짝 더 천천히 말하며 포인트를 강조하면 더욱 효과적인 전달이 가능합니다.'
        },
        worst: {
            points: [
                '말이 너무 빠르거나 너무 느려서 듣는 사람이 집중하기 어려움',
                '긴장으로 인해 빨라지거나, 생각하며 말하면서 지나치게 느려지는 경향이 있음'
            ],
            improvement: '녹음해서 스스로 말하는 속도를 체크하고, 청취자가 이해하기 좋은 속도를 연습하면 도움이 됩니다.'
        }
    },
    '발음 정확도': {
        best: {
            points: [
                '발음이 또렷하고 정확하여 듣는 사람이 이해하기 쉬움',
                '조음이 명확하고, 문장의 흐름이 자연스러움'
            ],
            improvement: '적절한 억양을 추가하여 전달력을 더욱 높이면 좋을 것 같습니다.'
        },
        worst: {
            points: [
                '발음이 부정확하여 일부 단어나 문장이 잘 들리지 않음',
                '끝맺음이 흐려지거나, 일부 단어를 뭉개어 발음하는 경향이 있음'
            ],
            improvement: '문장을 또박또박 읽는 연습을 하면서 정확한 발음에 신경 쓰는 것이 중요합니다.'
        }
    },
    '조직 적합도': {
        best : {
            points : [
                '조직 문화와 가치관을 잘 이해하고, 본인의 경험과 연결하여 설득력 있게 설명함',
                '협업 경험이 풍부하고, 팀워크에서의 역할을 명확하게 제시함'
        ],
        improvement: '회사의 장기적인 목표와 본인의 성장 방향을 더욱 구체적으로 연결하면 더욱 강한 인상을 줄 수 있을 것 같습니다.'
        },
        worst: {
            points: [
                '회사의 조직 문화나 핵심 가치에 대한 이해가 부족해 보임',
                '협업 경험이 부족하거나, 조직 내에서의 역할을 명확하게 설명하지 못함'
            ],
            improvement: '지원하는 회사의 핵심 가치와 문화를 사전에 파악하고, 본인의 경험과 연결하여 설명하는 연습이 필요합니다.'
        }

    }
    // 다른 평가 지표들에 대한 피드백도 추가 가능
};

// 평균 점수 계산 및 총괄 평가 업데이트 함수
function updateOverallEvaluation(questions) {
    // 평가 지표별 평균 점수 계산
    const totalScores = {
        '질문 이해도': 0,
        '논리적 전개': 0,
        '내용의 구체성': 0,
        '문제 해결 접근': 0,
        '조직 적합도': 0
    };
    
    let questionCount = 0;
    
    questions.forEach(item => {
        if (item.evaluation?.scores) {
            totalScores['질문 이해도'] += item.evaluation.scores.question_understanding || 0;
            totalScores['논리적 전개'] += item.evaluation.scores.logical_flow || 0;
            totalScores['내용의 구체성'] += item.evaluation.scores.content_specificity || 0;
            totalScores['문제 해결 접근'] += item.evaluation.scores.problem_solving || 0;
            totalScores['조직 적합도'] += item.evaluation.scores.organizational_fit || 0;
            questionCount++;
        }
    });

    // 평균 계산
    const averageScores = {};
    Object.keys(totalScores).forEach(key => {
        averageScores[key] = questionCount > 0 ? 
            Math.round((totalScores[key] / questionCount) * 10) / 10 : 0;
    });

    // 막대 그래프 생성
    const ctx = document.getElementById('evaluationBarChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(averageScores),
                datasets: [{
                    data: Object.values(averageScores),
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

    // 강점과 약점 찾기
    let maxScore = -1;
    let minScore = Infinity;
    let maxCategory = '';
    let minCategory = '';
    
    Object.entries(averageScores).forEach(([category, score]) => {
        if (score > maxScore) {
            maxScore = score;
            maxCategory = category;
        }
        if (score < minScore) {
            minScore = score;
            minCategory = category;
        }
    });

    // 강점 피드백 업데이트
    const bestScoreSection = document.querySelector('.best-score');
    if (bestScoreSection) {
        const scoreItem = bestScoreSection.querySelector('.score-item');
        scoreItem.querySelector('.score-label').textContent = maxCategory;
        scoreItem.querySelector('.score-fill').style.width = `${maxScore * 10}%`;
        scoreItem.querySelector('.score-value').textContent = `${maxScore}/10`;

        const feedbackDiv = bestScoreSection.querySelector('.score-feedback');
        const bestFeedback = feedbackData[maxCategory]?.best;
        if (bestFeedback) {
            feedbackDiv.innerHTML = `
                ${bestFeedback.points.map(point => `<p>✓ ${point}</p>`).join('')}
                <p class="improvement">💡 ${bestFeedback.improvement}</p>
            `;
        }
    }

    // 약점 피드백 업데이트
    const worstScoreSection = document.querySelector('.worst-score');
    if (worstScoreSection) {
        const scoreItem = worstScoreSection.querySelector('.score-item');
        scoreItem.querySelector('.score-label').textContent = minCategory;
        scoreItem.querySelector('.score-fill').style.width = `${minScore * 10}%`;
        scoreItem.querySelector('.score-value').textContent = `${minScore}/10`;

        const feedbackDiv = worstScoreSection.querySelector('.score-feedback');
        const worstFeedback = feedbackData[minCategory]?.worst;
        if (worstFeedback) {
            feedbackDiv.innerHTML = `
                ${worstFeedback.points.map(point => `<p>✗ ${point}</p>`).join('')}
                <p class="improvement">💡 ${worstFeedback.improvement}</p>
            `;
        }
    }
}

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
        console.log('Received data:', result);

        if (!result.data || !result.data.questions || result.data.questions.length === 0) {
            throw new Error('No interview data found');
        }

        const questions = result.data.questions;  // 실제 질문 데이터 배열

        // 질문 카드 렌더링
        const container = document.getElementById('questionContainer');
        questions.forEach((item, index) => {
            container.innerHTML += `
                <div class="question-card">
                    <div class="question-header">
                        <h4>Q${index + 1}. ${item.question_text}</h4>
                        <div class="total-score">${item.evaluation?.total_score || '점수 없음'}/50</div>
                    </div>
                    <div class="answer-box">
                        <p class="answer-label">답변 내용</p>
                        <p class="answer-content">${item.answer?.transcribed_text || '답변 없음'}</p>
                    </div>
                    <div class="analysis-container" style="display: flex; gap: 20px;">
                        <div class="metrics-section" style="flex: 1;">
                            <div class="metrics-box" style="height: 300px;">
                                ${item.evaluation?.scores ? 
                                    `<canvas id="radarChart${index}"></canvas>` : 
                                    '<p>평가 데이터가 없습니다.</p>'}
                            </div>
                        </div>
                        <div class="improvement-section" style="flex: 1;">
                            <div class="improvement-box" style="margin-bottom: 5px;"> 
                                <div class="score-feedback">
                                    <p class="improvement" style="margin-bottom: 5px;">💡 평가 지표 개선사항:</p> 
                                    ${item.evaluation?.improvements ? 
                                        item.evaluation.improvements.map(imp => `<p>- ${imp}</p>`).join('') : 
                                        '<p>개선사항 없음</p>'}
                                </div>
                            </div>
                            ${item.evaluation?.nonverbal_improvements ? `
                            <div class="improvement-box">
                                <div class="score-feedback">
                                    <p class="improvement" style="margin-bottom: 5px;">💡비언어적 개선사항:</p>
                                    ${item.evaluation.nonverbal_improvements.length > 0 ? 
                                        item.evaluation.nonverbal_improvements.map(imp => `<p>- ${imp}</p>`).join('') : 
                                        '<p>개선사항 없음</p>'}
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });

        // 레이더 차트 생성
        questions.forEach((item, index) => {
            if (item.evaluation?.scores) {
                const scores = [
                    item.evaluation.scores.question_understanding || 0,
                    item.evaluation.scores.logical_flow || 0,
                    item.evaluation.scores.content_specificity || 0,
                    item.evaluation.scores.problem_solving || 0,
                    item.evaluation.scores.organizational_fit || 0
                ];
                createRadarChart(`radarChart${index}`, scores);
            }
        });

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

        // 총괄 평가 업데이트
        updateOverallEvaluation(result.data.questions);

    } catch (error) {
        console.error('Error:', error);
        const container = document.getElementById('questionContainer');
        container.innerHTML = `<div class="error-message">데이터를 불러오는데 실패했습니다: ${error.message}</div>`;
    }
});

// 레이더 차트 생성 함수
function createRadarChart(questionId, scores) {
    const ctx = document.getElementById(questionId);
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