"""
Daegu Public Data Visualization - Streamlit Application

An educational tool for exploring and analyzing public datasets from Daegu.
Provides individual dataset exploration, cross-dataset spatial analysis, and
educational content to help data analysis learners discover insights independently.
"""
import io
import time
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium
from utils.loader import load_dataset, load_dataset_from_session, get_dataset_info, read_csv_safe, read_uploaded_csv
from utils.geo import detect_lat_lng_columns
from utils.visualizer import (
    plot_numeric_distribution,
    plot_categorical_distribution,
    plot_boxplot,
    plot_kde,
    plot_scatter,
    plot_with_options,
    check_missing_ratio,
    create_folium_map,
    create_overlay_map
)
from utils.geo import compute_proximity_stats
from utils.narration import (
    summarize_proximity_stats,
    generate_distribution_insight,
    compare_distributions
)
from utils.chatbot import (
    SYSTEM_PROMPT,
    create_data_context,
    create_chat_response,
    create_chat_response_with_tools,
    stream_chat_response_with_tools,
    handle_chat_error,
    validate_api_key
)
from anthropic import Anthropic

# 데이터셋 매핑 상수
DATASET_MAPPING = {
    'cctv': {
        'display_name': 'CCTV',
        'tab_icon': '🎥',
        'expected_file': '대구 CCTV 정보.csv',
        'color': 'red'
    },
    'lights': {
        'display_name': '보안등',
        'tab_icon': '💡',
        'expected_file': '대구 보안등 정보.csv',
        'color': 'blue'
    },
    'zones': {
        'display_name': '어린이 보호구역',
        'tab_icon': '🏫',
        'expected_file': '대구 어린이 보호 구역 정보.csv',
        'color': 'green'
    },
    'parking': {
        'display_name': '주차장',
        'tab_icon': '🅿️',
        'expected_file': '대구 주차장 정보.csv',
        'color': 'purple'
    },
    'accident': {
        'display_name': '사고',
        'tab_icon': '🚗',
        'expected_file': 'countrywide_accident.csv',
        'color': 'orange'
    },
    'train': {
        'display_name': '훈련 데이터',
        'tab_icon': '📊',
        'expected_file': 'train.csv',
        'color': 'darkred'
    },
    'test': {
        'display_name': '테스트 데이터',
        'tab_icon': '📋',
        'expected_file': 'test.csv',
        'color': 'darkblue'
    }
}

# AI 모델 옵션
AI_MODEL_OPTIONS = [
    {'id': 'claude-sonnet-4-5-20250929', 'name': 'Claude Sonnet 4.5', 'description': '빠른 응답, 비용 효율적 (권장)'},
    {'id': 'claude-opus-4-5-20251101', 'name': 'Claude Opus 4.5', 'description': '복잡한 분석에 적합'},
    {'id': 'claude-haiku-4-5-20251001', 'name': 'Claude Haiku 4.5', 'description': '간단한 질문에 최적'}
]


def init_session_state():
    """
    session_state 초기화.
    앱 시작 시 한 번 호출.
    """
    if 'initialized' in st.session_state:
        return

    # 데이터셋 저장소
    if 'datasets' not in st.session_state:
        st.session_state.datasets = {}

    # 업로드 상태
    if 'upload_status' not in st.session_state:
        st.session_state.upload_status = {
            key: False for key in DATASET_MAPPING.keys()
        }

    # 챗봇 세션
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = {
            'api_key': '',
            'model': 'claude-sonnet-4-5-20250929',
            'selected_dataset': None,
            'chat_history': {},  # T035: Dataset-specific chat history
            'tokens': {'total': 0, 'input': 0, 'output': 0}
        }

    # 지도 설정
    if 'map_settings' not in st.session_state:
        st.session_state.map_settings = {
            'max_points': 5000,  # 기본값
            'confirmed': False   # Enter 키 입력 여부
        }

    st.session_state.initialized = True


def get_chat_history(dataset_name: str) -> list:
    """
    Get chat history for a specific dataset. (T036)

    Parameters:
        dataset_name (str): Dataset key (e.g., 'cctv', 'lights')

    Returns:
        list: Chat history for the dataset
    """
    if dataset_name not in st.session_state.chatbot['chat_history']:
        st.session_state.chatbot['chat_history'][dataset_name] = []
    return st.session_state.chatbot['chat_history'][dataset_name]


def clear_chat_history(dataset_name: str) -> None:
    """
    Clear chat history for a specific dataset. (T037)

    Parameters:
        dataset_name (str): Dataset key (e.g., 'cctv', 'lights')
    """
    st.session_state.chatbot['chat_history'][dataset_name] = []


