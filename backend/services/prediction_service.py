"""
Prediction Service
Migrated from utils/predictor.py
"""
import pandas as pd
from backend.ml.model_loader import get_model, get_encoders, get_feature_config


def encode_features(features: dict) -> pd.DataFrame:
    """
    Encode features to model input format
    
    Args:
        features: 11 feature dictionary
        
    Returns:
        Encoded DataFrame
        
    Raises:
        ValueError: Invalid feature value
    """
    config = get_feature_config()
    encoders = get_encoders()
    
    # Feature order
    feature_cols = config["feature_cols"]
    cat_cols = config["cat_cols"]
    num_cols = config["num_cols"]
    
    # Validate required features
    for col in feature_cols:
        if col not in features:
            raise ValueError(f"필수 피처 '{col}'이(가) 누락되었습니다.")
    
    # Create DataFrame
    df = pd.DataFrame([features])
    
    # Encode categorical features
    for col in cat_cols:
        if col in encoders:
            encoder = encoders[col]
            value = features[col]
            
            # Validate value
            if value not in encoder.classes_:
                valid_values = ", ".join(encoder.classes_[:10])
                if len(encoder.classes_) > 10:
                    valid_values += f" 등 ({len(encoder.classes_)}개)"
                raise ValueError(
                    f"'{value}'은(는) '{col}'의 유효한 값이 아닙니다. "
                    f"유효한 값: {valid_values}"
                )
            
            df[col] = encoder.transform([value])
    
    # Convert numeric features
    for col in num_cols:
        df[col] = pd.to_numeric(df[col])
    
    # Reorder columns
    df = df[feature_cols]
    
    return df


def predict_single_eclo(features: dict) -> float:
    """
    Predict ECLO value for single accident
    
    Args:
        features: 11 feature dictionary
        
    Returns:
        Predicted ECLO value (float)
        
    Raises:
        ValueError: Invalid feature value
    """
    model = get_model()
    encoded_df = encode_features(features)
    
    # Predict
    prediction = model.predict(encoded_df)
    
    # Return single value
    return float(prediction[0])


def interpret_eclo(eclo_value: float) -> str:
    """
    Interpret ECLO value
    
    Args:
        eclo_value: Predicted ECLO value
        
    Returns:
        Interpretation string
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
    Detailed interpretation of ECLO value
    
    Args:
        eclo_value: Predicted ECLO value
        
    Returns:
        Detailed interpretation string
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
    Batch predict ECLO for multiple accidents
    
    Args:
        accidents: List of accident feature dictionaries
        
    Returns:
        List of prediction results
    """
    model = get_model()
    results = []
    
    for idx, features in enumerate(accidents):
        result = {
            "index": idx + 1,
            "features": features,
            "eclo": None,
            "interpretation": None,
            "detail": None,
            "error": None
        }
        
        try:
            encoded_df = encode_features(features)
            prediction = model.predict(encoded_df)
            eclo_value = float(prediction[0])
            
            result["eclo"] = eclo_value
            result["interpretation"] = interpret_eclo(eclo_value)
            result["detail"] = interpret_eclo_detail(eclo_value)
            
        except ValueError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = f"예측 오류: {str(e)}"
        
        results.append(result)
    
    return results
