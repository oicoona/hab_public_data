"""
Prompt templates for AI chatbot.

v1.2.3: 프롬프트 모듈화
- 모든 시스템 프롬프트를 이 파일에서 관리
- 각 프롬프트별 용도와 사용처 문서화
"""

# ============================================================================
# 메인 시스템 프롬프트
# 사용처: chatbot.py - LangGraph 챗봇의 기본 시스템 프롬프트
# ============================================================================

SYSTEM_PROMPT_BASE = """당신은 데이터 분석 전문가입니다. 사용자가 업로드한 CSV 데이터셋에 대한 질문에 답변합니다.

핵심 역할:
- 데이터의 구조, 통계, 패턴에 대해 명확하게 설명
- 분석 인사이트와 해석 제공
- 추가 탐색 방향 제안

답변 가이드라인:
1. 한국어로 친절하게 답변
2. 데이터에 기반한 정확한 정보만 제공
3. 불확실한 경우 그 점을 명시
4. 기술적 용어는 쉽게 설명
5. 가능하면 구체적인 수치 포함

주의사항:
- 데이터에 없는 정보는 추측하지 않음
- 개인정보 보호 관련 민감 데이터 언급 자제
- 시각화 코드 요청 시 Plotly 기반 예시 제공

중요: 데이터 분석 질문에 답변할 때는 제공된 도구(tools)를 사용하여 정확한 정보를 얻으세요.
데이터와 관련 없는 일반 질문에는 도구 없이 직접 답변해도 됩니다."""


# ============================================================================
# ECLO 예측 프롬프트
# 사용처: chatbot.py - SYSTEM_PROMPT에 결합되어 ECLO 예측 기능 안내
# ============================================================================

ECLO_PREDICTION_PROMPT = """
## ECLO 예측 기능 (v1.2.3)

사용자가 교통사고 ECLO(사고 심각도) 예측을 요청하면, **어떤 데이터셋이 활성화되어 있든** predict_eclo 도구를 사용할 수 있습니다.
단일 건 또는 여러 건의 사고 데이터를 동시에 예측할 수 있습니다.

### ECLO 예측 요청 감지
다음과 같은 표현이 나오면 ECLO 예측 의도로 판단하세요:
- "ECLO 예측해줘", "사고 심각도 예측", "ECLO 값 알려줘"
- 날짜, 시간, 장소, 기상 조건 등 사고 정보와 함께 "예측" 언급
- "여러 건", "다음 사고들", "N개 사고" 등 배치 예측 요청

### 필수 피처 11개
ECLO 예측에는 다음 11개 정보가 필요합니다:
1. weather (기상상태): 맑음, 흐림, 비, 눈, 안개, 기타
2. road_surface (노면상태): 건조, 젖음/습기, 적설, 서리/결빙, 침수, 기타
3. road_type (도로형태): 교차로 - 교차로안, 교차로 - 교차로부근, 교차로 - 교차로횡단보도내, 단일로 - 기타, 단일로 - 터널, 단일로 - 교량, 단일로 - 고가도로위, 단일로 - 지하차도(도로)내, 주차장 - 주차장, 기타 - 기타
4. accident_type (사고유형): 차대차, 차대사람, 차량단독
5. time_period (시간대): 심야, 출근시간대, 일반시간대, 퇴근시간대
6. district (시군구): 대구광역시 내 상세 주소 (예: 대구광역시 수성구 상동, 대구광역시 중구 동성로1가)
7. day_of_week (요일): 월요일, 화요일, 수요일, 목요일, 금요일, 토요일, 일요일
8. accident_hour (사고시): 0-23
9. accident_year (사고연): 연도 (예: 2022)
10. accident_month (사고월): 1-12
11. accident_day (사고일): 1-31

### 재질문 규칙
사용자가 일부 정보만 제공한 경우:
1. 제공된 정보를 파싱하여 확인
2. 누락된 피처를 친절하게 질문
3. 모든 피처가 수집되면 predict_eclo 도구 호출

예시:
- 사용자: "2022-01-01 토요일 맑음 대구 수성구 상동 교차로 건조 차대사람 ECLO 예측해줘"
- AI: "ECLO 예측을 위해 몇 가지 추가 정보가 필요합니다:
  - 사고 시간(시)은 몇 시인가요? (0-23)
  - 시간대는 어떻게 되나요? (심야/출근시간대/일반시간대/퇴근시간대)
  - 도로형태를 더 구체적으로 알려주세요 (예: 교차로 - 교차로안)"

### 시간대 매핑 힌트
- 심야: 00시~06시경 (새벽)
- 출근시간대: 07시~09시경
- 일반시간대: 10시~17시경 (낮)
- 퇴근시간대: 18시~21시경

### 배치 예측 (v1.2.3)
여러 건의 사고를 동시에 예측할 때:
1. 각 사고별로 11개 피처 수집
2. 누락된 정보가 있으면 해당 사고 번호와 함께 재질문
3. predict_eclo_batch 도구로 일괄 예측
4. 결과를 테이블 형태로 정리하여 제공"""


# ============================================================================
# 결합된 시스템 프롬프트
# 사용처: chatbot.py - 실제 LLM에 전달되는 최종 프롬프트
# ============================================================================

SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + ECLO_PREDICTION_PROMPT


# ============================================================================
# 도구 설명 (Tool Descriptions)
# 사용처: tools.py - 각 도구의 docstring 참조용
# README.md - 도구 목록 문서화용
# ============================================================================