# Page configuration
st.set_page_config(
    page_title="대구 공공데이터 시각화",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_dataset_tab(dataset_name: str, dataset_display_name: str):
    """
    Render a complete tab for exploring an individual dataset.

    Parameters:
        dataset_name (str): Internal dataset name for load_dataset()
        dataset_display_name (str): Display name for UI
    """
    st.header(f"{dataset_display_name} 데이터셋")

    # Check if dataset is uploaded (T020, T021)
    if not st.session_state.upload_status.get(dataset_name, False):
        st.info(f"📤 **{dataset_display_name}** 데이터를 먼저 업로드해주세요.")
        st.markdown("**프로젝트 개요** 탭에서 CSV 파일을 업로드할 수 있습니다.")
        return

    # Load dataset from session_state (T022)
    df = load_dataset_from_session(dataset_name)
    if df is None:
        st.warning(f"⚠️ {dataset_display_name} 데이터를 불러올 수 없습니다. 다시 업로드해주세요.")
        return

    # Get dataset info
    info = get_dataset_info(df)

    # Display basic statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("전체 행 수", f"{info['row_count']:,}")
    with col2:
        st.metric("전체 컬럼 수", info['column_count'])
    with col3:
        missing_pct = sum(info['missing_ratios'].values()) / len(info['missing_ratios']) * 100 if info['missing_ratios'] else 0
        st.metric("평균 결측값 %", f"{missing_pct:.1f}%")

    # Data Preview
    with st.expander("📋 데이터 미리보기 (처음 10개 행)", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    # Column Information
    with st.expander("📊 컬럼 정보", expanded=False):
        col_info_df = []
        for col in df.columns:
            col_info_df.append({
                '컬럼': col,
                '타입': info['dtypes'][col],
                '결측값 %': f"{info['missing_ratios'][col] * 100:.1f}%"
            })
        st.dataframe(col_info_df, use_container_width=True)

    # Descriptive Statistics for Numeric Columns
    if not info['numeric_summary'].empty:
        with st.expander("📈 숫자 컬럼 통계", expanded=False):
            st.dataframe(info['numeric_summary'], use_container_width=True)

    # Visualizations
    st.subheader("시각화")

    # Detect coordinates
    lat_col, lng_col = detect_lat_lng_columns(df)

    # Map Visualization
    if lat_col and lng_col:
        st.markdown("### 🗺️ 지리적 분포")
        st.info(f"감지된 좌표: **{lat_col}** (위도), **{lng_col}** (경도)")

        # 지도 설정 확인 여부 체크
        if not st.session_state.map_settings['confirmed']:
            st.warning("⚠️ 사이드바에서 지도 설정을 확인하고 Enter 키를 눌러주세요.")
        else:
            # Get columns for popup (exclude coordinate columns, limit to first 3 non-numeric)
            popup_candidates = [col for col in df.columns if col not in [lat_col, lng_col]]
            popup_cols = popup_candidates[:3]  # Show first 3 columns in popup

            # 지도 캐시 키에 max_points 포함
            max_points = st.session_state.map_settings['max_points']
            cache_key = f"map_{dataset_name}_{len(df)}_{max_points}"

            if cache_key not in st.session_state:
                st.session_state[cache_key] = create_folium_map(
                    df, lat_col, lng_col,
                    popup_cols=popup_cols,
                    color='blue',
                    name=dataset_display_name,
                    max_points=max_points
                )

            # T042: Display map with returned_objects=[] to prevent rerendering
            st_folium(st.session_state[cache_key], width=700, height=500, returned_objects=[])
    else:
        st.info("ℹ️ 지리 좌표가 감지되지 않았습니다. 이 데이터셋에는 지도 시각화를 사용할 수 없습니다.")

    # Numeric Distributions (T029-T033: 차트 유형 선택, 결측치 경고)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        st.markdown("### 📊 숫자 컬럼 분포")

        # T029: Chart type selection
        chart_type = st.selectbox(
            "차트 유형 선택:",
            options=['히스토그램', '박스플롯', 'KDE', '산점도'],
            key=f"{dataset_name}_chart_type"
        )

        chart_type_map = {
            '히스토그램': 'histogram',
            '박스플롯': 'boxplot',
            'KDE': 'kde',
            '산점도': 'scatter'
        }

        # T030: For scatter plot, show X/Y column selection
        if chart_type == '산점도':
            col1, col2 = st.columns(2)
            with col1:
                x_col = st.selectbox(
                    "X축 컬럼:",
                    options=numeric_cols,
                    key=f"{dataset_name}_scatter_x"
                )
            with col2:
                y_col = st.selectbox(
                    "Y축 컬럼:",
                    options=[c for c in numeric_cols if c != x_col] if len(numeric_cols) > 1 else numeric_cols,
                    key=f"{dataset_name}_scatter_y"
                )

            # T033: Missing value warning for scatter
            x_warning, x_ratio = check_missing_ratio(df, x_col)
            y_warning, y_ratio = check_missing_ratio(df, y_col)
            if x_warning:
                st.warning(f"⚠️ {x_col} 컬럼의 결측값이 {x_ratio*100:.1f}%입니다. 결과가 왜곡될 수 있습니다.")
            if y_warning:
                st.warning(f"⚠️ {y_col} 컬럼의 결측값이 {y_ratio*100:.1f}%입니다. 결과가 왜곡될 수 있습니다.")

            # T031: Render scatter plot
            fig = plot_scatter(df, x_col, y_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Single column selection for other chart types
            selected_numeric_col = st.selectbox(
                "시각화할 숫자 컬럼 선택:",
                options=numeric_cols,
                key=f"{dataset_name}_numeric_select"
            )

            if selected_numeric_col:
                # T033: Missing value warning
                is_high_missing, missing_ratio = check_missing_ratio(df, selected_numeric_col)
                if is_high_missing:
                    st.warning(f"⚠️ {selected_numeric_col} 컬럼의 결측값이 {missing_ratio*100:.1f}%입니다. 결과가 왜곡될 수 있습니다.")

                # T031: Render selected chart type
                fig = plot_with_options(df, selected_numeric_col, chart_type_map[chart_type])
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ 이 데이터셋에는 숫자형 컬럼이 없습니다.")

    # Categorical Distributions
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if categorical_cols:
        st.markdown("### 📊 범주형 컬럼 분포")

        # Let user select which categorical column to visualize
        selected_cat_col = st.selectbox(
            "시각화할 범주형 컬럼 선택:",
            options=categorical_cols,
            key=f"{dataset_name}_cat_select"
        )

        if selected_cat_col:
            fig = plot_categorical_distribution(df, selected_cat_col)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ 이 데이터셋에는 범주형 컬럼이 없습니다.")


def render_overview_tab():
    """
    Render the project overview tab with upload functionality. (T016-T019)
    """
    st.header("📖 프로젝트 개요")

    # Project Introduction
    st.markdown("""
    ## 대구 공공데이터 시각화 프로젝트

    이 프로젝트는 대구시의 다양한 공공 데이터를 탐색하고 분석할 수 있는 대화형 웹 애플리케이션입니다.
    데이터 분석을 학습하는 사용자들이 실제 공공 데이터를 통해 인사이트를 발견하고
    데이터 시각화 기술을 익힐 수 있도록 설계되었습니다.
    """)

    # Data Upload Section (T017-T019)
    st.subheader("📤 데이터 업로드")
    st.markdown("각 데이터셋에 해당하는 CSV 파일을 업로드하세요.")

    # Display upload status
    uploaded_count = sum(st.session_state.upload_status.values())
    st.info(f"업로드 현황: {uploaded_count} / {len(DATASET_MAPPING)} 데이터셋")

    # Create upload widgets for each dataset
    for dataset_key, dataset_info in DATASET_MAPPING.items():
        with st.expander(
            f"{dataset_info['tab_icon']} {dataset_info['display_name']} "
            f"({'✅ 업로드됨' if st.session_state.upload_status.get(dataset_key) else '⏳ 대기중'})"
        ):
            st.markdown(f"**예상 파일명**: `{dataset_info['expected_file']}`")

            uploaded_file = st.file_uploader(
                f"{dataset_info['display_name']} CSV 파일 선택",
                type=['csv'],
                key=f"upload_{dataset_key}"
            )

            if uploaded_file is not None:
                try:
                    df = read_uploaded_csv(uploaded_file)
                    # Store in session_state (T018)
                    st.session_state.datasets[dataset_key] = df
                    st.session_state.upload_status[dataset_key] = True

                    # Display upload info (T019)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("파일명", uploaded_file.name)
                    with col2:
                        file_size_kb = uploaded_file.size / 1024
                        if file_size_kb > 1024:
                            st.metric("파일 크기", f"{file_size_kb/1024:.2f} MB")
                        else:
                            st.metric("파일 크기", f"{file_size_kb:.2f} KB")
                    with col3:
                        st.metric("행 x 컬럼", f"{len(df):,} x {len(df.columns)}")

                    st.success(f"✅ {dataset_info['display_name']} 데이터 업로드 완료!")

                    # Show preview
                    with st.expander("📋 데이터 미리보기", expanded=False):
                        st.dataframe(df.head(5), use_container_width=True)

                except Exception as e:
                    st.error(f"❌ 파일 읽기 오류: {str(e)}")

    st.markdown("---")

    # Technical Information (T045) - v1.1.3: 주요 기능, 사용 방법 섹션 삭제
    st.subheader("🔧 기술 스택")

    tech_col1, tech_col2, tech_col3 = st.columns(3)

    with tech_col1:
        st.markdown("""
        **프론트엔드**
        - Streamlit 1.28+
        - Plotly 5.17+
        - Folium 0.14+
        """)

    with tech_col2:
        st.markdown("""
        **데이터 처리**
        - Pandas 2.0+
        - NumPy 1.24+
        """)

    with tech_col3:
        st.markdown("""
        **AI**
        - Anthropic Claude
        - Python 3.10+
        """)

    # v1.1.3: 시스템 구조, 데이터 분석 기초 개념, 분석 가이드 질문, 교차 데이터 분석 중요성 섹션 삭제


def render_cross_analysis_tab():
    """
    Render the cross-data analysis tab with proximity analysis, overlay maps,
    distribution comparison, and natural language insights. (T028-T041)
    """
    st.header("🔄 교차 데이터 분석")
    st.markdown("""
    여러 데이터셋을 동시에 지도 위에 표시하고, 공간적 근접성을 분석하며,
    분포를 비교하여 인사이트를 발견합니다.
    """)

    # Check if any datasets are uploaded
    uploaded_datasets = [
        key for key, uploaded in st.session_state.upload_status.items()
        if uploaded
    ]

    if not uploaded_datasets:
        st.info("📤 먼저 **프로젝트 개요** 탭에서 데이터셋을 업로드해주세요.")
        return

    # Dataset selection
    st.subheader("📊 데이터셋 선택")

    available_options = {
        DATASET_MAPPING[key]['display_name']: key
        for key in uploaded_datasets
    }

    # Multi-select for datasets
    selected_names = st.multiselect(
        "분석할 데이터셋을 선택하세요 (2개 이상 권장):",
        options=list(available_options.keys()),
        default=list(available_options.keys())[:2] if len(available_options) >= 2 else list(available_options.keys())
    )

    if len(selected_names) == 0:
        st.warning("⚠️ 최소 1개 이상의 데이터셋을 선택해주세요.")
        return

    # Load selected datasets
    datasets_to_overlay = []
    datasets_with_coords = {}
    dataset_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'darkblue']

    for idx, name in enumerate(selected_names):
        dataset_key = available_options[name]
        df = load_dataset_from_session(dataset_key)

        if df is not None:
            lat_col, lng_col = detect_lat_lng_columns(df)

            if lat_col and lng_col:
                popup_candidates = [col for col in df.columns if col not in [lat_col, lng_col]]
                popup_cols = popup_candidates[:3]

                datasets_to_overlay.append({
                    'df': df,
                    'lat_col': lat_col,
                    'lng_col': lng_col,
                    'popup_cols': popup_cols,
                    'color': dataset_colors[idx % len(dataset_colors)],
                    'name': name,
                    'icon': 'info-sign'
                })
                datasets_with_coords[name] = {
                    'df': df,
                    'lat_col': lat_col,
                    'lng_col': lng_col,
                    'key': dataset_key
                }
            else:
                st.warning(f"⚠️ {name} 데이터셋에서 좌표 정보를 찾을 수 없습니다. (지도 및 근접 분석 제외)")

    # Create tabs for different analysis types
    analysis_tabs = st.tabs(["🗺️ 통합 지도", "📍 근접 분석", "📈 분포 비교"])

    # Tab 1: Overlay Map (T035)
    with analysis_tabs[0]:
        if datasets_to_overlay:
            st.subheader("🗺️ 통합 지도 시각화")

            # Show legend
            st.markdown("**범례:**")
            legend_cols = st.columns(min(len(datasets_to_overlay), 4))
            for idx, ds in enumerate(datasets_to_overlay):
                with legend_cols[idx % 4]:
                    color_emoji = {'red': '🔴', 'blue': '🔵', 'green': '🟢', 'purple': '🟣', 'orange': '🟠', 'darkred': '🔴', 'darkblue': '🔵'}
                    emoji = color_emoji.get(ds['color'], '⚪')
                    st.markdown(f"{emoji} **{ds['name']}** ({len(ds['df']):,}개)")

            # Overlay map caching with session_state
            overlay_cache_key = f"overlay_map_{len(datasets_to_overlay)}_{sum(len(ds['df']) for ds in datasets_to_overlay)}"
            if overlay_cache_key not in st.session_state:
                st.session_state[overlay_cache_key] = create_overlay_map(datasets_to_overlay)

            # Display map with returned_objects=[] to prevent rerendering
            st_folium(st.session_state[overlay_cache_key], width=900, height=600, returned_objects=[])

            st.info("💡 지도 우측 상단의 레이어 컨트롤을 사용하여 각 데이터셋을 개별적으로 켜고 끌 수 있습니다.")
        else:
            st.warning("⚠️ 좌표 정보가 있는 데이터셋이 없습니다.")

    # Tab 2: Proximity Analysis (T034, T037-T041)
    with analysis_tabs[1]:
        st.subheader("📍 근접 분석")
        st.markdown("""
        두 데이터셋 간의 공간적 근접성을 분석합니다.
        기준 데이터셋의 각 포인트에서 대상 데이터셋의 포인트가 특정 거리 내에 몇 개 있는지 계산합니다.
        """)

        if len(datasets_with_coords) < 2:
            st.warning("⚠️ 근접 분석을 위해서는 좌표 정보가 있는 데이터셋이 최소 2개 필요합니다.")
        else:
            coord_dataset_names = list(datasets_with_coords.keys())

            col1, col2 = st.columns(2)
            with col1:
                base_name = st.selectbox(
                    "기준 데이터셋:",
                    options=coord_dataset_names,
                    key="proximity_base"
                )
            with col2:
                target_options = [n for n in coord_dataset_names if n != base_name]
                target_name = st.selectbox(
                    "대상 데이터셋:",
                    options=target_options,
                    key="proximity_target"
                )

            # Threshold selection
            st.markdown("**분석 거리 임계값 (km):**")
            threshold_col1, threshold_col2, threshold_col3 = st.columns(3)
            with threshold_col1:
                t1 = st.number_input("임계값 1", value=0.5, min_value=0.1, max_value=10.0, step=0.1, key="t1")
            with threshold_col2:
                t2 = st.number_input("임계값 2", value=1.0, min_value=0.1, max_value=10.0, step=0.1, key="t2")
            with threshold_col3:
                t3 = st.number_input("임계값 3", value=2.0, min_value=0.1, max_value=10.0, step=0.1, key="t3")

            thresholds = sorted([t1, t2, t3])

            if st.button("🔍 근접 분석 실행", key="run_proximity"):
                base_data = datasets_with_coords[base_name]
                target_data = datasets_with_coords[target_name]

                # Show progress
                with st.spinner(f"'{base_name}'과(와) '{target_name}' 간의 근접 분석 중..."):
                    try:
                        # Run proximity analysis (T034)
                        proximity_df = compute_proximity_stats(
                            base_data['df'],
                            base_data['lat_col'],
                            base_data['lng_col'],
                            target_data['df'],
                            target_data['lat_col'],
                            target_data['lng_col'],
                            thresholds=thresholds
                        )

                        if proximity_df.empty:
                            st.error("❌ 근접 분석 결과가 비어있습니다. 좌표 데이터를 확인해주세요.")
                        else:
                            # Display results table
                            st.markdown("### 📊 근접 분석 결과")

                            # Summary statistics
                            summary_data = []
                            for t in thresholds:
                                t_str = str(t)
                                if t_str in proximity_df.columns:
                                    summary_data.append({
                                        '거리 임계값': f"{t}km",
                                        '평균': f"{proximity_df[t_str].mean():.2f}",
                                        '중앙값': f"{proximity_df[t_str].median():.1f}",
                                        '최소': f"{proximity_df[t_str].min():.0f}",
                                        '최대': f"{proximity_df[t_str].max():.0f}",
                                        '표준편차': f"{proximity_df[t_str].std():.2f}"
                                    })

                            st.dataframe(summary_data, use_container_width=True)

                            # Natural language insights (T037)
                            st.markdown("### 💡 분석 인사이트")
                            for t in thresholds:
                                t_str = str(t)
                                if t_str in proximity_df.columns:
                                    insight = summarize_proximity_stats(proximity_df, t_str, target_name)
                                    st.markdown(f"**{t}km 반경:** {insight}")

                            # Store results in session state for potential reuse
                            st.session_state['last_proximity_result'] = proximity_df

                    except Exception as e:
                        st.error(f"❌ 근접 분석 중 오류 발생: {str(e)}")

    # Tab 3: Distribution Comparison (T036, T038, T039)
    with analysis_tabs[2]:
        st.subheader("📈 분포 비교")
        st.markdown("""
        두 데이터셋의 숫자형 컬럼 분포를 비교합니다.
        동일한 컬럼명을 가진 경우 직접 비교가 가능합니다.
        """)

        if len(selected_names) < 2:
            st.warning("⚠️ 분포 비교를 위해서는 최소 2개의 데이터셋이 필요합니다.")
        else:
            # Select datasets to compare
            col1, col2 = st.columns(2)
            with col1:
                compare_name1 = st.selectbox(
                    "첫 번째 데이터셋:",
                    options=selected_names,
                    key="compare_ds1"
                )
            with col2:
                compare_options2 = [n for n in selected_names if n != compare_name1]
                compare_name2 = st.selectbox(
                    "두 번째 데이터셋:",
                    options=compare_options2,
                    key="compare_ds2"
                )

            # Load datasets
            df1 = load_dataset_from_session(available_options[compare_name1])
            df2 = load_dataset_from_session(available_options[compare_name2])

            if df1 is not None and df2 is not None:
                # Find common numeric columns
                numeric_cols1 = set(df1.select_dtypes(include=['number']).columns)
                numeric_cols2 = set(df2.select_dtypes(include=['number']).columns)
                common_numeric = list(numeric_cols1.intersection(numeric_cols2))

                # Column selection
                st.markdown("**비교할 컬럼 선택:**")

                col1, col2 = st.columns(2)
                with col1:
                    all_numeric1 = list(df1.select_dtypes(include=['number']).columns)
                    selected_col1 = st.selectbox(
                        f"{compare_name1} 컬럼:",
                        options=all_numeric1 if all_numeric1 else ["(숫자형 컬럼 없음)"],
                        key="compare_col1"
                    )
                with col2:
                    all_numeric2 = list(df2.select_dtypes(include=['number']).columns)
                    # Default to same column if common
                    default_idx = 0
                    if selected_col1 in all_numeric2:
                        default_idx = all_numeric2.index(selected_col1)
                    selected_col2 = st.selectbox(
                        f"{compare_name2} 컬럼:",
                        options=all_numeric2 if all_numeric2 else ["(숫자형 컬럼 없음)"],
                        index=default_idx if all_numeric2 else 0,
                        key="compare_col2"
                    )

                if selected_col1 != "(숫자형 컬럼 없음)" and selected_col2 != "(숫자형 컬럼 없음)":
                    # Display comparison chart
                    st.markdown("### 📊 분포 비교 차트")

                    # Create overlayed histogram
                    fig = px.histogram(
                        pd.DataFrame({
                            f'{compare_name1} - {selected_col1}': df1[selected_col1].dropna(),
                        }),
                        title=f"분포 비교: {selected_col1} vs {selected_col2}",
                        opacity=0.7,
                        barmode='overlay'
                    )

                    # Add second histogram
                    fig.add_trace(
                        px.histogram(
                            pd.DataFrame({
                                f'{compare_name2} - {selected_col2}': df2[selected_col2].dropna(),
                            }),
                            opacity=0.7
                        ).data[0]
                    )

                    fig.update_layout(
                        xaxis_title="값",
                        yaxis_title="빈도",
                        legend_title="데이터셋",
                        barmode='overlay'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Distribution comparison insight
                    st.markdown("### 💡 비교 인사이트")
                    comparison_insight = compare_distributions(df1, selected_col1, df2, selected_col2)
                    st.markdown(comparison_insight)

                    # Individual distribution insights
                    with st.expander("📝 개별 분포 분석", expanded=False):
                        st.markdown(f"**{compare_name1} - {selected_col1}:**")
                        st.markdown(generate_distribution_insight(df1, selected_col1))
                        st.markdown(f"\n**{compare_name2} - {selected_col2}:**")
                        st.markdown(generate_distribution_insight(df2, selected_col2))
                else:
                    st.info("ℹ️ 비교할 숫자형 컬럼이 없습니다.")


def render_sidebar():
    """
    Render the sidebar with API key input and status. (T041-T044)
    """
    with st.sidebar:
        st.header("🤖 AI 설정")

        # T041: API Key input
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Anthropic API Key를 입력하세요. https://console.anthropic.com 에서 발급받을 수 있습니다.",
            key="sidebar_api_key"
        )

        if api_key:
            if validate_api_key(api_key):
                st.session_state.chatbot['api_key'] = api_key
                st.success("✅ API Key 설정됨")
            else:
                st.error("❌ API Key 형식이 올바르지 않습니다")
        else:
            st.info("API Key를 입력하면 AI 챗봇을 사용할 수 있습니다")

        # 지도 설정
        st.subheader("🗺️ 지도 설정")

        with st.form(key="map_settings_form", clear_on_submit=False):
            map_points_input = st.text_input(
                "최대 표시 포인트 수",
                value=str(st.session_state.map_settings['max_points']),
                placeholder="5000",
                help="지도에 표시할 최대 데이터 포인트 수입니다."
            )
            st.caption("기본값: 5000")

            # 숨김 submit 버튼 (Enter 키로 제출)
            submitted = st.form_submit_button("적용", use_container_width=True)

            if submitted:
                try:
                    new_val = int(map_points_input) if map_points_input else 5000
                    if new_val <= 0:
                        st.error("❌ 1 이상의 숫자를 입력해주세요")
                    else:
                        st.session_state.map_settings['max_points'] = new_val
                        st.session_state.map_settings['confirmed'] = True
                        # 지도 캐시 초기화
                        keys_to_delete = [k for k in list(st.session_state.keys()) if k.startswith('map_') and k != 'map_settings']
                        for k in keys_to_delete:
                            del st.session_state[k]
                except ValueError:
                    st.error("❌ 숫자를 입력해주세요")

        # 상태 표시 (form 외부)
        if st.session_state.map_settings['confirmed']:
            st.success(f"✅ 지도 포인트 수: {st.session_state.map_settings['max_points']:,}개")
        else:
            st.info("Enter 키 또는 적용 버튼을 눌러 지도 설정을 적용하세요")

        # T042: Model selection
        st.subheader("모델 선택")
        model_options = {opt['name']: opt['id'] for opt in AI_MODEL_OPTIONS}
        model_descriptions = {opt['name']: opt['description'] for opt in AI_MODEL_OPTIONS}

        selected_model_name = st.selectbox(
            "AI 모델",
            options=list(model_options.keys()),
            help=model_descriptions.get(list(model_options.keys())[0], ""),
            key="sidebar_model"
        )
        st.session_state.chatbot['model'] = model_options[selected_model_name]
        st.caption(model_descriptions[selected_model_name])

        # T043: Token usage display
        st.subheader("📊 토큰 사용량")
        tokens = st.session_state.chatbot['tokens']
        col1, col2 = st.columns(2)
        with col1:
            st.metric("입력", f"{tokens['input']:,}")
        with col2:
            st.metric("출력", f"{tokens['output']:,}")
        st.metric("총계", f"{tokens['total']:,}")

        st.markdown("---")

        # T044: Upload status display
        st.subheader("📁 데이터 업로드 현황")
        uploaded_count = sum(st.session_state.upload_status.values())
        st.progress(uploaded_count / len(DATASET_MAPPING))
        st.caption(f"{uploaded_count} / {len(DATASET_MAPPING)} 데이터셋 업로드됨")

        for key, status in st.session_state.upload_status.items():
            icon = "✅" if status else "⏳"
            st.text(f"{icon} {DATASET_MAPPING[key]['display_name']}")


def render_chatbot_tab():
    """
    Render the chatbot tab for data Q&A. (T045-T050)
    """
    st.header("💬 데이터 질의응답")
    st.markdown("업로드한 데이터셋에 대해 AI에게 질문하세요.")

    # T050: Check API Key
    api_key = st.session_state.chatbot.get('api_key', '')
    if not api_key or not validate_api_key(api_key):
        st.warning("⚠️ 사이드바에서 Anthropic API Key를 먼저 입력해주세요.")
        st.info("""
        **API Key 발급 방법:**
        1. [Anthropic Console](https://console.anthropic.com) 방문
        2. 계정 생성 또는 로그인
        3. API Keys 메뉴에서 새 키 생성
        4. 생성된 키를 사이드바에 입력
        """)
        return

    # Check uploaded datasets
    uploaded_datasets = {
        DATASET_MAPPING[key]['display_name']: key
        for key, uploaded in st.session_state.upload_status.items()
        if uploaded
    }

    if not uploaded_datasets:
        st.info("📤 먼저 **프로젝트 개요** 탭에서 데이터셋을 업로드해주세요.")
        return

    # T046: Dataset selection
    selected_display_name = st.selectbox(
        "분석할 데이터셋 선택:",
        options=list(uploaded_datasets.keys()),
        key="chatbot_dataset"
    )
    selected_dataset_key = uploaded_datasets[selected_display_name]
    st.session_state.chatbot['selected_dataset'] = selected_dataset_key

    # Load selected dataset
    df = load_dataset_from_session(selected_dataset_key)
    if df is None:
        st.error("데이터를 불러올 수 없습니다.")
        return

    # Show dataset summary
    with st.expander("📊 데이터셋 요약", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("행 수", f"{len(df):,}")
        with col2:
            st.metric("컬럼 수", len(df.columns))
        with col3:
            total_cells = len(df) * len(df.columns)
            missing_pct = (df.isnull().sum().sum() / total_cells * 100) if total_cells > 0 else 0
            st.metric("전체 결측률", f"{missing_pct:.1f}%")
        st.dataframe(df.head(3), use_container_width=True)

    st.markdown("---")

    # T038: Get dataset-specific chat history
    chat_history = get_chat_history(selected_dataset_key)

    # T049: Display conversation history
    st.subheader("대화 내역")

    for msg in chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    # T047, T048: Question input and send
    user_question = st.chat_input("데이터에 대해 질문하세요...")

    if user_question:
        # Add user message to history
        chat_history.append({
            'role': 'user',
            'content': user_question
        })

        # Display user message
        with st.chat_message('user'):
            st.markdown(user_question)

        # T047: Generate response with streaming
        with st.chat_message('assistant'):
            try:
                # Create Anthropic client
                client = Anthropic(api_key=api_key)

                # v1.1.2: Create data context with caching
                cache_key = f"context_{selected_dataset_key}_{len(df)}"
                if cache_key not in st.session_state:
                    st.session_state[cache_key] = create_data_context(df, selected_display_name)
                data_context = st.session_state[cache_key]

                # Prepare messages for API
                api_messages = [
                    {'role': m['role'], 'content': m['content']}
                    for m in chat_history
                ]

                # T047: Stream response using st.write_stream
                response_container = st.empty()
                full_response = ""

                stream_gen = stream_chat_response_with_tools(
                    client=client,
                    model=st.session_state.chatbot['model'],
                    messages=api_messages,
                    data_context=data_context,
                    df=df
                )

                # v1.1.3: Collect tool execution info for summary after response
                tool_executions = []
                used_fallback = False

                # T046 v1.1.3: Process stream with usage tracking and tool info collection
                for chunk in stream_gen:
                    if isinstance(chunk, dict):
                        if '__usage__' in chunk:
                            # Update token usage from final message
                            usage = chunk['__usage__']
                            st.session_state.chatbot['tokens']['input'] += usage['input_tokens']
                            st.session_state.chatbot['tokens']['output'] += usage['output_tokens']
                            st.session_state.chatbot['tokens']['total'] += (
                                usage['input_tokens'] + usage['output_tokens']
                            )
                        elif '__tool_end__' in chunk:
                            # Collect tool execution info
                            tool_executions.append(chunk['__tool_end__'])
                        elif '__fallback_start__' in chunk:
                            used_fallback = True
                        # Skip other tool events (batch_start, tool_start, batch_end, fallback_end)
                    else:
                        full_response += chunk
                        response_container.markdown(full_response + "▌")

                response_container.markdown(full_response)

                # v1.1.3: Show tool summary after response (fixes position bug)
                if tool_executions:
                    total_time = sum(t['elapsed'] for t in tool_executions)
                    with st.expander(f"🔧 사용된 도구 ({len(tool_executions)}개, {total_time:.2f}초)", expanded=False):
                        for tool in tool_executions:
                            st.write(f"✅ `{tool['name']}` ({tool['elapsed']:.2f}초)")

                if used_fallback:
                    st.caption("💡 도구 기반 분석이 어려워 일반 응답으로 전환되었습니다.")

                # Add assistant message to history
                chat_history.append({
                    'role': 'assistant',
                    'content': full_response
                })

            except Exception as e:
                error_msg = handle_chat_error(e)
                st.error(error_msg)

    # T039: Clear conversation button (dataset-specific)
    if chat_history:
        if st.button("🗑️ 대화 내역 삭제", key="clear_chat"):
            clear_chat_history(selected_dataset_key)
            st.rerun()


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Render sidebar (T041-T044)
    render_sidebar()

    st.title("📊 대구 공공데이터 시각화")
    st.markdown("""
    대구 공공데이터 시각화 도구에 오신 것을 환영합니다! 이 애플리케이션은
    7개의 공공 데이터셋을 탐색하고 대화형 시각화를 통해 공간 패턴을 발견할 수 있도록 도와줍니다.
    """)

    # Create tabs - T013: 프로젝트 개요 first, T014: tab names, T015: 데이터 질의응답 추가
    # v1.1.3: 교차 데이터 분석 탭 삭제 (10개 → 9개)
    tabs = st.tabs([
        "📖 프로젝트 개요",
        "🎥 CCTV",
        "💡 보안등",
        "🏫 어린이 보호구역",
        "🅿️ 주차장",
        "🚗 사고",
        "📊 훈련 데이터",
        "📋 테스트 데이터",
        "💬 데이터 질의응답"
    ])

    # Tab 0: Project Overview (with upload)
    with tabs[0]:
        render_overview_tab()

    # Tab 1: CCTV
    with tabs[1]:
        render_dataset_tab('cctv', 'CCTV')

    # Tab 2: Security Lights
    with tabs[2]:
        render_dataset_tab('lights', '보안등')

    # Tab 3: Child Protection Zones
    with tabs[3]:
        render_dataset_tab('zones', '어린이 보호구역')

    # Tab 4: Parking Lots
    with tabs[4]:
        render_dataset_tab('parking', '주차장')

    # Tab 5: Accident
    with tabs[5]:
        render_dataset_tab('accident', '사고')

    # Tab 6: Train Data (T014: renamed)
    with tabs[6]:
        render_dataset_tab('train', '훈련 데이터')

    # Tab 7: Test Data (T014: renamed)
    with tabs[7]:
        render_dataset_tab('test', '테스트 데이터')

    # v1.1.3: 교차 데이터 분석 탭 삭제됨 (render_cross_analysis_tab 함수는 유지)

    # Tab 8: Chatbot (T045-T050) - v1.1.3: 탭 인덱스 9 → 8
    with tabs[8]:
        render_chatbot_tab()


if __name__ == "__main__":
    main()
