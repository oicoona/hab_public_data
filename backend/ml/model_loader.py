"""
ECLO Model Loader with Singleton Pattern
Loads model once at startup and keeps in memory
"""
import os
import json
import pickle
from pathlib import Path
from typing import Optional


class ECLOModelLoader:
    """Singleton class to load and cache ECLO model"""
    
    _instance: Optional['ECLOModelLoader'] = None
    _model = None
    _encoders = None
    _feature_config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_all()
    
    def _load_all(self):
        """Load model, encoders, and config"""
        # Determine model directory path
        # In Docker: /app/model/
        # In local: ../model/ from backend/
        model_dir = Path("/app/model")
        if not model_dir.exists():
            # Fallback to local development path
            model_dir = Path(__file__).parent.parent.parent / "model"
        
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        model_path = model_dir / "accident_lgbm_model.pkl"
        encoders_path = model_dir / "label_encoders.pkl"
        config_path = model_dir / "feature_config.json"
        
        # Load model
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        with open(model_path, "rb") as f:
            self._model = pickle.load(f)
        
        # Load encoders
        if not encoders_path.exists():
            raise FileNotFoundError(f"Encoders file not found: {encoders_path}")
        with open(encoders_path, "rb") as f:
            self._encoders = pickle.load(f)
        
        # Load config
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self._feature_config = json.load(f)
        
        print(f"✓ ECLO model loaded successfully from {model_dir}")
    
    @property
    def model(self):
        """Get the loaded model"""
        return self._model
    
    @property
    def encoders(self):
        """Get the loaded encoders"""
        return self._encoders
    
    @property
    def feature_config(self):
        """Get the feature config"""
        return self._feature_config


# Global instance
model_loader = ECLOModelLoader()


def get_model():
    """Get the global model instance"""
    return model_loader.model


def get_encoders():
    """Get the global encoders instance"""
    return model_loader.encoders


def get_feature_config():
    """Get the global feature config"""
    return model_loader.feature_config
