"""
ECLO (Equivalent Casualty Loss of life) prediction module.

v1.2: LightGBM 모델 기반 ECLO 예측
- 11개 피처 입력 → ECLO 값 예측
- 라벨 인코딩 및 피처 검증
"""
import os
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


# 모델 파일 경로
MODEL_DIR = Path(__file__).parent.parent / "model"
MODEL_PATH = MODEL_DIR / "accident_lgbm_model.pkl"
ENCODERS_PATH = MODEL_DIR / "label_encoders.pkl"
CONFIG_PATH = MODEL_DIR / "feature_config.json"

# 캐싱된 모델/인코더
_model = None
_encoders = None
_feature_config = None


def load_model():
    """LightGBM 모델을 로드합니다."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model


def load_encoders():
    """라벨 인코더를 로드합니다."""
    global _encoders
    if _encoders is None:
        if not ENCODERS_PATH.exists():
            raise FileNotFoundError(f"인코더 파일을 찾을 수 없습니다: {ENCODERS_PATH}")
        with open(ENCODERS_PATH, "rb") as f:
            _encoders = pickle.load(f)
    return _encoders


def load_feature_config():
    """피처 설정을 로드합니다."""
    global _feature_config
    if _feature_config is None:
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _feature_config = json.load(f)
    return _feature_config


def get_valid_values(feature_name: str) -> list:
    """특정 피처의 유효 값 목록을 반환합니다."""
    encoders = load_encoders()
    if feature_name in encoders:
        return list(encoders[feature_name].classes_)
    return []


def encode_features(features: dict) -> pd.DataFrame:
    """
    피처를 인코딩하여 모델 입력 형식으로 변환합니다.

    Parameters:
        features: 11개 피처 딕셔너리

    Returns:
        인코딩된 DataFrame

    Raises:
        ValueError: 유효하지 않은 피처 값
    """
    config = load_feature_config()
    encoders = load_encoders()

    # 피처 순서에 맞게 DataFrame 생성
    feature_cols = config["feature_cols"]
    cat_cols = config["cat_cols"]
    num_cols = config["num_cols"]

    # 입력 피처 검증
    for col in feature_cols:
        if col not in features:
            raise ValueError(f"필수 피처 '{col}'이(가) 누락되었습니다.")

    # DataFrame 생성
    df = pd.DataFrame([features])

    # 범주형 피처 인코딩
    for col in cat_cols:
        if col in encoders:
            encoder = encoders[col]
            value = features[col]

            # 유효 값 검증
            if value not in encoder.classes_:
                valid_values = ", ".join(encoder.classes_[:10])
                if len(encoder.classes_) > 10:
                    valid_values += f" 등 ({len(encoder.classes_)}개)"
                raise ValueError(
                    f"'{value}'은(는) '{col}'의 유효한 값이 아닙니다. "
                    f"유효한 값: {valid_values}"
                )

            df[col] = encoder.transform([value])

    # 수치형 피처 타입 변환
    for col in num_cols:
        df[col] = pd.to_numeric(df[col])

    # 피처 순서 맞추기
    df = df[feature_cols]

    return df


def predict_eclo_value(features: dict) -> float:
    """
    ECLO 값을 예측합니다.

    Parameters:
        features: 11개 피처 딕셔너리
            - 기상상태 (str)
            - 노면상태 (str)
            - 도로형태 (str)
            - 사고유형 (str)
            - 시간대 (str)
            - 시군구 (str)
            - 요일 (str)
            - 사고시 (int): 0-23
            - 사고연 (int): 연도
            - 사고월 (int): 1-12
            - 사고일 (int): 1-31

    Returns:
        예측된 ECLO 값 (float)

    Raises:
        FileNotFoundError: 모델 파일 누락
        ValueError: 유효하지 않은 피처 값
    """
    model = load_model()
    encoded_df = encode_features(features)

    # 예측
    prediction = model.predict(encoded_df)

    # 단일 값 반환
    return float(prediction[0])


def interpret_eclo(eclo_value: float) -> str:
    """
    ECLO 값을 해석합니다.

    Parameters:
        eclo_value: 예측된 ECLO 값

    Returns:
        해석 문자열
    """
    if eclo_value < 0.1:
        return "경미"
    elif eclo_value < 0.5:
        return "일반"
    elif eclo_value < 1.0:
        return "심각"
    else:
        return "매우 심각"


def interpret_eclo_detail(eclo_value: float) -> str:
    """
    ECLO 값을 상세하게 해석합니다.

    Parameters:
        eclo_value: 예측된 ECLO 값

    Returns:
        상세 해석 문자열
    """
    if eclo_value < 0.1:
        return (
            "경미한 사고 수준입니다. "
            "부상 가능성이 낮고, 대부분 경상 또는 무상해로 예상됩니다."
        )
    elif eclo_value < 0.5:
        return (
            "일반적인 사고 수준입니다. "
            "경상 가능성이 있으며, 치료가 필요할 수 있습니다."
        )
    elif eclo_value < 1.0:
        return (
            "심각한 사고 수준입니다. "
            "중상 가능성이 있으며, 장기 치료나 입원이 필요할 수 있습니다."
        )
    else:
        return (
            "매우 심각한 사고 수준입니다. "
            "치명적 부상 가능성이 높으며, 즉각적인 응급 처치가 필요합니다."
        )


def predict_eclo_batch(accidents: list[dict]) -> list[dict]:
    """
    여러 사고 데이터의 ECLO를 일괄 예측합니다. (v1.2.3)

    Parameters:
        accidents: 사고 정보 딕셔너리 리스트
            각 딕셔너리는 11개 피처 포함:
            - 기상상태, 노면상태, 도로형태, 사고유형, 시간대
            - 시군구, 요일, 사고시, 사고연, 사고월, 사고일

    Returns:
        예측 결과 리스트 (각 항목: {features, eclo, interpretation, error})

    Raises:
        FileNotFoundError: 모델 파일 누락
    """
    model = load_model()
    results = []

    for idx, features in enumerate(accidents):
        result = {
            "index": idx + 1,
            "features": features,
            "eclo": None,
            "interpretation": None,
            "error": None
        }

        try:
            encoded_df = encode_features(features)
            prediction = model.predict(encoded_df)
            eclo_value = float(prediction[0])

            result["eclo"] = eclo_value
            result["interpretation"] = interpret_eclo(eclo_value)

        except ValueError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = f"예측 오류: {str(e)}"

        results.append(result)

    return results


# 피처별 유효 값 (docstring 참조용)
VALID_VALUES = {
    "기상상태": ["맑음", "흐림", "비", "눈", "안개", "기타"],
    "노면상태": ["건조", "젖음/습기", "적설", "결빙", "기타"],
    "도로형태": ["단일로", "교차로", "횡단보도", "철길건널목", "기타"],
    "사고유형": ["차대차", "차대사람", "차량단독"],
    "시간대": ["새벽", "아침", "낮", "저녁", "밤"],
    "요일": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"],
}
