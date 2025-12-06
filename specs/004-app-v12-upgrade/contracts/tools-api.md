# Tools API Contract: v1.2

**Date**: 2025-12-06
**Feature**: 004-app-v12-upgrade

## 개요

v1.2에서 사용되는 21개 도구의 API 계약을 정의한다.

---

## 1. 공통 사항

### Config 구조

모든 도구는 `RunnableConfig`를 통해 DataFrame과 컨텍스트를 전달받는다.

```python
config = {
    "configurable": {
        "dataframe": pd.DataFrame,      # 현재 활성 DataFrame
        "current_dataset": str,          # 데이터셋 이름 ("train", "test", etc.)
    }
}
```

### 반환 형식

모든 도구는 문자열(`str`)을 반환한다. Markdown 형식을 사용하여 가독성을 높인다.

---

## 2. 데이터 분석 도구 (20개)

### 2.1 get_dataframe_info

DataFrame 기본 정보를 반환한다.

```python
@tool
def get_dataframe_info(config: RunnableConfig) -> str:
    """DataFrame 기본 정보를 반환합니다. 행/열 수, 컬럼명, 데이터 타입을 포함합니다."""
```

**입력**: 없음
**출력**: DataFrame 행/열 수, 컬럼 목록 및 타입

---

### 2.2 get_column_statistics

특정 수치형 컬럼의 통계 정보를 반환한다.

```python
@tool
def get_column_statistics(column: str, config: RunnableConfig) -> str:
    """특정 수치형 컬럼의 통계 정보를 반환합니다. 평균, 중앙값, 표준편차, 최소/최대값 등을 포함합니다."""
```

**입력**:
- `column` (str, required): 통계를 계산할 컬럼명

**출력**: 평균, 표준편차, 최소, 25%, 중앙값, 75%, 최대

---

### 2.3 get_missing_values

각 컬럼별 결측치 개수와 비율을 분석한다.

```python
@tool
def get_missing_values(config: RunnableConfig) -> str:
    """각 컬럼별 결측치 개수와 비율을 분석하여 반환합니다."""
```

**입력**: 없음
**출력**: 컬럼별 결측치 수, 비율, 전체 결측치 요약

---

### 2.4 get_value_counts

범주형 컬럼의 값별 개수를 반환한다.

```python
@tool
def get_value_counts(column: str, top_n: int = 20, config: RunnableConfig) -> str:
    """범주형 컬럼의 값별 개수를 반환합니다. 상위 N개만 표시할 수 있습니다."""
```

**입력**:
- `column` (str, required): 값 분포를 확인할 컬럼명
- `top_n` (int, optional, default=20): 상위 N개만 표시

**출력**: 값별 개수 및 비율

---

### 2.5 filter_dataframe

주어진 조건에 맞는 행만 필터링한다.

```python
@tool
def filter_dataframe(
    column: str,
    operator: Literal["==", "!=", ">", "<", ">=", "<=", "contains"],
    value: Any,
    config: RunnableConfig
) -> str:
    """주어진 조건에 맞는 행만 필터링하여 결과를 반환합니다."""
```

**입력**:
- `column` (str, required): 필터링할 컬럼명
- `operator` (str, required): 비교 연산자
- `value` (Any, required): 비교할 값

**출력**: 필터링 전후 행 수, 샘플 데이터

---

### 2.6 sort_dataframe

특정 컬럼을 기준으로 데이터를 정렬한다.

```python
@tool
def sort_dataframe(
    column: str,
    ascending: bool = True,
    top_n: int = 10,
    config: RunnableConfig
) -> str:
    """특정 컬럼을 기준으로 데이터를 정렬하여 상위 결과를 반환합니다."""
```

**입력**:
- `column` (str, required): 정렬 기준 컬럼명
- `ascending` (bool, optional, default=True): 오름차순 여부
- `top_n` (int, optional, default=10): 반환할 행 수

**출력**: 정렬된 상위 N행

---

### 2.7 get_correlation

수치형 컬럼들 간의 상관관계를 분석한다.

```python
@tool
def get_correlation(columns: list[str] | None = None, config: RunnableConfig) -> str:
    """수치형 컬럼들 간의 상관관계를 분석하여 상관계수 행렬을 반환합니다."""
```

**입력**:
- `columns` (list[str], optional): 분석할 컬럼 목록 (비어있으면 모든 수치형)

**출력**: 상관계수 행렬

---

### 2.8 group_by_aggregate

특정 컬럼을 기준으로 그룹화하고 집계 연산을 수행한다.

```python
@tool
def group_by_aggregate(
    group_column: str,
    agg_column: str,
    operation: Literal["sum", "mean", "count", "min", "max", "median", "std"],
    config: RunnableConfig
) -> str:
    """특정 컬럼을 기준으로 그룹화하고 집계 연산을 수행합니다."""
```

