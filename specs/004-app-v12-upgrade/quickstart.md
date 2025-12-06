# Quickstart Guide: v1.2 업그레이드

**Date**: 2025-12-06
**Feature**: 004-app-v12-upgrade

## 개요

이 가이드는 v1.2 업그레이드 후 앱을 실행하고 새로운 기능을 사용하는 방법을 설명한다.

---

## 1. 환경 설정

### 1.1 uv 사용 (권장)

```bash
# uv 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 및 의존성 설치
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 1.2 pip 사용 (대안)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. 앱 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## 3. 새로운 기능 사용

### 3.1 LangGraph 기반 AI 챗봇

기존과 동일한 방식으로 AI 챗봇을 사용할 수 있다. 내부적으로 LangGraph 워크플로우로 전환되었다.

1. 사이드바에서 **Anthropic API Key** 입력
2. 데이터셋 업로드 (프로젝트 개요 탭)
3. AI 챗봇 탭에서 질문
   - 예: "데이터 구조를 알려줘"
   - 예: "컬럼별 결측치를 분석해줘"

### 3.2 ECLO 예측 기능

train 또는 test 데이터셋이 활성화된 상태에서 ECLO 예측을 요청할 수 있다.

**사용 방법**:

1. **train.csv** 또는 **test.csv** 업로드
2. AI 챗봇 탭에서 해당 데이터셋 선택
3. "ECLO를 예측해줘" 입력
4. AI가 필요한 정보를 물어보면 답변
   - 예: "기상상태는 맑음, 도로형태는 직선, 월요일 오후 3시에 발생했어"
5. 모든 11개 피처가 수집되면 예측 결과 확인

**필수 피처 (11개)**:
- 기상상태, 노면상태, 도로형태, 사고유형
- 시간대, 시군구, 요일
- 사고시, 사고연, 사고월, 사고일

**예시 대화**:

```
사용자: ECLO를 예측해줘

AI: ECLO 예측을 위해 다음 정보가 필요합니다:
- 기상상태, 노면상태, 도로형태, 사고유형
- 시간대, 시군구, 요일
- 사고시, 사고연, 사고월, 사고일
어떤 조건의 사고를 예측하고 싶으신가요?

사용자: 맑은 날씨에 건조한 노면, 직선 도로에서 차대차 사고,
아침 시간대 대구 중구에서 2024년 3월 15일 월요일 오전 8시에 발생

AI: 입력하신 조건으로 ECLO를 예측했습니다.
예측된 ECLO 값: 0.35
이는 일반적 사고 수준으로, 경상 가능성이 있는 사고입니다.
...
```

### 3.3 프로젝트 개요 탭 확장

프로젝트 개요 탭에 새로운 섹션이 추가되었다.

**버전 히스토리**:
- v1.0부터 v1.2까지 버전별 발전 사항
- 각 버전의 핵심 기능 및 도구 수 표시

**AI 챗봇 아키텍처**:
- LangGraph 워크플로우 구조 다이어그램
- 21개 도구 목록 (데이터 분석 20개 + ECLO 예측 1개)

---

## 4. 문제 해결

### 4.1 의존성 설치 오류

```bash
# 캐시 정리 후 재설치
uv pip cache purge
uv pip install -r requirements.txt --force-reinstall
```

### 4.2 ECLO 예측 오류

**"ECLO 예측은 train 또는 test 데이터셋에서만 사용 가능합니다"**
→ train.csv 또는 test.csv를 업로드하고 해당 탭을 선택

**"ECLO 예측 모델을 찾을 수 없습니다"**
→ model/ 디렉토리에 다음 파일이 있는지 확인:
- accident_lgbm_model.pkl
- feature_config.json
- label_encoders.pkl

### 4.3 API Key 오류

**"API Key가 유효하지 않습니다"**
→ Anthropic API Key 형식 확인 (sk-ant-로 시작)

---

## 5. 검증 체크리스트

v1.2 업그레이드 후 다음 항목을 검증한다:

- [ ] uv로 의존성 설치 성공
- [ ] `streamlit run app.py` 실행 성공
- [ ] 기존 20개 분석 도구 정상 동작
- [ ] ECLO 예측 도구 정상 동작 (train/test 데이터셋)
- [ ] 프로젝트 개요 탭에 버전 히스토리 표시
- [ ] 프로젝트 개요 탭에 AI 챗봇 아키텍처 표시
- [ ] 스트리밍 응답 정상 동작
- [ ] 도구 실행 피드백 표시

---

## 6. 개발자 참고

### 6.1 새 파일 구조

```
utils/
├── graph.py       # LangGraph StateGraph 정의
├── predictor.py   # ECLO 예측 모듈
└── tools.py       # @tool 데코레이터 형식으로 변환
```

### 6.2 주요 변경 파일

- `utils/chatbot.py`: LangGraph 워크플로우 통합
- `utils/tools.py`: @tool 데코레이터로 마이그레이션
- `app.py`: 프로젝트 개요 탭 확장
- `requirements.txt`: LangChain/LangGraph 추가
- `README.md`: uv 설치 가이드 추가