TOOL_DESCRIPTIONS = {
    # 데이터 정보 도구
    "get_dataframe_info": {
        "category": "데이터 정보",
        "description": "데이터프레임의 기본 정보 (행/열 수, 컬럼 타입, 메모리 사용량)",
        "params": ["없음 (현재 활성 데이터셋 사용)"],
    },
    "get_column_statistics": {
        "category": "데이터 정보",
        "description": "특정 컬럼의 기초 통계량 (평균, 중앙값, 표준편차 등)",
        "params": ["column: 분석할 컬럼명"],
    },
    "get_missing_values": {
        "category": "데이터 정보",
        "description": "각 컬럼별 결측값 개수와 비율",
        "params": ["없음"],
    },
    "get_value_counts": {
        "category": "데이터 정보",
        "description": "특정 컬럼의 값 빈도수 계산",
        "params": ["column: 분석할 컬럼명", "top_n: 상위 N개 (기본값 10)"],
    },

    # 데이터 조작 도구
    "filter_dataframe": {
        "category": "데이터 조작",
        "description": "조건에 맞는 행 필터링",
        "params": ["column: 필터링 컬럼", "operator: 연산자 (==, !=, >, <, >=, <=, contains)", "value: 비교값"],
    },
    "sort_dataframe": {
        "category": "데이터 조작",
        "description": "특정 컬럼 기준 정렬",
        "params": ["column: 정렬 기준 컬럼", "ascending: 오름차순 여부 (기본값 True)"],
    },
    "get_unique_values": {
        "category": "데이터 조작",
        "description": "특정 컬럼의 고유값 목록",
        "params": ["column: 컬럼명"],
    },
    "get_sample_rows": {
        "category": "데이터 조작",
        "description": "데이터프레임에서 샘플 행 추출",
        "params": ["n: 샘플 개수 (기본값 5)", "random: 랜덤 샘플 여부"],
    },

    # 통계 분석 도구
    "get_correlation": {
        "category": "통계 분석",
        "description": "두 숫자 컬럼 간의 상관계수 계산",
        "params": ["column1: 첫 번째 컬럼", "column2: 두 번째 컬럼"],
    },
    "group_by_aggregate": {
        "category": "통계 분석",
        "description": "그룹별 집계 연산 (합계, 평균, 개수 등)",
        "params": ["group_column: 그룹화 컬럼", "agg_column: 집계 대상 컬럼", "agg_func: 집계 함수"],
    },
    "calculate_percentile": {
        "category": "통계 분석",
        "description": "특정 컬럼의 백분위수 계산",
        "params": ["column: 컬럼명", "percentile: 백분위 (0-100)"],
    },
    "get_outliers": {
        "category": "통계 분석",
        "description": "IQR 방식으로 이상치 탐지",
        "params": ["column: 분석할 컬럼명"],
    },
    "cross_tabulation": {
        "category": "통계 분석",
        "description": "두 범주형 컬럼의 교차표 생성",
        "params": ["column1: 행 컬럼", "column2: 열 컬럼"],
    },
    "get_column_correlation_with_target": {
        "category": "통계 분석",
        "description": "타겟 컬럼과 모든 숫자 컬럼의 상관관계",
        "params": ["target_column: 타겟 컬럼명"],
    },

    # 시계열 분석 도구
    "get_date_range": {
        "category": "시계열",
        "description": "날짜 컬럼의 최소/최대 범위",
        "params": ["date_column: 날짜 컬럼명"],
    },
    "get_temporal_pattern": {
        "category": "시계열",
        "description": "시간대별 패턴 분석 (시간, 요일, 월별)",
        "params": ["date_column: 날짜 컬럼", "value_column: 값 컬럼", "period: 기간 단위"],
    },

    # 지리 분석 도구
    "get_geo_bounds": {
        "category": "지리",
        "description": "위경도 컬럼의 경계값 (최소/최대 좌표)",
        "params": ["lat_column: 위도 컬럼", "lng_column: 경도 컬럼"],
    },

    # 데이터 품질 도구
    "analyze_missing_pattern": {
        "category": "데이터 품질",
        "description": "결측값 패턴 분석",
        "params": ["없음"],
    },
    "detect_data_types": {
        "category": "데이터 품질",
        "description": "각 컬럼의 실제 데이터 타입 감지",
        "params": ["없음"],
    },
    "summarize_categorical_distribution": {
        "category": "데이터 품질",
        "description": "범주형 컬럼의 분포 요약",
        "params": ["column: 분석할 컬럼명"],
    },

    # ECLO 예측 도구
    "predict_eclo": {
        "category": "예측",
        "description": "단일 사고 데이터의 ECLO(사고 심각도) 예측",
        "params": [
            "weather: 기상상태",
            "road_surface: 노면상태",
            "road_type: 도로형태",
            "accident_type: 사고유형",
            "time_period: 시간대",
            "district: 시군구",
            "day_of_week: 요일",
            "accident_hour: 사고시 (0-23)",
            "accident_year: 사고연",
            "accident_month: 사고월 (1-12)",
            "accident_day: 사고일 (1-31)",
        ],
    },
    "predict_eclo_batch": {
        "category": "예측",
        "description": "여러 사고 데이터의 ECLO 일괄 예측 (v1.2.3)",
        "params": ["accidents: 사고 정보 리스트 (각 항목은 11개 피처 포함)"],
    },
}


def get_tool_list_markdown() -> str:
    """
    README.md용 도구 목록 마크다운 생성.

    Returns:
        str: 마크다운 형식의 도구 목록
    """
    categories = {}
    for tool_name, info in TOOL_DESCRIPTIONS.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((tool_name, info))

    lines = []
    for category, tools in categories.items():
        lines.append(f"\n#### {category}\n")
        lines.append("| 도구명 | 설명 | 파라미터 |")
        lines.append("|:-------|:-----|:---------|")
        for tool_name, info in tools:
            params = ", ".join(info["params"]) if info["params"] else "없음"
            lines.append(f"| `{tool_name}` | {info['description']} | {params} |")

    return "\n".join(lines)
