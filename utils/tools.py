"""
Data analysis tools for LangGraph-based AI chatbot.

v1.2: LangChain @tool 데코레이터 형식으로 마이그레이션
- 기존 20개 분석 도구 + 1개 ECLO 예측 도구
- RunnableConfig를 통한 DataFrame 전달
"""
import pandas as pd
import numpy as np
from typing import Any, Literal

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from utils.geo import detect_lat_lng_columns


# ============================================================================
# Helper Functions
# ============================================================================

def get_dataframe_from_config(config: RunnableConfig) -> pd.DataFrame:
    """RunnableConfig에서 DataFrame을 추출합니다."""
    configurable = config.get("configurable", {})
    df = configurable.get("dataframe")
    if df is None:
        raise KeyError("현재 활성화된 데이터셋이 없습니다.")
    return df


def get_current_dataset_from_config(config: RunnableConfig) -> str:
    """RunnableConfig에서 현재 데이터셋 이름을 추출합니다."""
    configurable = config.get("configurable", {})
    return configurable.get("current_dataset", "")


# ============================================================================
# Data Analysis Tools (20개)
# ============================================================================

@tool
def get_dataframe_info(config: RunnableConfig) -> str:
    """DataFrame 기본 정보를 반환합니다. 행/열 수, 컬럼명, 데이터 타입을 포함합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if df.empty:
        return "데이터가 없습니다 (빈 DataFrame)."

    info_lines = [
        f"## DataFrame 기본 정보",
        f"- 행 수: {len(df):,}",
        f"- 열 수: {len(df.columns)}",
        f"",
        f"## 컬럼 목록 및 데이터 타입",
    ]

    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        info_lines.append(f"- {col}: {dtype} (비결측치: {non_null:,})")

    return "\n".join(info_lines)


@tool
def get_column_statistics(column: str, config: RunnableConfig) -> str:
    """특정 수치형 컬럼의 통계 정보를 반환합니다. 평균, 중앙값, 표준편차, 최소/최대값 등을 포함합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {', '.join(df.columns)}"

    if not pd.api.types.is_numeric_dtype(df[column]):
        return f"'{column}' 컬럼은 수치형이 아닙니다. 데이터 타입: {df[column].dtype}"

    col_data = df[column].dropna()

    if len(col_data) == 0:
        return f"'{column}' 컬럼의 모든 값이 결측치입니다."

    stats = {
        "개수": len(col_data),
        "평균": col_data.mean(),
        "표준편차": col_data.std(),
        "최소값": col_data.min(),
        "25%": col_data.quantile(0.25),
        "중앙값": col_data.median(),
        "75%": col_data.quantile(0.75),
        "최대값": col_data.max(),
    }

    lines = [f"## '{column}' 컬럼 통계"]
    for name, value in stats.items():
        if isinstance(value, float):
            lines.append(f"- {name}: {value:,.2f}")
        else:
            lines.append(f"- {name}: {value:,}")

    return "\n".join(lines)


@tool
def get_missing_values(config: RunnableConfig) -> str:
    """각 컬럼별 결측치 개수와 비율을 분석하여 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if df.empty:
        return "데이터가 없습니다 (빈 DataFrame)."

    total_rows = len(df)
    lines = [f"## 결측치 현황 (전체 {total_rows:,}행)"]

    for col in df.columns:
        missing_count = df[col].isnull().sum()
        missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0
        lines.append(f"- {col}: {missing_count:,}개 ({missing_pct:.1f}%)")

    total_missing = df.isnull().sum().sum()
    total_cells = total_rows * len(df.columns)
    total_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0
    lines.append(f"\n**전체 결측치**: {total_missing:,}개 / {total_cells:,}개 ({total_pct:.1f}%)")

    return "\n".join(lines)


@tool
def get_value_counts(column: str, top_n: int = 20, config: RunnableConfig = None) -> str:
    """범주형 컬럼의 값별 개수를 반환합니다. 상위 N개만 표시할 수 있습니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {', '.join(df.columns)}"

    value_counts = df[column].value_counts()
    total_unique = len(value_counts)

    lines = [f"## '{column}' 컬럼 값 분포 (상위 {min(top_n, total_unique)}개 / 총 {total_unique}개)"]

    for idx, (value, count) in enumerate(value_counts.head(top_n).items()):
        pct = count / len(df) * 100
        lines.append(f"- {value}: {count:,}개 ({pct:.1f}%)")

    if total_unique > top_n:
        lines.append(f"\n... 외 {total_unique - top_n}개 값")

    return "\n".join(lines)


