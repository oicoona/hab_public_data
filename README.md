# 대구 공공데이터 시각화

대구 지역 공공데이터를 탐색·분석하는 교육용 Streamlit 애플리케이션입니다.

데이터 출처: [DACON 대구 교통사고 피해 예측 AI 경진대회](https://dacon.io/competitions/official/236193/overview/description)

---

## 빠른 시작

### uv 사용 (권장)

```bash
# 1. uv 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 의존성 설치 및 앱 실행
uv run streamlit run app.py
```

### pip 사용 (기존 방식)

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 앱 실행
streamlit run app.py
```

---

## 버전 히스토리

### v1.2.5 (현재)

**시계열 분석 및 다중 데이터셋 분석** - 날짜 컬럼 자동 변환, 체크박스 기반 다중 선택

#### 주요 변경사항

| 영역 | v1.2.4 | v1.2.5 |
|:-----|:-------|:-------|
| **날짜 컬럼 처리** | 문자열(object) 타입 | datetime64 자동 변환 ✅ |
| **데이터셋 선택** | selectbox (단일 선택) | checkbox (다중 선택) ✅ |
| **분석 범위** | 1개 데이터셋만 분석 | 여러 데이터셋 동시 분석 ✅ |
| **채팅 세션** | 데이터셋별 단일 세션 | 선택 조합별 독립 세션 ✅ |

#### 개선 사항 (완료)

- **시계열 데이터 처리**: 날짜 컬럼(`설치연도`, `사고일시`) 자동 datetime 변환
  - 영향 데이터셋: CCTV, 보안등, 사고, train, test
  - `utils/loader.py`에서 `pd.to_datetime()` 자동 적용
  - 시계열 분석 도구 정상 동작

- **다중 데이터셋 선택**: selectbox → checkbox 전환으로 여러 데이터셋 동시 선택
  - 3열 그리드 레이아웃으로 UI 개선
  - 선택된 데이터셋 요약 표시
  - 상관/연관 분석 가능 (예: "CCTV와 사고 데이터의 상관관계는?")

- **다중 데이터 컨텍스트**: 선택된 모든 데이터셋 정보를 AI에게 전달
  - 데이터셋별 컨텍스트 캐싱 유지
  - 다중 컨텍스트 동적 병합

- **세션 관리 개선**: 선택 조합별 대화 내역 분리
  - 세션 키: `{dataset1}_{dataset2}_...` (정렬)
  - 조합별 독립적인 채팅 이력 관리

#### 기술 세부사항

**날짜 컬럼 매핑** (`utils/loader.py`):
```python
date_columns = {
    'cctv': ['설치연도'],
    'lights': ['설치연도'],
    'accident': ['사고일시'],
    'train': ['사고일시'],
    'test': ['사고일시']
}
```

**UI 개선** (`app.py`):
- 데이터셋 선택: 3열 체크박스 그리드
- 선택 확인: 아이콘 + 이름 표시
- 요약 정보: 선택된 데이터셋별 메트릭 (행/컬럼/결측률)

기준 문서: `docs/v1.2.5/note.md`, `docs/v1.2.5/app_improvement_proposal.md`

---

### v1.2.4

**환경 설정 자동화** - .env 지원, 데이터셋 요약 확대

#### 주요 변경사항

| 영역 | v1.2.3 | v1.2.4 |
|:-----|:-------|:-------|
| **환경 변수** | 수동 입력 only | `.env` 파일 자동 로드 (CLAUDE_API_KEY) ✅ |
| **데이터셋 요약** | 3개 행 표시 | 10개 행 표시 ✅ |
| **지도 상태 관리** | 개별 키 방식 | `map_cache` 딕셔너리 통합 (미수정) |
| **질의응답 UI** | 기본 레이아웃 | 컨테이너 구분 (미수정) |

#### 개선 사항 (완료)

- **환경 변수 자동 로드**: `.env` 파일에서 `CLAUDE_API_KEY` 자동 감지 및 적용
  - 우선순위: `.env` → Streamlit secrets → 사용자 입력
  - `python-dotenv` 패키지 추가
  - `ANTHROPIC_API_KEY` → `CLAUDE_API_KEY`로 변경
- **데이터셋 요약 확대**: 질의응답 탭에서 표시 행수 3개 → 10개로 변경

#### 기술 스택 추가

- `python-dotenv>=1.0.0` (환경 변수 관리)

#### 향후 개선 예정

- 지도 상태 유지: 데이터셋별 지도를 독립적으로 관리하여 탭 전환 시 유지
- 질의응답 UI: 대화 내역 컨테이너 명확히 구분, 빈 상태 안내 추가

기준 문서: `docs/v1.2.4/note.md`, `docs/app_improvement_proposal.md`

---

### v1.2.3

**코드 품질 개선 및 배치 예측** - 프롬프트 모듈화, 배치 ECLO 예측 지원

#### 주요 변경사항

| 영역 | v1.2.2 | v1.2.3 |
|:-----|:-------|:-------|
| **프롬프트 관리** | chatbot.py 내 하드코딩 | `utils/prompts.py` 분리 |
| **ECLO 예측** | 단일 건만 가능 | 배치 예측 지원 (N건 동시) |
| **도구 개수** | 21개 | 22개 (+predict_eclo_batch) |
| **코드 품질** | 미사용 import 존재 | 불필요한 코드 정리 |

#### 신규 파일

| 파일 | 설명 |
|:-----|:-----|
| `utils/prompts.py` | 시스템 프롬프트 모듈 (SYSTEM_PROMPT, ECLO_PREDICTION_PROMPT, TOOL_DESCRIPTIONS) |

#### 신규 도구

| 도구 | 설명 |
|:-----|:-----|
| `predict_eclo_batch` | 여러 사고 데이터의 ECLO 일괄 예측 |

#### 개선 사항

- 프롬프트를 `utils/prompts.py`로 분리하여 관리 용이성 향상
- `utils/chatbot.py`에서 미사용 import 제거 (AsyncGenerator, SystemMessage)
- `app.py`에서 미사용 import 제거 (SYSTEM_PROMPT, create_chat_response 등)
- `utils/predictor.py`에 배치 예측 함수 추가

기준 문서: `docs/v1.2.3/app_improvement_proposal.md`

---

### v1.2.2

**ECLO 예측 독립화** - 데이터셋에 관계없이 ECLO 예측 가능

#### 주요 변경사항

| 영역 | v1.2.1 | v1.2.2 |
|:-----|:-------|:-------|
| **ECLO 예측** | train/test 데이터셋 필수 | 모든 데이터셋에서 사용 가능 |
| **사용자 경험** | 피처 누락 시 오류 | 자연어 재질문으로 정보 수집 |
| **의존성** | - | scikit-learn, lightgbm 추가 |

#### 개선 사항

- ECLO 예측 도구에서 데이터셋 조건 검증 제거
- 시스템 프롬프트에 ECLO 예측 재질문 로직 추가
- 유효값 목록을 실제 인코더 값으로 업데이트

기준 문서: `docs/v1.2.2/app_improvement_proposal.md`

---

### v1.2.1

**환경 개선 및 버그 수정** - uv 패키지 매니저 전환, API Key 검증 수정

#### 주요 변경사항

| 영역 | v1.2 | v1.2.1 |
|:-----|:-----|:-------|
| **패키지 관리** | `requirements.txt` only | `pyproject.toml` + uv 지원 |
| **API Key 검증** | `sk-ant-` 형식만 허용 | `sk-` 형식 모두 허용 |
| **Streamlit 컴포넌트** | `use_container_width` (deprecated) | `width='stretch'` |

기준 문서: `docs/v1.2.1/app_improvement_proposal.md`

---

### v1.2

**LangGraph 마이그레이션** - LangGraph 기반 Tool Calling 아키텍처로 전환

#### 주요 변경사항

| 영역 | v1.1.x | v1.2 |
|:-----|:-------|:-----|
| **Tool Calling 아키텍처** | Anthropic API 직접 사용 | LangGraph StateGraph 기반 |
| **워크플로우** | 동기 Tool 실행 | 조건부 라우팅 기반 비동기 처리 |
| **분석 도구** | 20개 | 21개 (+ECLO 예측) |
| **패키지 매니저** | pip only | uv 지원 추가 |

#### 신규 기능

- **ECLO 예측 도구**: LightGBM 모델 기반 사고 심각도 예측
- **LangGraph 워크플로우**: chatbot-tools 조건부 라우팅
- **버전 히스토리 UI**: 프로젝트 개요 탭에 버전 히스토리 표시
- **아키텍처 시각화**: LangGraph 워크플로우 다이어그램 및 21개 도구 목록

#### 기술 스택 추가

- `langchain>=0.3.0`
- `langchain-anthropic>=0.3.0`
- `langgraph>=0.2.0`

#### 새로운 모듈

| 모듈 | 설명 |
|:-----|:-----|
| `utils/graph.py` | LangGraph StateGraph 정의 (ChatState, route_tools, build_graph) |
| `utils/predictor.py` | ECLO 예측 모듈 (LightGBM 모델 로드, 피처 인코딩) |

기준 문서: `docs/v1.2/app_improvement_proposal.md`
스펙 문서: `specs/004-app-v12-upgrade/`

---

### v1.1.3

**UI 간소화 및 버그 수정** - Tool Calling 피드백 위치 수정, 탭 구조 단순화

#### 주요 변경사항

| 영역 | v1.1.2 | v1.1.3 |
|:-----|:-------|:-------|
| **Tool Calling 피드백** | 응답 텍스트 위에 표시 (밀림 현상) | 응답 완료 후 expander로 요약 표시 |
| **프로젝트 개요 탭** | 소개 + 업로드 + 교육 콘텐츠 | 소개 + 업로드 + 기술 스택만 유지 |
| **탭 개수** | 10개 | 9개 (교차 데이터 분석 탭 삭제) |
| **지도 설정** | 없음 | 사이드바에서 최대 포인트 수 설정 |

#### 삭제된 섹션 (프로젝트 개요 탭)

- 주요 기능
- 사용 방법
- 시스템 구조
- 데이터 분석 기초 개념 (6개 expander)
- 분석 가이드 질문
- 교차 데이터 분석의 중요성

#### 신규 기능

- **지도 설정**: 사이드바에서 최대 표시 포인트 수 설정 (기본값: 5000)
- **지도 활성화 조건**: Enter 키 또는 적용 버튼으로 설정 확정 필요

#### 버그 수정

- Tool Calling 피드백 위치 오류 수정 (응답이 상태값을 밀어내는 현상)

기준 문서: `docs/v1.1.3/app_improvement_proposal.md`

---

### v1.1.2

**사용자 경험 개선** - Tool Calling UX 고도화 및 분석 도구 확장

#### 주요 변경사항

| 영역 | v1.1.1 | v1.1.2 |
|:-----|:-------|:-------|
| **Tool Calling 피드백** | "도구 실행 중..." 단순 텍스트 | st.status로 도구명, 순번, 경과시간 표시 |
| **토큰 사용량** | 표시만 됨 (업데이트 안됨) | API 응답에서 실시간 추출하여 표시 |
| **도구 미발견 처리** | 정적 에러 메시지 | LLM 폴백으로 동적 응답 생성 |
| **분석 도구** | 15개 | 20개 (+5개 추가) |
| **데이터셋 전환** | 매번 컨텍스트 재생성 | 컨텍스트 캐싱으로 속도 향상 |

#### 추가된 분석 도구 (5개)

| 도구 | 설명 |
|:-----|:-----|
| `analyze_missing_pattern` | 결측값 패턴 분석 (MCAR, MAR, MNAR 추정) |
| `get_column_correlation_with_target` | 타겟 컬럼과의 상관관계 분석 |
| `detect_data_types` | 컬럼별 실제 데이터 타입 추론 |
| `get_temporal_pattern` | 시간 관련 컬럼의 패턴 분석 |
| `summarize_categorical_distribution` | 범주형 컬럼 분포 요약 |

#### 버그 수정

- 토큰 사용량 미업데이트 수정 (API 응답에서 usage 추출)
- Claude Haiku 4.5 모델 ID 수정 (`20250901` → `20251001`)

기준 문서: `docs/v1.1.2/app_improvement_proposal.md`

---

### v1.1.1

**AI 분석 고도화** - Tool Calling 도입 및 성능 최적화

#### 주요 변경사항

| 영역 | v1.1 | v1.1.1 |
|:-----|:-----|:-------|
| **AI 모델** | Claude 4 시리즈 | Claude 4.5 시리즈 (Sonnet, Opus, Haiku) |
| **챗봇 분석** | 샘플링 데이터 기반 | Tool Calling (15개 분석 도구) |
| **대화 컨텍스트** | 전체 통합 이력 | 데이터셋별 분리 관리 |
| **응답 출력** | 전체 완료 후 표시 | 스트리밍 실시간 출력 |
| **지도 렌더링** | 매번 새로 생성 | session_state 캐싱 |
| **교차 분석** | 통합 지도 포함 | 제거 (단순화) |

#### Tool Calling 분석 도구 (15개)

| 도구 | 설명 |
|:-----|:-----|
| `get_dataframe_info` | DataFrame 기본 정보 |
| `get_column_statistics` | 컬럼별 통계 |
| `get_missing_values` | 결측치 현황 |
| `get_value_counts` | 값 분포 |
| `filter_dataframe` | 조건 필터링 |
| `sort_dataframe` | 정렬 |
| `get_correlation` | 상관관계 |
| `group_by_aggregate` | 그룹별 집계 |
| `get_unique_values` | 고유값 목록 |
| `get_date_range` | 날짜 범위 |
| `get_outliers` | 이상치 탐지 |
| `get_sample_rows` | 샘플 추출 |
| `calculate_percentile` | 백분위수 |
| `get_geo_bounds` | 지리적 범위 |
| `cross_tabulation` | 교차표 |

#### 버그 수정

- ZeroDivisionError 방지 (빈 DataFrame 처리)
- NaN 값 안전한 포맷팅 처리
- 빈 좌표 데이터 지도 렌더링 오류 수정

#### 성능 개선

- `iterrows` → `itertuples` 변환
- 지도 객체 캐싱 (`session_state`)
- `st_folium` 리렌더링 방지 (`returned_objects=[]`)

기준 문서: `docs/v1.1.1/app_improvement_proposal.md`
스펙 문서: `specs/003-app-v111-upgrade/`

---

### v1.1

**사용자 중심 개선** - CSV 업로드 방식 전환 및 AI 챗봇 도입

#### 주요 변경사항

| 영역 | v1.0 | v1.1 |
|:-----|:-----|:-----|
| **데이터 로딩** | 서버 내 고정 파일 경로 | CSV 파일 업로드 방식 |
| **성능** | 상호작용마다 재로딩 | `session_state` + `cache` 적용 |
| **시각화** | 히스토그램, bar chart | 박스플롯, KDE, 산점도 추가 |
| **시각화 스타일** | 기본 스타일 | Plotly 색상/스타일 개선 |
| **결측치 처리** | 테이블 표시만 | 30% 이상 시 warning 알림 |
| **탭 명칭** | "기차", "테스트" | "훈련 데이터", "테스트 데이터" |
| **교차 분석** | 근접성 분석 포함 | 통합 지도 시각화만 유지 |
| **프로젝트 개요** | 소개 페이지 | 데이터 업로드 허브 |

#### 신규 기능

- **AI 데이터 질의응답**: Anthropic Claude 기반 챗봇으로 데이터 분석 질문
- **사이드바**: API Key 입력, 모델 선택, 토큰 사용량, 업로드 현황 표시

#### 코드 품질 개선

- Deprecated API 수정 (`width='stretch'` → `use_container_width=True`)
- Mutable default argument 수정 (`[]` → `None`)
- ZeroDivisionError 방지 로직 추가

기준 문서: `docs/v1.1/app_improvement_proposal.md`
스펙 문서: `specs/002-app-v1-1-upgrade/`

---

### v1.0

**기초 컨셉 구현** - 7개 공공데이터셋 개별 탐색 기능

- 데이터셋별 탭 구성 (CCTV, 보안등, 어린이보호구역, 주차장, 사고, train, test)
- 기본 통계 및 데이터 미리보기
- 숫자형/범주형 컬럼 히스토그램
- 좌표 기반 Folium 지도 시각화
- 교차 데이터 분석 (근접성 분석)
- 프로젝트 개요 탭

기준 문서: `docs/v1.0/*.md`
스펙 문서: `specs/001-daegu-data-viz/`

---

## Stack

이 프로젝트는 [GitHub SpecKit](https://github.com/github/spec-kit)을 활용한 스펙 기반 개발 연습과 데이터 시각화를 학습하기 위해 만들어졌습니다.

| 분류 | 기술 |
|------|------|
| **언어** | Python 3.10+ |
| **웹 프레임워크** | Streamlit 1.28+ |
| **데이터 처리** | pandas 2.0+, numpy 1.24+ |
| **시각화** | Plotly 5.17+, Folium 0.14+ |
| **지도 연동** | streamlit-folium 0.15+ |
| **AI** | Anthropic Claude 4.5, LangChain 0.3+, LangGraph 0.2+ |
| **ML** | LightGBM (ECLO 예측 모델) |
| **스펙 관리** | GitHub SpecKit |
| **패키지 매니저** | uv (권장), pip |
| **개발 도구** | Claude Code |

---

## Tool Calling 도구 목록 (22개)

AI 챗봇이 데이터 분석 시 사용하는 도구 목록입니다.

### 데이터 정보

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `get_dataframe_info` | 데이터프레임의 기본 정보 (행/열 수, 컬럼 타입) | 없음 |
| `get_column_statistics` | 특정 컬럼의 기초 통계량 | column |
| `get_missing_values` | 각 컬럼별 결측값 개수와 비율 | 없음 |
| `get_value_counts` | 특정 컬럼의 값 빈도수 | column, top_n |

### 데이터 조작

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `filter_dataframe` | 조건에 맞는 행 필터링 | column, operator, value |
| `sort_dataframe` | 특정 컬럼 기준 정렬 | column, ascending, top_n |
| `get_unique_values` | 특정 컬럼의 고유값 목록 | column |
| `get_sample_rows` | 데이터에서 샘플 행 추출 | n, column, value |

### 통계 분석

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `get_correlation` | 수치형 컬럼들 간의 상관관계 분석 | columns |
| `group_by_aggregate` | 그룹별 집계 연산 | group_column, agg_column, operation |
| `calculate_percentile` | 특정 컬럼의 백분위수 계산 | column, percentile |
| `get_outliers` | IQR 방식으로 이상치 탐지 | column, multiplier |
| `cross_tabulation` | 두 범주형 컬럼의 교차표 생성 | row_column, col_column, normalize |
| `get_column_correlation_with_target` | 타겟 컬럼과 모든 숫자 컬럼의 상관관계 | target_column |

### 시계열 분석

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `get_date_range` | 날짜 컬럼의 최소/최대 범위 | column |
| `get_temporal_pattern` | 시간대별 패턴 분석 (월별, 요일별) | column |

### 지리 분석

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `get_geo_bounds` | 위경도 컬럼의 경계값 (최소/최대 좌표) | 없음 |

### 데이터 품질

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `analyze_missing_pattern` | 결측값 패턴 분석 (MCAR, MAR, MNAR 추정) | column |
| `detect_data_types` | 각 컬럼의 실제 데이터 타입 감지 | 없음 |
| `summarize_categorical_distribution` | 범주형 컬럼의 분포 요약 | column |

### ECLO 예측

| 도구명 | 설명 | 파라미터 |
|:-------|:-----|:---------|
| `predict_eclo` | 단일 사고 데이터의 ECLO 예측 | weather, road_surface, road_type, accident_type, time_period, district, day_of_week, accident_hour, accident_year, accident_month, accident_day |
| `predict_eclo_batch` | 여러 사고 데이터의 ECLO 일괄 예측 (v1.2.3) | accidents (사고 정보 리스트) |

---

## 프로젝트 구조

```
public_data/
├── app.py                 # Streamlit 메인 앱
├── pyproject.toml         # uv 패키지 매니저 설정 (v1.2.1+)
├── requirements.txt       # Python 의존성 (pip 호환)
├── syllabus.md           # 15일 교육과정 커리큘럼
├── data/                  # 대구 공공데이터 CSV
│   ├── train.csv
│   ├── test.csv
│   ├── countrywide_accident.csv
│   ├── 대구 CCTV 정보.csv
│   ├── 대구 보안등 정보.csv
│   ├── 대구 어린이 보호 구역 정보.csv
│   └── 대구 주차장 정보.csv
├── model/                 # v1.2: ECLO 예측 모델
│   ├── accident_lgbm_model.pkl  # LightGBM 모델
│   ├── label_encoders.pkl       # 라벨 인코더
│   └── feature_config.json      # 피처 설정
├── utils/                 # 유틸리티 모듈
│   ├── chatbot.py        # AI 챗봇 로직 (LangGraph 통합)
│   ├── graph.py          # v1.2: LangGraph StateGraph 정의
│   ├── predictor.py      # v1.2: ECLO 예측 모듈
│   ├── prompts.py        # v1.2.3: 시스템 프롬프트 모듈
│   ├── tools.py          # Tool Calling 도구 (22개)
│   ├── visualizer.py     # Plotly 시각화
│   ├── geo.py            # Folium 지도
│   ├── loader.py         # 데이터 로더
│   └── narration.py      # 나레이션
├── docs/                  # 버전별 문서
│   ├── constitution.md
│   ├── v1.0/, v1.1/, v1.1.1/, v1.1.2/, v1.1.3/
│   ├── v1.2/, v1.2.1/, v1.2.2/, v1.2.3/, v1.2.4/, v1.2.5/
├── specs/                 # SDD 스펙 산출물
│   ├── 001-daegu-data-viz/
│   ├── 002-app-v1-1-upgrade/
│   ├── 003-app-v111-upgrade/
│   └── 004-app-v12-upgrade/
└── material/              # 일차별 학습 자료
    ├── 1-3/              # 1~3일차
    ├── 3-7/              # 3~7일차
    ├── 8-10/             # 8~10일차
    ├── 11-12/            # 11~12일차
    ├── 13/               # 13일차
    ├── 14/               # 14일차
    └── 15/               # 15일차
```

---

## 문서

| 문서 | 설명 |
|------|------|
| `docs/v1.0/*.md` | v1.0 스펙 결정을 위한 최초 참고 문서 |
| `docs/v1.1/*.md` | v1.1 개선 제안서 및 노트 |
| `docs/v1.1.1/*.md` | v1.1.1 개선 제안서 (Tool Calling, 성능 최적화) |
| `docs/v1.1.2/*.md` | v1.1.2 개선 제안서 (UX 개선, 분석 도구 확장) |
| `docs/v1.1.3/*.md` | v1.1.3 개선 제안서 (UI 간소화, 버그 수정) |
| `docs/v1.2/*.md` | v1.2 개선 제안서 (LangGraph 마이그레이션) |
| `docs/v1.2.1/*.md` | v1.2.1 개선 제안서 (uv 마이그레이션, 버그 수정) |
| `docs/v1.2.2/*.md` | v1.2.2 개선 제안서 (ECLO 예측 독립화) |
| `docs/v1.2.3/*.md` | v1.2.3 개선 제안서 (프롬프트 모듈화, 배치 예측) |
| `docs/v1.2.4/*.md` | v1.2.4 개선 제안서 (환경 설정 자동화) |
| `docs/v1.2.5/*.md` | v1.2.5 개선 제안서 (시계열 분석, 다중 데이터셋 선택) |
| `specs/001-daegu-data-viz/` | v1.0 스펙 산출물 (spec, plan, tasks) |
| `specs/002-app-v1-1-upgrade/` | v1.1 스펙 산출물 |
| `specs/003-app-v111-upgrade/` | v1.1.1 스펙 산출물 |
| `specs/004-app-v12-upgrade/` | v1.2 스펙 산출물 (LangGraph, ECLO 예측) |
| `material/` | 일차별 학습 자료 (아래 참조) |
| `syllabus.md` | 전체 15일 커리큘럼 문서 |

---

## 학습 자료 (material/)

15일 교육과정의 일차별 학습 자료입니다. 전체 커리큘럼은 `syllabus.md`를 참조하세요.

### 커리큘럼 개요

```
Phase 1: 데이터 분석 기초 (1~4일차)
Phase 2: Streamlit 앱 개발 (5~10일차)
Phase 3: AI 챗봇 통합 (11~15일차)
```

### 일차별 학습 내용

| 디렉토리 | 일차 | 핵심 내용 |
|:---------|:-----|:----------|
| `material/1-3/` | 1~3일차 | 파이썬 기초, 데이터 분석, EDA, 예측 모델 구축 |
| `material/3-7/` | 3~7일차 | Pandas, Plotly, AutoML, 가드레일 모델, 대구 공공데이터 검증 |
| `material/8-10/` | 8~10일차 | Streamlit 기초~고급, Folium 지도, 대시보드 구현 |
| `material/11-12/` | 11~12일차 | SDD 방법론, LangChain, Claude API |
| `material/13/` | 13일차 | Anthropic Tool Calling (정의, 실행, 다중 도구) |
| `material/14/` | 14일차 | LangGraph 대화 메모리 (Buffer, Window, Summary, Hybrid) |
| `material/15/` | 15일차 | LangGraph 메모리 + Tool Calling 통합 |

### 학습 흐름

```
[데이터 분석 기초] → [Streamlit 앱 개발] → [AI 챗봇 통합]
      ↓                    ↓                    ↓
  CSV 분석            시각화 앱            Tool Calling
  EDA, 모델          Plotly, Folium       LangGraph 메모리
```
