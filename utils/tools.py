"""
Data analysis tools for Tool Calling in Claude chatbot.

이 모듈은 Claude API의 Tool Use 기능을 위한 15개 데이터 분석 도구를 정의합니다.
각 도구는 pandas DataFrame을 분석하여 결과를 문자열로 반환합니다.
"""
import pandas as pd
import numpy as np
from typing import Any

from utils.geo import detect_lat_lng_columns


# ============================================================================
# Tool Definitions (JSON Schema for Anthropic API)
# ============================================================================

TOOLS = [
    {
        "name": "get_dataframe_info",
        "description": "DataFrame 기본 정보를 반환합니다. 행/열 수, 컬럼명, 데이터 타입을 포함합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_column_statistics",
        "description": "특정 수치형 컬럼의 통계 정보를 반환합니다. 평균, 중앙값, 표준편차, 최소/최대값 등을 포함합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "통계를 계산할 컬럼명"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "get_missing_values",
        "description": "각 컬럼별 결측치 개수와 비율을 분석하여 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_value_counts",
        "description": "범주형 컬럼의 값별 개수를 반환합니다. 상위 N개만 표시할 수 있습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "값 분포를 확인할 컬럼명"
                },
                "top_n": {
                    "type": "integer",
                    "description": "상위 N개만 표시 (기본값: 20)"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "filter_dataframe",
        "description": "주어진 조건에 맞는 행만 필터링하여 결과를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "필터링할 컬럼명"
                },
                "operator": {
                    "type": "string",
                    "enum": ["==", "!=", ">", "<", ">=", "<=", "contains"],
                    "description": "비교 연산자"
                },
                "value": {
                    "description": "비교할 값"
                }
            },
            "required": ["column", "operator", "value"]
        }
    },
    {
        "name": "sort_dataframe",
        "description": "특정 컬럼을 기준으로 데이터를 정렬하여 상위 결과를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "정렬 기준 컬럼명"
                },
                "ascending": {
                    "type": "boolean",
                    "description": "오름차순 정렬 여부 (기본값: true)"
                },
                "top_n": {
                    "type": "integer",
                    "description": "반환할 행 수 (기본값: 10)"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "get_correlation",
        "description": "수치형 컬럼들 간의 상관관계를 분석하여 상관계수 행렬을 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "상관관계를 분석할 컬럼 목록 (비어있으면 모든 수치형 컬럼)"
                }
            },
            "required": []
        }
    },
    {
        "name": "group_by_aggregate",
        "description": "특정 컬럼을 기준으로 그룹화하고 집계 연산을 수행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_column": {
                    "type": "string",
                    "description": "그룹화 기준 컬럼명"
                },
                "agg_column": {
                    "type": "string",
                    "description": "집계할 컬럼명"
                },
                "operation": {
                    "type": "string",
                    "enum": ["sum", "mean", "count", "min", "max", "median", "std"],
                    "description": "집계 연산 종류"
                }
            },
            "required": ["group_column", "agg_column", "operation"]
        }
    },
    {
        "name": "get_unique_values",
        "description": "특정 컬럼의 고유값 목록과 개수를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "고유값을 확인할 컬럼명"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "get_date_range",
        "description": "날짜 컬럼의 최소/최대 날짜와 기간을 분석하여 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "날짜 컬럼명"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "get_outliers",
        "description": "IQR(사분위수 범위) 기반으로 이상치를 탐지하여 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "이상치를 탐지할 수치형 컬럼명"
                },
                "multiplier": {
                    "type": "number",
                    "description": "IQR 배수 (기본값: 1.5)"
                }
            },
            "required": ["column"]
        }
    },
    {
        "name": "get_sample_rows",
        "description": "데이터에서 샘플 행을 추출하여 반환합니다. 조건을 지정할 수 있습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {
                    "type": "integer",
                    "description": "추출할 샘플 수 (기본값: 5)"
                },
                "column": {
                    "type": "string",
                    "description": "조건을 적용할 컬럼명 (선택)"
                },
                "value": {
                    "description": "필터링할 값 (선택)"
                }
            },
            "required": []
        }
    },
    {
        "name": "calculate_percentile",
        "description": "수치형 컬럼에서 특정 백분위수 값을 계산합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {
                    "type": "string",
                    "description": "백분위수를 계산할 컬럼명"
                },
                "percentile": {
                    "type": "number",
                    "description": "계산할 백분위수 (0-100)"
                }
            },
            "required": ["column", "percentile"]
        }
    },
    {
        "name": "get_geo_bounds",
        "description": "위경도 데이터의 지리적 범위(최소/최대 위도, 경도)를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "cross_tabulation",
        "description": "두 범주형 컬럼 간의 교차표(빈도표)를 생성합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "row_column": {
                    "type": "string",
                    "description": "행(row)으로 사용할 컬럼명"
                },
                "col_column": {
                    "type": "string",
                    "description": "열(column)으로 사용할 컬럼명"
                },
                "normalize": {
                    "type": "boolean",
                    "description": "비율로 정규화 여부 (기본값: false)"
                }
            },
            "required": ["row_column", "col_column"]
        }
    }
]


