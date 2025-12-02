"""
Plotly charts and Folium maps generation.
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import folium
from folium.plugins import MarkerCluster


# Color palette for consistent styling (T034, T035)
PLOT_COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'tertiary': '#2ca02c',
    'histogram': '#636EFA',
    'boxplot': '#EF553B',
    'kde': '#00CC96',
    'scatter': '#AB63FA'
}


def check_missing_ratio(df: pd.DataFrame, column: str, threshold: float = 0.3) -> tuple[bool, float]:
    """
    Check if column has missing values above threshold. (T032)

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Column name to check
        threshold (float): Missing ratio threshold (default: 0.3 = 30%)

    Returns:
        tuple[bool, float]: (is_above_threshold, actual_ratio)
    """
    missing_count = df[column].isnull().sum()
    total_count = len(df)
    ratio = missing_count / total_count if total_count > 0 else 0.0
    return (ratio >= threshold, ratio)


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


def plot_boxplot(df: pd.DataFrame, column: str, title: str | None = None) -> go.Figure:
    """
    Create boxplot for numeric column distribution. (T025)

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Numeric column name
        title (str | None): Optional chart title

    Returns:
        plotly.graph_objects.Figure: Interactive boxplot
    """
    missing_count = df[column].isnull().sum()

    if title is None:
        title = f"Boxplot of {column}"
        if missing_count > 0:
            title += f" ({missing_count} missing values)"

    fig = px.box(
        df.dropna(subset=[column]),
        y=column,
        title=title,
        color_discrete_sequence=[PLOT_COLORS['boxplot']]
    )

    fig.update_layout(
        showlegend=False,
        hovermode='y unified'
    )

    return fig


def plot_kde(df: pd.DataFrame, column: str, title: str | None = None) -> go.Figure:
    """
    Create KDE (Kernel Density Estimation) plot for numeric column. (T026)

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Numeric column name
        title (str | None): Optional chart title

    Returns:
        plotly.graph_objects.Figure: Interactive KDE plot
    """
    data = df[column].dropna().values
    missing_count = df[column].isnull().sum()

    if title is None:
        title = f"KDE of {column}"
        if missing_count > 0:
            title += f" ({missing_count} missing values)"

    # Check if we have enough data points
    if len(data) < 2:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="데이터가 부족하여 KDE를 생성할 수 없습니다",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        fig.update_layout(title=title)
        return fig

    try:
        # Create distplot with KDE
        fig = ff.create_distplot(
            [data],
            [column],
            show_hist=True,
            show_rug=False,
            colors=[PLOT_COLORS['kde']]
        )
        fig.update_layout(
            title=title,
            showlegend=False
        )
    except Exception:
        # Fallback to histogram if distplot fails
        fig = px.histogram(
            df.dropna(subset=[column]),
            x=column,
            title=title,
            histnorm='probability density',
            color_discrete_sequence=[PLOT_COLORS['kde']]
        )

    return fig


def plot_scatter(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    title: str | None = None
) -> go.Figure:
    """
    Create scatter plot for two numeric columns. (T027)

    Parameters:
        df (pd.DataFrame): Input dataset
        x_column (str): X-axis numeric column name
        y_column (str): Y-axis numeric column name
        title (str | None): Optional chart title

    Returns:
        plotly.graph_objects.Figure: Interactive scatter plot
    """
    if title is None:
        title = f"{x_column} vs {y_column}"

    # Drop rows where either column is missing
    df_clean = df.dropna(subset=[x_column, y_column])

    fig = px.scatter(
        df_clean,
        x=x_column,
        y=y_column,
        title=title,
        color_discrete_sequence=[PLOT_COLORS['scatter']],
        opacity=0.6
    )

    fig.update_layout(
        hovermode='closest'
    )

    return fig


def plot_with_options(
    df: pd.DataFrame,
    column: str,
    chart_type: str = 'histogram',
    y_column: str | None = None,
    title: str | None = None
) -> go.Figure:
    """
    Create chart based on chart type selection. (T028)

    Parameters:
        df (pd.DataFrame): Input dataset
        column (str): Primary column name
        chart_type (str): One of 'histogram', 'boxplot', 'kde', 'scatter'
        y_column (str | None): Y column for scatter plot
        title (str | None): Optional chart title

    Returns:
        plotly.graph_objects.Figure: Interactive chart
    """
    if chart_type == 'histogram':
        return plot_numeric_distribution(df, column, title)
    elif chart_type == 'boxplot':
        return plot_boxplot(df, column, title)
    elif chart_type == 'kde':
        return plot_kde(df, column, title)
    elif chart_type == 'scatter':
        if y_column is None:
            raise ValueError("scatter plot requires y_column")
        return plot_scatter(df, column, y_column, title)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


def create_folium_map(
    df: pd.DataFrame,
    lat_col: str,
    lng_col: str,
    popup_cols: list[str] | None = None,
    color: str = 'blue',
    name: str = 'Points',
    icon: str = 'info-sign',
    max_points: int = 5000
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
        max_points (int): Maximum number of points to display (default: 5000)

    Returns:
        folium.Map: Map object ready for rendering
    """
    # Default center: Daegu city center
    DAEGU_CENTER_LAT = 35.8714
    DAEGU_CENTER_LNG = 128.6014

    # Drop rows with missing coordinates
    df_clean = df.dropna(subset=[lat_col, lng_col]).copy()

    # Early return with default Daegu center map if no valid coordinates
    if len(df_clean) == 0:
        m = folium.Map(
            location=[DAEGU_CENTER_LAT, DAEGU_CENTER_LNG],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        return m

    # Sample to max_points if dataset larger (for performance)
    if len(df_clean) > max_points:
        df_clean = df_clean.sample(max_points, random_state=42)

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

    # T043: Optimized with itertuples for better performance
    for row in df_clean.itertuples(index=False):
        lat = getattr(row, lat_col)
        lng = getattr(row, lng_col)

        # Create popup content
        if popup_cols:
            popup_html = "<div style='width: 200px'>"
            for col in popup_cols:
                if hasattr(row, col):
                    popup_html += f"<b>{col}:</b> {getattr(row, col)}<br>"
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


def create_overlay_map(datasets: list[dict], max_points: int = 5000) -> folium.Map:
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
        max_points (int): Maximum number of points per dataset (default: 5000)

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
        if len(df_clean) > max_points:
            df_clean = df_clean.sample(max_points, random_state=42)

        # Create feature group
        feature_group = folium.FeatureGroup(name=name)

        # Use MarkerCluster for large datasets
        if len(df_clean) > 100:
            marker_cluster = MarkerCluster().add_to(feature_group)
            marker_container = marker_cluster
        else:
            marker_container = feature_group

        # T044: Optimized with itertuples for better performance
        for row in df_clean.itertuples(index=False):
            lat = getattr(row, lat_col)
            lng = getattr(row, lng_col)

            # Create popup
            if popup_cols:
                popup_html = f"<div style='width: 200px'><b>Dataset:</b> {name}<br>"
                for col in popup_cols:
                    if hasattr(row, col):
                        popup_html += f"<b>{col}:</b> {getattr(row, col)}<br>"
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
