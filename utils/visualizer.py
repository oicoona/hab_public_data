"""
Plotly charts and Folium maps generation.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster


def plot_numeric_distribution(df: pd.DataFrame, column: str, title: str | None = None) -> go.Figure:
    """
    Create histogram for numeric column distribution.

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Numeric column name
        title (str | None): Optional chart title (default: auto-generated)

    Returns:
        plotly.graph_objects.Figure: Interactive histogram
    """
    # Count missing values
    missing_count = df[column].isnull().sum()
    total_count = len(df)

    # Auto-generate title if not provided
    if title is None:
        title = f"Distribution of {column}"
        if missing_count > 0:
            title += f" ({missing_count} missing values)"

    # Create histogram
    fig = px.histogram(
        df.dropna(subset=[column]),
        x=column,
        title=title,
        labels={column: column},
        marginal="box"  # Add box plot on top
    )

    # Update layout
    fig.update_layout(
        showlegend=False,
        hovermode='x unified'
    )

    return fig


def plot_categorical_distribution(df: pd.DataFrame, column: str, title: str | None = None, top_n: int = 20) -> go.Figure:
    """
    Create bar chart for categorical column distribution.

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Categorical column name
        title (str | None): Optional chart title
        top_n (int): Show top N categories (default: 20)

    Returns:
        plotly.graph_objects.Figure: Interactive bar chart
    """
    # Get value counts
    value_counts = df[column].value_counts().head(top_n)

    # Auto-generate title if not provided
    if title is None:
        total_categories = df[column].nunique()
        if total_categories > top_n:
            title = f"Top {top_n} Categories in {column} (of {total_categories} total)"
        else:
            title = f"Distribution of {column}"

    # Create bar chart
    fig = px.bar(
        x=value_counts.index,
        y=value_counts.values,
        title=title,
        labels={'x': column, 'y': 'Count'}
    )

    # Update layout
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45
    )

    return fig


def create_folium_map(
    df: pd.DataFrame,
    lat_col: str,
    lng_col: str,
    popup_cols: list[str] = [],
    color: str = 'blue',
    name: str = 'Points',
    icon: str = 'info-sign'
) -> folium.Map:
    """
    Create Folium map with markers for dataset.

    Parameters:
        df (pd.DataFrame): Dataset with coordinates
        lat_col, lng_col (str): Coordinate column names
        popup_cols (list[str]): Columns to include in marker popups (default: empty)
        color (str): Marker color (default: 'blue')
        name (str): Layer name for legend (default: 'Points')
        icon (str): Marker icon (default: 'info-sign')

    Returns:
        folium.Map: Map object ready for rendering
    """
    # Drop rows with missing coordinates
    df_clean = df.dropna(subset=[lat_col, lng_col]).copy()

    # Sample to 5000 points if dataset larger (for performance)
    if len(df_clean) > 5000:
        df_clean = df_clean.sample(5000, random_state=42)

    # Calculate map center as mean of coordinates
    center_lat = df_clean[lat_col].mean()
    center_lng = df_clean[lng_col].mean()

    # Determine zoom level based on coordinate spread
    lat_range = df_clean[lat_col].max() - df_clean[lat_col].min()
    lng_range = df_clean[lng_col].max() - df_clean[lng_col].min()
    max_range = max(lat_range, lng_range)

    # Simple zoom calculation
    if max_range > 1.0:
        zoom_start = 10
    elif max_range > 0.5:
        zoom_start = 11
    elif max_range > 0.1:
        zoom_start = 12
    else:
        zoom_start = 13

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )

    # Create feature group for this dataset
    feature_group = folium.FeatureGroup(name=name)

    # Use MarkerCluster if more than 100 points
    if len(df_clean) > 100:
        marker_cluster = MarkerCluster().add_to(feature_group)
        marker_container = marker_cluster
    else:
        marker_container = feature_group

    # Add markers
    for idx, row in df_clean.iterrows():
        lat = row[lat_col]
        lng = row[lng_col]

        # Create popup content
        if popup_cols:
            popup_html = "<div style='width: 200px'>"
            for col in popup_cols:
                if col in row:
                    popup_html += f"<b>{col}:</b> {row[col]}<br>"
            popup_html += "</div>"
        else:
            popup_html = f"<b>Location:</b> ({lat:.4f}, {lng:.4f})"

        # Add marker
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
        ).add_to(marker_container)

    # Add feature group to map
    feature_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m


def create_overlay_map(datasets: list[dict]) -> folium.Map:
    """
    Create map with multiple datasets overlaid as separate layers.

    Parameters:
        datasets (list[dict]): List of dataset specifications, each with:
            - df (pd.DataFrame): Dataset
            - lat_col (str): Latitude column name
            - lng_col (str): Longitude column name
            - popup_cols (list[str]): Columns for popup
            - color (str): Marker color
            - name (str): Layer name
            - icon (str): Marker icon

    Returns:
        folium.Map: Map with multiple togglable layers
    """
    if not datasets:
        # Return empty map if no datasets
        return folium.Map(location=[35.8714, 128.6014], zoom_start=12)

    # Calculate unified map center from all datasets
    all_lats = []
    all_lngs = []

    for ds in datasets:
        df_clean = ds['df'].dropna(subset=[ds['lat_col'], ds['lng_col']])
        if len(df_clean) > 0:
            all_lats.extend(df_clean[ds['lat_col']].tolist())
            all_lngs.extend(df_clean[ds['lng_col']].tolist())

    if not all_lats:
        # Default to Daegu center if no valid coordinates
        center_lat, center_lng = 35.8714, 128.6014
        zoom_start = 12
    else:
        center_lat = sum(all_lats) / len(all_lats)
        center_lng = sum(all_lngs) / len(all_lngs)

        # Determine zoom based on spread
        lat_range = max(all_lats) - min(all_lats)
        lng_range = max(all_lngs) - min(all_lngs)
        max_range = max(lat_range, lng_range)

        if max_range > 1.0:
            zoom_start = 10
        elif max_range > 0.5:
            zoom_start = 11
        elif max_range > 0.1:
            zoom_start = 12
        else:
            zoom_start = 13

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )

    # Add each dataset as a separate layer
    for ds in datasets:
        df = ds['df']
        lat_col = ds['lat_col']
        lng_col = ds['lng_col']
        popup_cols = ds.get('popup_cols', [])
        color = ds.get('color', 'blue')
        name = ds.get('name', 'Points')
        icon = ds.get('icon', 'info-sign')

        # Drop rows with missing coordinates
        df_clean = df.dropna(subset=[lat_col, lng_col]).copy()

        # Sample if needed
        if len(df_clean) > 5000:
            df_clean = df_clean.sample(5000, random_state=42)

        # Create feature group
        feature_group = folium.FeatureGroup(name=name)

        # Use MarkerCluster for large datasets
        if len(df_clean) > 100:
            marker_cluster = MarkerCluster().add_to(feature_group)
            marker_container = marker_cluster
        else:
            marker_container = feature_group

        # Add markers
        for idx, row in df_clean.iterrows():
            lat = row[lat_col]
            lng = row[lng_col]

            # Create popup
            if popup_cols:
                popup_html = f"<div style='width: 200px'><b>Dataset:</b> {name}<br>"
                for col in popup_cols:
                    if col in row:
                        popup_html += f"<b>{col}:</b> {row[col]}<br>"
                popup_html += "</div>"
            else:
                popup_html = f"<b>{name}</b><br>({lat:.4f}, {lng:.4f})"

            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=color, icon=icon, prefix='glyphicon')
            ).add_to(marker_container)

        # Add feature group to map
        feature_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    return m