**입력**:
- `group_column` (str, required): 그룹화 기준 컬럼명
- `agg_column` (str, required): 집계할 컬럼명
- `operation` (str, required): 집계 연산 종류

**출력**: 그룹별 집계 결과

---

### 2.9 get_unique_values

특정 컬럼의 고유값 목록과 개수를 반환한다.

```python
@tool
def get_unique_values(column: str, config: RunnableConfig) -> str:
    """특정 컬럼의 고유값 목록과 개수를 반환합니다."""
```

**입력**:
- `column` (str, required): 고유값을 확인할 컬럼명

**출력**: 고유값 목록 (50개 이하) 또는 상위 50개

---

### 2.10 get_date_range

날짜 컬럼의 최소/최대 날짜와 기간을 분석한다.

```python
@tool
def get_date_range(column: str, config: RunnableConfig) -> str:
    """날짜 컬럼의 최소/최대 날짜와 기간을 분석하여 반환합니다."""
```

**입력**:
- `column` (str, required): 날짜 컬럼명

**출력**: 시작/종료 날짜, 기간(일), 유효/결측 날짜 수

---

### 2.11 get_outliers

IQR 기반으로 이상치를 탐지한다.

```python
@tool
def get_outliers(column: str, multiplier: float = 1.5, config: RunnableConfig) -> str:
    """IQR(사분위수 범위) 기반으로 이상치를 탐지하여 반환합니다."""
```

**입력**:
- `column` (str, required): 이상치를 탐지할 수치형 컬럼명
- `multiplier` (float, optional, default=1.5): IQR 배수

**출력**: Q1, Q3, IQR, 하한/상한선, 이상치 개수

---

### 2.12 get_sample_rows

데이터에서 샘플 행을 추출한다.

```python
@tool
def get_sample_rows(
    n: int = 5,
    column: str | None = None,
    value: Any = None,
    config: RunnableConfig
) -> str:
    """데이터에서 샘플 행을 추출하여 반환합니다. 조건을 지정할 수 있습니다."""
```

**입력**:
- `n` (int, optional, default=5): 추출할 샘플 수
- `column` (str, optional): 조건을 적용할 컬럼명
- `value` (Any, optional): 필터링할 값

**출력**: 샘플 데이터

---

### 2.13 calculate_percentile

수치형 컬럼에서 특정 백분위수 값을 계산한다.

```python
@tool
def calculate_percentile(column: str, percentile: float, config: RunnableConfig) -> str:
    """수치형 컬럼에서 특정 백분위수 값을 계산합니다."""
```

**입력**:
- `column` (str, required): 백분위수를 계산할 컬럼명
- `percentile` (float, required): 계산할 백분위수 (0-100)

**출력**: 백분위수 값

---

### 2.14 get_geo_bounds

위경도 데이터의 지리적 범위를 반환한다.

```python
@tool
def get_geo_bounds(config: RunnableConfig) -> str:
    """위경도 데이터의 지리적 범위(최소/최대 위도, 경도)를 반환합니다."""
```

**입력**: 없음
**출력**: 위도/경도 범위, 유효 좌표 수

---

### 2.15 cross_tabulation

두 범주형 컬럼 간의 교차표를 생성한다.

```python
@tool
def cross_tabulation(
    row_column: str,
    col_column: str,
    normalize: bool = False,
    config: RunnableConfig
) -> str:
    """두 범주형 컬럼 간의 교차표(빈도표)를 생성합니다."""
```

**입력**:
- `row_column` (str, required): 행으로 사용할 컬럼명
- `col_column` (str, required): 열로 사용할 컬럼명
- `normalize` (bool, optional, default=False): 비율로 정규화 여부

**출력**: 교차표

---

### 2.16 analyze_missing_pattern

결측값 패턴을 분석하여 MCAR, MAR, MNAR 여부를 추정한다.

```python
@tool
def analyze_missing_pattern(column: str, config: RunnableConfig) -> str:
    """결측값 패턴을 분석하여 MCAR, MAR, MNAR 여부를 추정합니다."""
```

**입력**:
- `column` (str, required): 결측값 패턴을 분석할 컬럼명

**출력**: 결측값 현황, 패턴 유형 추정, 관련 컬럼 상관관계

---

### 2.17 get_column_correlation_with_target

특정 타겟 컬럼과 다른 수치형 컬럼들 간의 상관관계를 분석한다.

```python
@tool
def get_column_correlation_with_target(target_column: str, config: RunnableConfig) -> str:
    """특정 타겟 컬럼과 다른 모든 수치형 컬럼들 간의 상관관계를 분석합니다."""
```

**입력**:
- `target_column` (str, required): 타겟 컬럼명

