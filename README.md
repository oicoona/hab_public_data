# 대구 공공데이터 시각화

대구 지역 공공데이터를 탐색·분석하는 교육용 Streamlit 애플리케이션입니다.

데이터 출처: [DACON 대구 교통사고 피해 예측 AI 경진대회](https://dacon.io/competitions/official/236193/overview/description)

---

## 빠른 시작

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

### v1.1.3 (현재)

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
| **AI** | Anthropic Claude 4.5 |
| **스펙 관리** | GitHub SpecKit |
| **개발 도구** | Claude Code |

---

## 문서

| 문서 | 설명 |
|------|------|
| `docs/v1.0/*.md` | v1.0 스펙 결정을 위한 최초 참고 문서 |
| `docs/v1.1/*.md` | v1.1 개선 제안서 및 노트 |
| `docs/v1.1.1/*.md` | v1.1.1 개선 제안서 (Tool Calling, 성능 최적화) |
| `docs/v1.1.2/*.md` | v1.1.2 개선 제안서 (UX 개선, 분석 도구 확장) |
| `docs/v1.1.3/*.md` | v1.1.3 개선 제안서 (UI 간소화, 버그 수정) |
| `specs/001-daegu-data-viz/` | v1.0 스펙 산출물 (spec, plan, tasks) |
| `specs/002-app-v1-1-upgrade/` | v1.1 스펙 산출물 |
| `specs/003-app-v111-upgrade/` | v1.1.1 스펙 산출물 |
| `streamlit_study/` | Streamlit 학습 예제 (01~14번) |