# ============================================================================
# Tool Handlers (T011-T025)
# ============================================================================

def get_dataframe_info(df: pd.DataFrame, **kwargs) -> str:
    """
    DataFrame 기본 정보를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame

    Returns:
        str: DataFrame 정보 문자열
    """
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


def get_column_statistics(df: pd.DataFrame, column: str, **kwargs) -> str:
    """
    특정 수치형 컬럼의 통계 정보를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 통계를 계산할 컬럼명

    Returns:
        str: 통계 정보 문자열
    """
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


def get_missing_values(df: pd.DataFrame, **kwargs) -> str:
    """
    각 컬럼별 결측치 개수와 비율을 분석합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame

    Returns:
        str: 결측치 현황 문자열
    """
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


def get_value_counts(df: pd.DataFrame, column: str, top_n: int = 20, **kwargs) -> str:
    """
    범주형 컬럼의 값별 개수를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 값 분포를 확인할 컬럼명
        top_n (int): 상위 N개만 표시 (기본값: 20)

    Returns:
        str: 값 분포 문자열
    """
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


def filter_dataframe(df: pd.DataFrame, column: str, operator: str, value: Any, **kwargs) -> str:
    """
    조건에 맞는 행만 필터링하여 결과를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 필터링할 컬럼명
        operator (str): 비교 연산자
        value: 비교할 값

    Returns:
        str: 필터링 결과 문자열
    """
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


def sort_dataframe(df: pd.DataFrame, column: str, ascending: bool = True, top_n: int = 10, **kwargs) -> str:
    """
    특정 컬럼을 기준으로 데이터를 정렬합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 정렬 기준 컬럼명
        ascending (bool): 오름차순 정렬 여부
        top_n (int): 반환할 행 수

    Returns:
        str: 정렬 결과 문자열
    """
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


def get_correlation(df: pd.DataFrame, columns: list[str] | None = None, **kwargs) -> str:
    """
    수치형 컬럼들 간의 상관관계를 분석합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        columns (list[str] | None): 분석할 컬럼 목록

    Returns:
        str: 상관계수 행렬 문자열
    """
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


def group_by_aggregate(df: pd.DataFrame, group_column: str, agg_column: str, operation: str, **kwargs) -> str:
    """
    특정 컬럼을 기준으로 그룹화하고 집계 연산을 수행합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        group_column (str): 그룹화 기준 컬럼명
        agg_column (str): 집계할 컬럼명
        operation (str): 집계 연산 종류

    Returns:
        str: 그룹별 집계 결과 문자열
    """
    if group_column not in df.columns:
        return f"'{group_column}' 컬럼을 찾을 수 없습니다."

    if agg_column not in df.columns:
        return f"'{agg_column}' 컬럼을 찾을 수 없습니다."

    valid_ops = ["sum", "mean", "count", "min", "max", "median", "std"]
    if operation not in valid_ops:
        return f"지원하지 않는 집계 연산입니다: {operation}. 지원: {', '.join(valid_ops)}"

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