**출력**: 상관계수 순위, 강도 해석

---

### 2.18 detect_data_types

컬럼별 실제 데이터 타입을 추론한다.

```python
@tool
def detect_data_types(config: RunnableConfig) -> str:
    """컬럼별 실제 데이터 타입을 추론합니다. 숫자처럼 보이는 문자열, 날짜 형식 등을 감지합니다."""
```

**입력**: 없음
**출력**: 컬럼별 pandas 타입, 추론 타입, 비고

---

### 2.19 get_temporal_pattern

시간/날짜 관련 컬럼의 패턴을 분석한다.

```python
@tool
def get_temporal_pattern(column: str, config: RunnableConfig) -> str:
    """시간/날짜 관련 컬럼의 패턴을 분석합니다. 월별, 요일별, 시간대별 분포를 확인합니다."""
```

**입력**:
- `column` (str, required): 시간/날짜 컬럼명

**출력**: 연도별, 월별, 요일별, 시간대별 분포

---

### 2.20 summarize_categorical_distribution

범주형 컬럼의 분포를 상세하게 요약한다.

```python
@tool
def summarize_categorical_distribution(column: str, config: RunnableConfig) -> str:
    """범주형 컬럼의 분포를 상세하게 요약합니다. 집중도, 편향성, 희귀 카테고리 등을 분석합니다."""
```

**입력**:
- `column` (str, required): 범주형 컬럼명

**출력**: 기본 통계, 집중도 분석, 희귀 카테고리, 상위 카테고리

---

## 3. ECLO 예측 도구 (1개)

### 3.1 predict_eclo

ECLO(Equivalent Casualty Loss of life)를 예측한다.

```python
@tool
def predict_eclo(
    기상상태: str,
    노면상태: str,
    도로형태: str,
    사고유형: str,
    시간대: str,
    시군구: str,
    요일: str,
    사고시: int,
    사고연: int,
    사고월: int,
    사고일: int,
    config: RunnableConfig
) -> str:
    """
    ECLO(Equivalent Casualty Loss of life)를 예측합니다.

    이 도구는 train 또는 test 데이터셋이 활성화된 경우에만 사용 가능합니다.
    모든 11개 피처가 제공되어야 예측이 가능합니다.

    피처별 유효 값:
    - 기상상태: 맑음, 흐림, 비, 눈, 안개 등
    - 노면상태: 건조, 젖음, 적설, 결빙 등
    - 도로형태: 직선, 곡선, 교차로 등
    - 사고유형: 차대차, 차대사람, 차량단독 등
    - 시간대: 새벽, 아침, 낮, 저녁, 밤
    - 시군구: 대구 시군구명
    - 요일: 월요일~일요일
    - 사고시: 0-23 (시간)
    - 사고연: 연도 (예: 2023)
    - 사고월: 1-12
    - 사고일: 1-31

    사용자가 피처 정보를 충분히 제공하지 않았다면,
    이 도구를 호출하기 전에 추가 정보를 요청하세요.
    """
```

**입력**:
| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| 기상상태 | str | Y | 맑음, 흐림, 비, 눈, 안개 등 |
| 노면상태 | str | Y | 건조, 젖음, 적설, 결빙 등 |
| 도로형태 | str | Y | 직선, 곡선, 교차로 등 |
| 사고유형 | str | Y | 차대차, 차대사람, 차량단독 등 |
| 시간대 | str | Y | 새벽, 아침, 낮, 저녁, 밤 |
| 시군구 | str | Y | 대구 시군구명 |
| 요일 | str | Y | 월요일~일요일 |
| 사고시 | int | Y | 0-23 |
| 사고연 | int | Y | 연도 |
| 사고월 | int | Y | 1-12 |
| 사고일 | int | Y | 1-31 |

**출력**: 예측된 ECLO 값, 해석, 입력 피처 요약

**조건**: `current_dataset`이 "train" 또는 "test"인 경우에만 사용 가능

**에러 케이스**:
- 데이터셋 조건 불충족: "ECLO 예측은 train 또는 test 데이터셋에서만 사용 가능합니다."
- 모델 파일 누락: "ECLO 예측 모델을 찾을 수 없습니다."
- 유효하지 않은 피처 값: "'{value}'은(는) {feature}의 유효한 값이 아닙니다. 유효한 값: {valid_values}"

---

## 4. 에러 처리

모든 도구는 다음 에러 패턴을 따른다:

```python
def tool_function(..., config: RunnableConfig) -> str:
    try:
        df = config["configurable"]["dataframe"]
        # ... 로직
    except KeyError:
        return "현재 활성화된 데이터셋이 없습니다."
    except Exception as e:
        return f"도구 실행 중 오류가 발생했습니다: {str(e)}"
```
