"""
Geospatial utilities for coordinate detection and distance calculations.
"""
from math import radians, cos, sin, asin, sqrt
import pandas as pd


def detect_lat_lng_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """
    Auto-detect latitude and longitude column names.

    Parameters:
        df (pd.DataFrame): Dataset with potential coordinate columns

    Returns:
        tuple[str | None, str | None]: (latitude_column_name, longitude_column_name)
        Returns (None, None) if coordinates not found
    """
    # Common patterns for latitude and longitude column names
    lat_candidates = ['lat', 'latitude', '위도', 'y좌표', 'y', 'Lat', 'Latitude']
    lng_candidates = ['lng', 'lon', 'longitude', '경도', 'x좌표', 'x', 'Lng', 'Lon', 'Longitude']

    lat_col = None
    lng_col = None

    # Check each column name against candidates (case-insensitive for English)
    for col in df.columns:
        # Check latitude
        if not lat_col:
            for candidate in lat_candidates:
                if col == candidate or col.lower() == candidate.lower():
                    lat_col = col
                    break

        # Check longitude
        if not lng_col:
            for candidate in lng_candidates:
                if col == candidate or col.lower() == candidate.lower():
                    lng_col = col
                    break

        # Stop if both found
        if lat_col and lng_col:
            break

    # Only return if both coordinates found
    if lat_col and lng_col:
        return (lat_col, lng_col)
    else:
        return (None, None)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula.

    Parameters:
        lat1, lon1 (float): First point latitude/longitude in decimal degrees
        lat2, lon2 (float): Second point latitude/longitude in decimal degrees

    Returns:
        float: Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Earth radius in kilometers
    km = 6371 * c
    return km


def validate_coordinates(lat: float, lng: float, bounds: dict | None = None) -> bool:
    """
    Validate if coordinates are within expected bounds (default: Daegu).

    Parameters:
        lat (float): Latitude in decimal degrees
        lng (float): Longitude in decimal degrees
        bounds (dict | None): Optional bounds dict with keys 'lat_min', 'lat_max', 'lng_min', 'lng_max'
            Default: Daegu bounds (35.7-36.1 N, 128.4-128.8 E)

    Returns:
        bool: True if coordinates valid and within bounds
    """
    # Reject invalid coordinates (0, 0)
    if lat == 0.0 and lng == 0.0:
        return False

    # Check basic latitude/longitude validity
    if not (-90 <= lat <= 90):
        return False
    if not (-180 <= lng <= 180):
        return False

    # Default Daegu bounds
    if bounds is None:
        bounds = {
            'lat_min': 35.7,
            'lat_max': 36.1,
            'lng_min': 128.4,
            'lng_max': 128.8
        }

    # Check bounds
    if not (bounds['lat_min'] <= lat <= bounds['lat_max']):
        return False
    if not (bounds['lng_min'] <= lng <= bounds['lng_max']):
        return False

    return True


def compute_proximity_stats(
    df_base: pd.DataFrame,
    base_lat_col: str,
    base_lng_col: str,
    df_target: pd.DataFrame,
    target_lat_col: str,
    target_lng_col: str,
    thresholds: list[float] = [0.5, 1.0, 2.0]
) -> pd.DataFrame:
    """
    Calculate proximity statistics between two datasets.

    Parameters:
        df_base (pd.DataFrame): Base dataset (e.g., train data)
        base_lat_col, base_lng_col (str): Coordinate column names in df_base
        df_target (pd.DataFrame): Target dataset (e.g., CCTV data)
        target_lat_col, target_lng_col (str): Coordinate column names in df_target
        thresholds (list[float]): Distance thresholds in kilometers (default: [0.5, 1.0, 2.0])

    Returns:
        pd.DataFrame: Proximity counts
            - Rows: Each base point (sampled to max 5000 if needed)
            - Columns: One column per threshold with count of target points within that distance
    """
    # Sample df_base to 5000 rows if larger (for performance)
    if len(df_base) > 5000:
        df_base = df_base.sample(5000, random_state=42)

    # Initialize results dictionary
    results = {str(t): [] for t in thresholds}

    # Drop rows with missing coordinates in both datasets
    df_base_clean = df_base.dropna(subset=[base_lat_col, base_lng_col])
    df_target_clean = df_target.dropna(subset=[target_lat_col, target_lng_col])

    # Calculate proximity for each base point
    for _, base_row in df_base_clean.iterrows():
        base_lat = base_row[base_lat_col]
        base_lng = base_row[base_lng_col]

        # Count target points within each threshold
        counts = {t: 0 for t in thresholds}

        for _, target_row in df_target_clean.iterrows():
            target_lat = target_row[target_lat_col]
            target_lng = target_row[target_lng_col]

            # Calculate distance
            dist = haversine_distance(base_lat, base_lng, target_lat, target_lng)

            # Increment counts for all thresholds that include this distance
            for t in thresholds:
                if dist <= t:
                    counts[t] += 1

        # Add counts to results
        for t in thresholds:
            results[str(t)].append(counts[t])

    # Convert to DataFrame
    return pd.DataFrame(results)