@tool
def filter_dataframe(
    column: str,
    operator: Literal["==", "!=", ">", "<", ">=", "<=", "contains"],
    value: Any,
    config: RunnableConfig
) -> str:
    """주어진 조건에 맞는 행만 필터링하여 결과를 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {', '.join(df.columns)}"

    try:
        if operator == "==":
            filtered = df[df[column] == value]
        elif operator == "!=":
            filtered = df[df[column] != value]
        elif operator == ">":
            filtered = df[df[column] > value]
        elif operator == "<":
            filtered = df[df[column] < value]
        elif operator == ">=":
            filtered = df[df[column] >= value]
        elif operator == "<=":
            filtered = df[df[column] <= value]
        elif operator == "contains":
            filtered = df[df[column].astype(str).str.contains(str(value), case=False, na=False)]
        else:
            return f"지원하지 않는 연산자입니다: {operator}"

        lines = [
            f"## 필터링 결과: {column} {operator} {value}",
            f"- 원본 행 수: {len(df):,}",
            f"- 필터링 후 행 수: {len(filtered):,}",
            f"",
            f"### 샘플 데이터 (최대 10행)",
            filtered.head(10).to_string(index=False)
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"필터링 중 오류 발생: {str(e)}"


@tool
def sort_dataframe(
    column: str,
    ascending: bool = True,
    top_n: int = 10,
    config: RunnableConfig = None
) -> str:
    """특정 컬럼을 기준으로 데이터를 정렬하여 상위 결과를 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {', '.join(df.columns)}"

    try:
        sorted_df = df.sort_values(by=column, ascending=ascending)
        order_text = "오름차순" if ascending else "내림차순"

        lines = [
            f"## 정렬 결과: {column} 기준 ({order_text})",
            f"- 상위 {min(top_n, len(sorted_df))}행",
            f"",
            sorted_df.head(top_n).to_string(index=False)
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"정렬 중 오류 발생: {str(e)}"


@tool
def get_correlation(columns: list[str] | None = None, config: RunnableConfig = None) -> str:
    """수치형 컬럼들 간의 상관관계를 분석하여 상관계수 행렬을 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    numeric_df = df.select_dtypes(include=[np.number])

    if numeric_df.empty:
        return "수치형 컬럼이 없습니다."

    if columns:
        valid_columns = [c for c in columns if c in numeric_df.columns]
        if not valid_columns:
            return f"지정한 컬럼 중 수치형 컬럼이 없습니다. 수치형 컬럼: {', '.join(numeric_df.columns)}"
        numeric_df = numeric_df[valid_columns]

    if len(numeric_df.columns) < 2:
        return "상관관계 분석에는 최소 2개의 수치형 컬럼이 필요합니다."

    corr_matrix = numeric_df.corr()

    lines = [
        f"## 상관계수 행렬 ({len(corr_matrix.columns)}개 컬럼)",
        f"",
        corr_matrix.round(3).to_string()
    ]

    return "\n".join(lines)


@tool
def group_by_aggregate(
    group_column: str,
    agg_column: str,
    operation: Literal["sum", "mean", "count", "min", "max", "median", "std"],
    config: RunnableConfig
) -> str:
    """특정 컬럼을 기준으로 그룹화하고 집계 연산을 수행합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if group_column not in df.columns:
        return f"'{group_column}' 컬럼을 찾을 수 없습니다."

    if agg_column not in df.columns:
        return f"'{agg_column}' 컬럼을 찾을 수 없습니다."

    try:
        if operation == "count":
            result = df.groupby(group_column)[agg_column].count()
        else:
            result = df.groupby(group_column)[agg_column].agg(operation)

        result_df = result.reset_index()
        result_df.columns = [group_column, f"{agg_column}_{operation}"]

        op_korean = {
            "sum": "합계", "mean": "평균", "count": "개수",
            "min": "최소", "max": "최대", "median": "중앙값", "std": "표준편차"
        }

        lines = [
            f"## 그룹별 집계: {group_column}별 {agg_column} {op_korean.get(operation, operation)}",
            f"- 그룹 수: {len(result_df)}",
            f"",
            result_df.to_string(index=False)
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"집계 중 오류 발생: {str(e)}"


@tool
def get_unique_values(column: str, config: RunnableConfig) -> str:
    """특정 컬럼의 고유값 목록과 개수를 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {', '.join(df.columns)}"

    unique_values = df[column].dropna().unique()
    unique_count = len(unique_values)

    lines = [f"## '{column}' 컬럼 고유값 ({unique_count}개)"]

    if unique_count <= 50:
        for val in sorted(unique_values, key=lambda x: str(x)):
            lines.append(f"- {val}")
    else:
        lines.append(f"고유값이 너무 많아 처음 50개만 표시합니다:")
        for val in sorted(unique_values, key=lambda x: str(x))[:50]:
            lines.append(f"- {val}")
        lines.append(f"... 외 {unique_count - 50}개")

    return "\n".join(lines)


@tool
def get_date_range(column: str, config: RunnableConfig) -> str:
    """날짜 컬럼의 최소/최대 날짜와 기간을 분석하여 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    try:
        date_col = pd.to_datetime(df[column], errors='coerce')
        valid_dates = date_col.dropna()

        if len(valid_dates) == 0:
            return f"'{column}' 컬럼에 유효한 날짜가 없습니다."

        min_date = valid_dates.min()
        max_date = valid_dates.max()
        date_range = max_date - min_date

        lines = [
            f"## '{column}' 컬럼 날짜 범위",
            f"- 시작 날짜: {min_date.strftime('%Y-%m-%d')}",
            f"- 종료 날짜: {max_date.strftime('%Y-%m-%d')}",
            f"- 기간: {date_range.days}일",
            f"- 유효 날짜 수: {len(valid_dates):,}개",
            f"- 결측 날짜 수: {len(date_col) - len(valid_dates):,}개"
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"날짜 분석 중 오류 발생: {str(e)}"


@tool
def get_outliers(column: str, multiplier: float = 1.5, config: RunnableConfig = None) -> str:
    """IQR(사분위수 범위) 기반으로 이상치를 탐지하여 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    if not pd.api.types.is_numeric_dtype(df[column]):
        return f"'{column}' 컬럼은 수치형이 아닙니다."

    col_data = df[column].dropna()

    if len(col_data) == 0:
        return f"'{column}' 컬럼의 모든 값이 결측치입니다."

    q1 = col_data.quantile(0.25)
    q3 = col_data.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    outliers_low = col_data[col_data < lower_bound]
    outliers_high = col_data[col_data > upper_bound]
    total_outliers = len(outliers_low) + len(outliers_high)

    lines = [
        f"## '{column}' 컬럼 이상치 분석 (IQR 배수: {multiplier})",
        f"",
        f"### 기준값",
        f"- Q1 (25%): {q1:,.2f}",
        f"- Q3 (75%): {q3:,.2f}",
        f"- IQR: {iqr:,.2f}",
        f"- 하한선: {lower_bound:,.2f}",
        f"- 상한선: {upper_bound:,.2f}",
        f"",
        f"### 이상치 현황",
        f"- 하한 미만: {len(outliers_low)}개",
        f"- 상한 초과: {len(outliers_high)}개",
        f"- 총 이상치: {total_outliers}개 ({total_outliers/len(col_data)*100:.1f}%)"
    ]

    return "\n".join(lines)


@tool
def get_sample_rows(
    n: int = 5,
    column: str | None = None,
    value: Any = None,
    config: RunnableConfig = None
) -> str:
    """데이터에서 샘플 행을 추출하여 반환합니다. 조건을 지정할 수 있습니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if df.empty:
        return "데이터가 없습니다 (빈 DataFrame)."

    if column and value is not None:
        if column not in df.columns:
            return f"'{column}' 컬럼을 찾을 수 없습니다."
        filtered_df = df[df[column] == value]
        title = f"## 샘플 데이터: {column} = {value} (최대 {n}행)"
    else:
        filtered_df = df
        title = f"## 샘플 데이터 (최대 {n}행)"

    if len(filtered_df) == 0:
        return "조건에 맞는 데이터가 없습니다."

    sample_df = filtered_df.sample(min(n, len(filtered_df)), random_state=42)

    lines = [
        title,
        f"- 전체 행 수: {len(filtered_df):,}",
        f"",
        sample_df.to_string(index=False)
    ]

    return "\n".join(lines)


@tool
def calculate_percentile(column: str, percentile: float, config: RunnableConfig) -> str:
    """수치형 컬럼에서 특정 백분위수 값을 계산합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    if not pd.api.types.is_numeric_dtype(df[column]):
        return f"'{column}' 컬럼은 수치형이 아닙니다."

    if not 0 <= percentile <= 100:
        return f"백분위수는 0-100 사이여야 합니다. 입력값: {percentile}"

    col_data = df[column].dropna()

    if len(col_data) == 0:
        return f"'{column}' 컬럼의 모든 값이 결측치입니다."

    result = col_data.quantile(percentile / 100)

    lines = [
        f"## '{column}' 컬럼 {percentile}번째 백분위수",
        f"- 결과값: {result:,.2f}",
        f"- 데이터 수: {len(col_data):,}개"
    ]

    return "\n".join(lines)


@tool
def get_geo_bounds(config: RunnableConfig) -> str:
    """위경도 데이터의 지리적 범위(최소/최대 위도, 경도)를 반환합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    lat_col, lng_col = detect_lat_lng_columns(df)

    if not lat_col or not lng_col:
        return "위경도 컬럼을 찾을 수 없습니다."

    lat_data = df[lat_col].dropna()
    lng_data = df[lng_col].dropna()

    if len(lat_data) == 0 or len(lng_data) == 0:
        return "유효한 좌표 데이터가 없습니다."

    lines = [
        f"## 지리적 범위",
        f"- 위도 컬럼: {lat_col}",
        f"- 경도 컬럼: {lng_col}",
        f"",
        f"### 위도 범위",
        f"- 최소: {lat_data.min():.6f}",
        f"- 최대: {lat_data.max():.6f}",
        f"- 범위: {lat_data.max() - lat_data.min():.6f}",
        f"",
        f"### 경도 범위",
        f"- 최소: {lng_data.min():.6f}",
        f"- 최대: {lng_data.max():.6f}",
        f"- 범위: {lng_data.max() - lng_data.min():.6f}",
        f"",
        f"- 유효 좌표 수: {min(len(lat_data), len(lng_data)):,}개"
    ]

    return "\n".join(lines)


@tool
def cross_tabulation(
    row_column: str,
    col_column: str,
    normalize: bool = False,
    config: RunnableConfig = None
) -> str:
    """두 범주형 컬럼 간의 교차표(빈도표)를 생성합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if row_column not in df.columns:
        return f"'{row_column}' 컬럼을 찾을 수 없습니다."

    if col_column not in df.columns:
        return f"'{col_column}' 컬럼을 찾을 수 없습니다."

    try:
        if normalize:
            cross_tab = pd.crosstab(df[row_column], df[col_column], normalize='all')
            cross_tab = cross_tab.round(3)
        else:
            cross_tab = pd.crosstab(df[row_column], df[col_column])

        normalize_text = " (비율)" if normalize else ""

        lines = [
            f"## 교차표: {row_column} x {col_column}{normalize_text}",
            f"",
            cross_tab.to_string()
        ]

        return "\n".join(lines)

    except Exception as e:
        return f"교차표 생성 중 오류 발생: {str(e)}"


@tool
def analyze_missing_pattern(column: str, config: RunnableConfig) -> str:
    """결측값 패턴을 분석하여 MCAR, MAR, MNAR 여부를 추정합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    missing_mask = df[column].isnull()
    total_rows = len(df)
    missing_count = missing_mask.sum()
    missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0

    if missing_count == 0:
        return f"'{column}' 컬럼에 결측값이 없습니다."

    lines = [
        f"## '{column}' 컬럼 결측값 패턴 분석",
        f"",
        f"### 기본 현황",
        f"- 전체 행 수: {total_rows:,}",
        f"- 결측값 수: {missing_count:,} ({missing_pct:.1f}%)",
        f"",
        f"### 결측값 패턴 추정"
    ]

    # 다른 컬럼들과의 관계 분석
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if column in numeric_cols:
        numeric_cols.remove(column)

    correlations = []
    for other_col in numeric_cols[:5]:
        valid_mask = df[other_col].notna()
        if valid_mask.sum() > 10:
            missing_indicator = missing_mask.astype(int)
            corr = df.loc[valid_mask, [other_col]].assign(missing=missing_indicator[valid_mask])
            r = corr['missing'].corr(corr[other_col])
            if not np.isnan(r):
                correlations.append((other_col, abs(r)))

    if correlations:
        correlations.sort(key=lambda x: x[1], reverse=True)
        max_corr = correlations[0][1]

        if max_corr < 0.1:
            pattern_type = "MCAR (완전 무작위 결측)"
            pattern_desc = "결측값이 다른 변수들과 거의 상관관계가 없습니다."
        elif max_corr < 0.3:
            pattern_type = "MAR 가능성 (무작위 결측)"
            pattern_desc = "결측값이 다른 변수들과 약한 상관관계를 보입니다."
        else:
            pattern_type = "MNAR 가능성 (비무작위 결측)"
            pattern_desc = "결측값이 다른 변수들과 상당한 상관관계를 보입니다."

        lines.append(f"- **추정 유형**: {pattern_type}")
        lines.append(f"- **설명**: {pattern_desc}")
        lines.append(f"")
        lines.append(f"### 관련 컬럼과의 상관관계")
        for col_name, corr_val in correlations[:3]:
            lines.append(f"- {col_name}: {corr_val:.3f}")
    else:
        lines.append("- 상관관계 분석을 위한 수치형 컬럼이 부족합니다.")

    return "\n".join(lines)


@tool
def get_column_correlation_with_target(target_column: str, config: RunnableConfig) -> str:
    """특정 타겟 컬럼과 다른 모든 수치형 컬럼들 간의 상관관계를 분석합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if target_column not in df.columns:
        return f"'{target_column}' 컬럼을 찾을 수 없습니다."

    if not pd.api.types.is_numeric_dtype(df[target_column]):
        return f"'{target_column}' 컬럼은 수치형이 아닙니다."

    numeric_df = df.select_dtypes(include=[np.number])
    if len(numeric_df.columns) < 2:
        return "상관관계 분석에는 최소 2개의 수치형 컬럼이 필요합니다."

    correlations = []
    for col in numeric_df.columns:
        if col != target_column:
            corr = numeric_df[target_column].corr(numeric_df[col])
            if not np.isnan(corr):
                correlations.append((col, corr))

    if not correlations:
        return "상관관계를 계산할 수 있는 컬럼이 없습니다."

    correlations.sort(key=lambda x: abs(x[1]), reverse=True)

    lines = [
        f"## '{target_column}' 컬럼과의 상관관계 분석",
        f"",
        f"### 상관계수 순위 (절대값 기준)"
    ]

    for idx, (col, corr) in enumerate(correlations, 1):
        abs_corr = abs(corr)
        if abs_corr >= 0.7:
            strength = "강함"
        elif abs_corr >= 0.4:
            strength = "중간"
        elif abs_corr >= 0.2:
            strength = "약함"
        else:
            strength = "매우 약함"

        direction = "양의 상관" if corr > 0 else "음의 상관"
        lines.append(f"{idx}. {col}: {corr:+.3f} ({strength}, {direction})")

    return "\n".join(lines)


@tool
def detect_data_types(config: RunnableConfig) -> str:
    """컬럼별 실제 데이터 타입을 추론합니다. 숫자처럼 보이는 문자열, 날짜 형식 등을 감지합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if df.empty:
        return "데이터가 없습니다 (빈 DataFrame)."

    lines = [
        f"## 컬럼별 데이터 타입 분석",
        f"",
        f"| 컬럼명 | pandas 타입 | 추론 타입 | 비고 |",
        f"|--------|-------------|-----------|------|"
    ]

    for col in df.columns:
        pandas_dtype = str(df[col].dtype)
        sample = df[col].dropna()

        if len(sample) == 0:
            inferred_type = "알 수 없음"
            note = "모든 값이 결측"
        elif pd.api.types.is_numeric_dtype(df[col]):
            if pd.api.types.is_integer_dtype(df[col]):
                unique_ratio = df[col].nunique() / len(sample)
                if unique_ratio < 0.05:
                    inferred_type = "범주형 (코드)"
                    note = f"고유값 {df[col].nunique()}개"
                else:
                    inferred_type = "정수"
                    note = ""
            else:
                inferred_type = "실수"
                note = ""
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            inferred_type = "날짜/시간"
            note = ""
        else:
            sample_vals = sample.astype(str).head(100)
            inferred_type = None
            note = ""

            try:
                pd.to_datetime(sample_vals, errors='raise')
                inferred_type = "날짜 (문자열)"
                note = "datetime 변환 가능"
            except (ValueError, TypeError):
                pass

            if inferred_type is None:
                try:
                    pd.to_numeric(sample_vals, errors='raise')
                    inferred_type = "숫자 (문자열)"
                    note = "numeric 변환 가능"
                except (ValueError, TypeError):
                    pass

            if inferred_type is None:
                unique_count = df[col].nunique()
                if unique_count <= 20:
                    inferred_type = "범주형"
                    note = f"고유값 {unique_count}개"
                elif unique_count <= len(df) * 0.5:
                    inferred_type = "범주형 (다수)"
                    note = f"고유값 {unique_count}개"
                else:
                    inferred_type = "텍스트/ID"
                    note = "고유값 비율 높음"

        lines.append(f"| {col} | {pandas_dtype} | {inferred_type} | {note} |")

    return "\n".join(lines)


@tool
def get_temporal_pattern(column: str, config: RunnableConfig) -> str:
    """시간/날짜 관련 컬럼의 패턴을 분석합니다. 월별, 요일별, 시간대별 분포를 확인합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    try:
        date_col = pd.to_datetime(df[column], errors='coerce')
        valid_dates = date_col.dropna()

        if len(valid_dates) == 0:
            return f"'{column}' 컬럼에 유효한 날짜 데이터가 없습니다."

        lines = [
            f"## '{column}' 컬럼 시간 패턴 분석",
            f"",
            f"### 기본 정보",
            f"- 유효 날짜 수: {len(valid_dates):,}개",
            f"- 기간: {valid_dates.min().strftime('%Y-%m-%d')} ~ {valid_dates.max().strftime('%Y-%m-%d')}"
        ]

        # 연도별 분포
        if valid_dates.dt.year.nunique() > 1:
            year_dist = valid_dates.dt.year.value_counts().sort_index()
            lines.append(f"")
            lines.append(f"### 연도별 분포")
            for year, count in year_dist.items():
                pct = count / len(valid_dates) * 100
                lines.append(f"- {year}년: {count:,}개 ({pct:.1f}%)")

        # 월별 분포
        month_dist = valid_dates.dt.month.value_counts().sort_index()
        lines.append(f"")
        lines.append(f"### 월별 분포")
        month_names = ['1월', '2월', '3월', '4월', '5월', '6월',
                       '7월', '8월', '9월', '10월', '11월', '12월']
        for month, count in month_dist.items():
            pct = count / len(valid_dates) * 100
            lines.append(f"- {month_names[month-1]}: {count:,}개 ({pct:.1f}%)")

        # 요일별 분포
        day_dist = valid_dates.dt.dayofweek.value_counts().sort_index()
        lines.append(f"")
        lines.append(f"### 요일별 분포")
        day_names = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
        for day, count in day_dist.items():
            pct = count / len(valid_dates) * 100
            lines.append(f"- {day_names[day]}: {count:,}개 ({pct:.1f}%)")

        return "\n".join(lines)

    except Exception as e:
        return f"시간 패턴 분석 중 오류 발생: {str(e)}"


@tool
def summarize_categorical_distribution(column: str, config: RunnableConfig) -> str:
    """범주형 컬럼의 분포를 상세하게 요약합니다. 집중도, 편향성, 희귀 카테고리 등을 분석합니다."""
    try:
        df = get_dataframe_from_config(config)
    except KeyError as e:
        return str(e)

    if column not in df.columns:
        return f"'{column}' 컬럼을 찾을 수 없습니다."

    value_counts = df[column].value_counts()
    total = len(df)
    unique_count = len(value_counts)
    missing_count = df[column].isnull().sum()

    lines = [
        f"## '{column}' 컬럼 범주형 분포 분석",
        f"",
        f"### 기본 통계",
        f"- 전체 행 수: {total:,}",
        f"- 고유 카테고리 수: {unique_count}",
        f"- 결측값: {missing_count:,}개 ({missing_count/total*100:.1f}%)"
    ]

    if unique_count > 0:
        top1_pct = value_counts.iloc[0] / (total - missing_count) * 100 if (total - missing_count) > 0 else 0
        top3_pct = value_counts.head(3).sum() / (total - missing_count) * 100 if (total - missing_count) > 0 else 0

        lines.append(f"")
        lines.append(f"### 집중도 분석")
        lines.append(f"- 최빈값 비율: {top1_pct:.1f}% ({value_counts.index[0]})")
        lines.append(f"- 상위 3개 비율: {top3_pct:.1f}%")

        if top1_pct > 80:
            bias = "매우 편향됨 (단일 값이 80% 이상)"
        elif top1_pct > 50:
            bias = "편향됨 (단일 값이 50% 이상)"
        elif top3_pct > 80:
            bias = "약간 편향됨 (상위 3개가 80% 이상)"
        else:
            bias = "균형적 분포"
        lines.append(f"- 편향성: {bias}")

    # 상위 카테고리
    lines.append(f"")
    lines.append(f"### 상위 카테고리 (최대 10개)")
    for idx, (cat, count) in enumerate(value_counts.head(10).items(), 1):
        pct = count / (total - missing_count) * 100 if (total - missing_count) > 0 else 0
        lines.append(f"{idx}. {cat}: {count:,}개 ({pct:.1f}%)")

    return "\n".join(lines)


# ============================================================================
# ECLO Prediction Tool (1개)
# ============================================================================

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
    - 노면상태: 건조, 젖음/습기, 적설, 결빙 등
    - 도로형태: 단일로, 교차로, 횡단보도 등
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
    # 데이터셋 조건 검증
    current_dataset = get_current_dataset_from_config(config)
    if current_dataset not in ["train", "test"]:
        return "ECLO 예측은 train 또는 test 데이터셋에서만 사용 가능합니다. 현재 데이터셋에서는 일반 데이터 분석 기능만 사용할 수 있습니다."

    # predictor 모듈 import 및 예측 실행
    try:
        from utils.predictor import predict_eclo_value, interpret_eclo

        features = {
            "기상상태": 기상상태,
            "노면상태": 노면상태,
            "도로형태": 도로형태,
            "사고유형": 사고유형,
            "시간대": 시간대,
            "시군구": 시군구,
            "요일": 요일,
            "사고시": 사고시,
            "사고연": 사고연,
            "사고월": 사고월,
            "사고일": 사고일,
        }

        eclo_value = predict_eclo_value(features)
        interpretation = interpret_eclo(eclo_value)

        lines = [
            f"## ECLO 예측 결과",
            f"",
            f"**예측된 ECLO 값**: {eclo_value:.4f}",
            f"",
            f"**해석**: {interpretation}",
            f"",
            f"### 입력된 피처",
            f"- 기상상태: {기상상태}",
            f"- 노면상태: {노면상태}",
            f"- 도로형태: {도로형태}",
            f"- 사고유형: {사고유형}",
            f"- 시간대: {시간대}",
            f"- 시군구: {시군구}",
            f"- 요일: {요일}",
            f"- 사고 시각: {사고연}년 {사고월}월 {사고일}일 {사고시}시"
        ]

        return "\n".join(lines)

    except FileNotFoundError as e:
        return f"ECLO 예측 모델을 찾을 수 없습니다: {str(e)}"
    except ValueError as e:
        return f"피처 값 오류: {str(e)}"
    except Exception as e:
        return f"ECLO 예측 중 오류가 발생했습니다: {str(e)}"


# ============================================================================
# Tool Export
# ============================================================================

def get_all_tools() -> list:
    """모든 도구 리스트를 반환합니다."""
    return [
        # 데이터 분석 도구 (20개)
        get_dataframe_info,
        get_column_statistics,
        get_missing_values,
        get_value_counts,
        filter_dataframe,
        sort_dataframe,
        get_correlation,
        group_by_aggregate,
        get_unique_values,
        get_date_range,
        get_outliers,
        get_sample_rows,
        calculate_percentile,
        get_geo_bounds,
        cross_tabulation,
        analyze_missing_pattern,
        get_column_correlation_with_target,
        detect_data_types,
        get_temporal_pattern,
        summarize_categorical_distribution,
        # ECLO 예측 도구 (1개)
        predict_eclo,
    ]


# ============================================================================
# Legacy Support (Backward Compatibility)
# ============================================================================

# 기존 코드와의 호환성을 위해 TOOLS 리스트 유지 (deprecated)
TOOLS = [
    {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else {"type": "object", "properties": {}}
    }
    for tool in get_all_tools()
]

# 기존 execute_tool 함수 (deprecated, LangGraph에서는 ToolNode 사용)
def execute_tool(tool_name: str, tool_input: dict, df: pd.DataFrame) -> str:
    """
    도구를 실행하고 결과를 반환합니다. (Legacy support)

    이 함수는 기존 코드와의 호환성을 위해 유지됩니다.
    새로운 코드에서는 LangGraph ToolNode를 사용하세요.
    """
    tools_map = {t.name: t for t in get_all_tools()}

    if tool_name not in tools_map:
        return f"알 수 없는 도구입니다: {tool_name}"

    try:
        # RunnableConfig 형식으로 DataFrame 전달
        config = {"configurable": {"dataframe": df, "current_dataset": ""}}
        tool_func = tools_map[tool_name]

        # 도구 호출
        return tool_func.invoke({**tool_input, "config": config})
    except Exception as e:
        return f"도구 실행 중 오류가 발생했습니다: {str(e)}"