def get_unique_values(df: pd.DataFrame, column: str, **kwargs) -> str:
    """
    특정 컬럼의 고유값 목록과 개수를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 고유값을 확인할 컬럼명

    Returns:
        str: 고유값 목록 문자열
    """
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


def get_date_range(df: pd.DataFrame, column: str, **kwargs) -> str:
    """
    날짜 컬럼의 최소/최대 날짜와 기간을 분석합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 날짜 컬럼명

    Returns:
        str: 날짜 범위 정보 문자열
    """
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


def get_outliers(df: pd.DataFrame, column: str, multiplier: float = 1.5, **kwargs) -> str:
    """
    IQR 기반으로 이상치를 탐지합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 이상치를 탐지할 컬럼명
        multiplier (float): IQR 배수 (기본값: 1.5)

    Returns:
        str: 이상치 정보 문자열
    """
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


def get_sample_rows(df: pd.DataFrame, n: int = 5, column: str | None = None, value: Any = None, **kwargs) -> str:
    """
    데이터에서 샘플 행을 추출합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        n (int): 추출할 샘플 수
        column (str | None): 조건을 적용할 컬럼명
        value: 필터링할 값

    Returns:
        str: 샘플 데이터 문자열
    """
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


def calculate_percentile(df: pd.DataFrame, column: str, percentile: float, **kwargs) -> str:
    """
    수치형 컬럼에서 특정 백분위수 값을 계산합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        column (str): 백분위수를 계산할 컬럼명
        percentile (float): 계산할 백분위수 (0-100)

    Returns:
        str: 백분위수 결과 문자열
    """
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


def get_geo_bounds(df: pd.DataFrame, **kwargs) -> str:
    """
    위경도 데이터의 지리적 범위를 반환합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame

    Returns:
        str: 지리적 범위 문자열
    """
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


def cross_tabulation(df: pd.DataFrame, row_column: str, col_column: str, normalize: bool = False, **kwargs) -> str:
    """
    두 범주형 컬럼 간의 교차표를 생성합니다.

    Parameters:
        df (pd.DataFrame): 분석할 DataFrame
        row_column (str): 행으로 사용할 컬럼명
        col_column (str): 열로 사용할 컬럼명
        normalize (bool): 비율로 정규화 여부

    Returns:
        str: 교차표 문자열
    """
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


# ============================================================================
# Tool Dispatcher (T026)
# ============================================================================

# 도구 이름과 핸들러 함수 매핑
TOOL_HANDLERS = {
    "get_dataframe_info": get_dataframe_info,
    "get_column_statistics": get_column_statistics,
    "get_missing_values": get_missing_values,
    "get_value_counts": get_value_counts,
    "filter_dataframe": filter_dataframe,
    "sort_dataframe": sort_dataframe,
    "get_correlation": get_correlation,
    "group_by_aggregate": group_by_aggregate,
    "get_unique_values": get_unique_values,
    "get_date_range": get_date_range,
    "get_outliers": get_outliers,
    "get_sample_rows": get_sample_rows,
    "calculate_percentile": calculate_percentile,
    "get_geo_bounds": get_geo_bounds,
    "cross_tabulation": cross_tabulation,
}


def execute_tool(tool_name: str, tool_input: dict, df: pd.DataFrame) -> str:
    """
    도구를 실행하고 결과를 반환합니다.

    Parameters:
        tool_name (str): 실행할 도구 이름
        tool_input (dict): 도구 입력 파라미터
        df (pd.DataFrame): 분석할 DataFrame

    Returns:
        str: 도구 실행 결과 문자열
    """
    if tool_name not in TOOL_HANDLERS:
        return f"알 수 없는 도구입니다: {tool_name}"

    try:
        handler = TOOL_HANDLERS[tool_name]
        result = handler(df, **tool_input)
        return result
    except Exception as e:
        return f"도구 실행 중 오류가 발생했습니다: {str(e)}"
