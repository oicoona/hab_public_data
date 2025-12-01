"""
Daegu Public Data Visualization - Streamlit Application

An educational tool for exploring and analyzing public datasets from Daegu.
Provides individual dataset exploration, cross-dataset spatial analysis, and
educational content to help data analysis learners discover insights independently.
"""
import streamlit as st
from streamlit_folium import st_folium
from utils.loader import load_dataset, get_dataset_info
from utils.geo import detect_lat_lng_columns, compute_proximity_stats
from utils.visualizer import plot_numeric_distribution, plot_categorical_distribution, create_folium_map, create_overlay_map

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

    # Try to load dataset
    try:
        df = load_dataset(dataset_name)
    except FileNotFoundError:
        st.warning(f"⚠️ {dataset_display_name} 데이터 파일을 찾을 수 없습니다. data/ 디렉토리에 CSV 파일이 있는지 확인해주세요.")
        st.info("데이터셋 이름을 기반으로 예상되는 파일 위치입니다. 설정 방법은 quickstart.md를 참조하세요.")
        return
    except Exception as e:
        st.error(f"❌ {dataset_display_name} 로딩 오류: {str(e)}")
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
        st.dataframe(df.head(10), width='stretch')

    # Column Information
    with st.expander("📊 컬럼 정보", expanded=False):
        col_info_df = []
        for col in df.columns:
            col_info_df.append({
                '컬럼': col,
                '타입': info['dtypes'][col],
                '결측값 %': f"{info['missing_ratios'][col] * 100:.1f}%"
            })
        st.dataframe(col_info_df, width='stretch')

    # Descriptive Statistics for Numeric Columns
    if not info['numeric_summary'].empty:
        with st.expander("📈 숫자 컬럼 통계", expanded=False):
            st.dataframe(info['numeric_summary'], width='stretch')

    # Visualizations
    st.subheader("시각화")

    # Detect coordinates
    lat_col, lng_col = detect_lat_lng_columns(df)

    # Map Visualization
    if lat_col and lng_col:
        st.markdown("### 🗺️ 지리적 분포")
        st.info(f"감지된 좌표: **{lat_col}** (위도), **{lng_col}** (경도)")

        # Get columns for popup (exclude coordinate columns, limit to first 3 non-numeric)
        popup_candidates = [col for col in df.columns if col not in [lat_col, lng_col]]
        popup_cols = popup_candidates[:3]  # Show first 3 columns in popup

        # Create map
        map_obj = create_folium_map(
            df, lat_col, lng_col,
            popup_cols=popup_cols,
            color='blue',
            name=dataset_display_name
        )

        # Display map
        st_folium(map_obj, width=700, height=500)
    else:
        st.info("ℹ️ 지리 좌표가 감지되지 않았습니다. 이 데이터셋에는 지도 시각화를 사용할 수 없습니다.")

    # Numeric Distributions
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        st.markdown("### 📊 숫자 컬럼 분포")

        # Let user select which numeric column to visualize
        selected_numeric_col = st.selectbox(
            "시각화할 숫자 컬럼 선택:",
            options=numeric_cols,
            key=f"{dataset_name}_numeric_select"
        )

        if selected_numeric_col:
            fig = plot_numeric_distribution(df, selected_numeric_col)
            st.plotly_chart(fig, width='stretch')

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
            st.plotly_chart(fig, width='stretch')


def main():
    """Main application entry point."""
    st.title("📊 대구 공공데이터 시각화")
    st.markdown("""
    대구 공공데이터 시각화 도구에 오신 것을 환영합니다! 이 애플리케이션은
    7개의 공공 데이터셋을 탐색하고 대화형 시각화를 통해 공간 패턴을 발견할 수 있도록 도와줍니다.
    """)

    # Create tabs for all datasets and analysis features
    tabs = st.tabs([
        "🎥 CCTV",
        "💡 보안등",
        "🏫 어린이 보호구역",
        "🅿️ 주차장",
        "🚗 사고",
        "🚂 기차",
        "📝 테스트",
        "🔄 교차 데이터 분석",
        "📖 프로젝트 개요"
    ])

    # Tab 0: CCTV
    with tabs[0]:
        render_dataset_tab('cctv', 'CCTV')

    # Tab 1: Security Lights
    with tabs[1]:
        render_dataset_tab('lights', '보안등')

    # Tab 2: Child Protection Zones
    with tabs[2]:
        render_dataset_tab('zones', '어린이 보호구역')

    # Tab 3: Parking Lots
    with tabs[3]:
        render_dataset_tab('parking', '주차장')

    # Tab 4: Accident
    with tabs[4]:
        render_dataset_tab('accident', '사고')

    # Tab 5: Train
    with tabs[5]:
        render_dataset_tab('train', '기차')

    # Tab 6: Test
    with tabs[6]:
        render_dataset_tab('test', '테스트')

    # Tab 7: Cross-Data Analysis
    with tabs[7]:
        st.header("🔄 교차 데이터 분석")
        st.markdown("""
        여러 데이터셋을 동시에 지도 위에 표시하여 공간적 관계를 분석합니다.
        서로 다른 데이터셋 간의 근접성과 패턴을 발견할 수 있습니다.
        """)

        # Dataset selection
        st.subheader("데이터셋 선택")

        available_datasets = {
            'CCTV': 'cctv',
            '보안등': 'lights',
            '어린이 보호구역': 'zones',
            '주차장': 'parking',
            '사고': 'accident',
            '기차': 'train'
        }

        # Multi-select for datasets
        selected_names = st.multiselect(
            "분석할 데이터셋을 선택하세요 (2개 이상 권장):",
            options=list(available_datasets.keys()),
            default=['CCTV', '보안등']
        )

        if len(selected_names) == 0:
            st.warning("⚠️ 최소 1개 이상의 데이터셋을 선택해주세요.")
        else:
            # Load selected datasets
            datasets_to_overlay = []
            dataset_colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred']
            dataset_icons = ['video-camera', 'lightbulb', 'education', 'car', 'warning-sign', 'road']

            with st.spinner("데이터셋 로딩 중..."):
                for idx, name in enumerate(selected_names):
                    try:
                        df = load_dataset(available_datasets[name])
                        lat_col, lng_col = detect_lat_lng_columns(df)

                        if lat_col and lng_col:
                            # Get popup columns (first 3 non-coordinate columns)
                            popup_candidates = [col for col in df.columns if col not in [lat_col, lng_col]]
                            popup_cols = popup_candidates[:3]

                            datasets_to_overlay.append({
                                'df': df,
                                'lat_col': lat_col,
                                'lng_col': lng_col,
                                'popup_cols': popup_cols,
                                'color': dataset_colors[idx % len(dataset_colors)],
                                'name': name,
                                'icon': dataset_icons[idx % len(dataset_icons)]
                            })
                        else:
                            st.warning(f"⚠️ {name} 데이터셋에서 좌표 정보를 찾을 수 없습니다.")
                    except FileNotFoundError:
                        st.warning(f"⚠️ {name} 데이터 파일을 찾을 수 없습니다.")
                    except Exception as e:
                        st.error(f"❌ {name} 로딩 오류: {str(e)}")

            # Display overlay map
            if datasets_to_overlay:
                st.subheader("🗺️ 통합 지도 시각화")

                # Show legend
                st.markdown("**범례:**")
                legend_cols = st.columns(len(datasets_to_overlay))
                for idx, ds in enumerate(datasets_to_overlay):
                    with legend_cols[idx]:
                        st.markdown(f"🔵 **{ds['name']}** ({len(ds['df']):,}개)")

                # Create and display map
                overlay_map = create_overlay_map(datasets_to_overlay)
                st_folium(overlay_map, width=900, height=600)

                st.info("💡 지도 우측 상단의 레이어 컨트롤을 사용하여 각 데이터셋을 개별적으로 켜고 끌 수 있습니다.")

                # Proximity Analysis
                if len(datasets_to_overlay) >= 2:
                    st.subheader("📊 근접성 분석")
                    st.markdown("""
                    두 데이터셋 간의 공간적 근접성을 분석합니다.
                    기준 데이터셋의 각 지점 주변에 대상 데이터셋의 지점이 몇 개나 있는지 계산합니다.
                    """)

                    col1, col2 = st.columns(2)
                    with col1:
                        base_dataset_name = st.selectbox(
                            "기준 데이터셋:",
                            options=[ds['name'] for ds in datasets_to_overlay]
                        )
                    with col2:
                        target_options = [ds['name'] for ds in datasets_to_overlay if ds['name'] != base_dataset_name]
                        if target_options:
                            target_dataset_name = st.selectbox(
                                "대상 데이터셋:",
                                options=target_options
                            )
                        else:
                            st.info("대상 데이터셋을 선택할 수 없습니다.")
                            target_dataset_name = None

                    if target_dataset_name:
                        # Get base and target datasets
                        base_ds = next(ds for ds in datasets_to_overlay if ds['name'] == base_dataset_name)
                        target_ds = next(ds for ds in datasets_to_overlay if ds['name'] == target_dataset_name)

                        # Distance thresholds
                        thresholds = st.multiselect(
                            "거리 임계값 (km):",
                            options=[0.1, 0.5, 1.0, 2.0, 5.0],
                            default=[0.5, 1.0]
                        )

                        if thresholds and st.button("근접성 분석 실행"):
                            with st.spinner("근접성 계산 중... (대용량 데이터의 경우 시간이 걸릴 수 있습니다)"):
                                proximity_df = compute_proximity_stats(
                                    base_ds['df'],
                                    base_ds['lat_col'],
                                    base_ds['lng_col'],
                                    target_ds['df'],
                                    target_ds['lat_col'],
                                    target_ds['lng_col'],
                                    thresholds=sorted(thresholds)
                                )

                                st.success("✅ 근접성 분석 완료!")

                                # Display statistics
                                st.markdown(f"**분석 결과**: {base_dataset_name} 각 지점 주변의 {target_dataset_name} 개수")

                                # Summary statistics
                                summary_cols = st.columns(len(thresholds))
                                for idx, threshold in enumerate(sorted(thresholds)):
                                    with summary_cols[idx]:
                                        avg_count = proximity_df[str(threshold)].mean()
                                        st.metric(
                                            f"{threshold}km 이내 평균",
                                            f"{avg_count:.1f}개"
                                        )

                                # Detailed statistics table
                                with st.expander("📊 상세 통계", expanded=False):
                                    stats_df = proximity_df.describe()
                                    st.dataframe(stats_df)

                                # Visualization
                                import plotly.express as px

                                # Create histogram for each threshold
                                for threshold in sorted(thresholds):
                                    fig = px.histogram(
                                        proximity_df,
                                        x=str(threshold),
                                        title=f"{threshold}km 이내 {target_dataset_name} 개수 분포",
                                        labels={str(threshold): f"{target_dataset_name} 개수"},
                                        marginal="box"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 좌표 정보가 있는 데이터셋이 없습니다.")

    # Tab 8: Project Overview
    with tabs[8]:
        st.header("📖 프로젝트 개요")

        # Project Introduction
        st.markdown("""
        ## 대구 공공데이터 시각화 프로젝트

        이 프로젝트는 대구시의 다양한 공공 데이터를 탐색하고 분석할 수 있는 대화형 웹 애플리케이션입니다.
        데이터 분석을 학습하는 사용자들이 실제 공공 데이터를 통해 인사이트를 발견하고
        데이터 시각화 기술을 익힐 수 있도록 설계되었습니다.
        """)

        # Key Features
        st.subheader("🎯 주요 기능")
        feature_col1, feature_col2 = st.columns(2)

        with feature_col1:
            st.markdown("""
            **개별 데이터셋 탐색**
            - 7개의 공공 데이터셋 제공
            - 기본 통계 및 데이터 미리보기
            - 대화형 차트 및 그래프
            - 지리적 분포 지도 시각화
            """)

            st.markdown("""
            **교차 데이터 분석**
            - 여러 데이터셋 동시 시각화
            - 공간적 관계 분석
            - 근접성 통계 계산
            """)

        with feature_col2:
            st.markdown("""
            **사용자 친화적 인터페이스**
            - 직관적인 탭 기반 네비게이션
            - 반응형 레이아웃
            - 실시간 데이터 필터링
            - 다양한 시각화 옵션
            """)

            st.markdown("""
            **교육적 가치**
            - 실제 공공 데이터 활용
            - 데이터 분석 기술 학습
            - 시각화 모범 사례
            """)

        # Available Datasets
        st.subheader("📊 사용 가능한 데이터셋")

        dataset_info = [
            {
                "이름": "CCTV",
                "설명": "대구시 CCTV 설치 위치 정보",
                "주요 컬럼": "설치 위치, 좌표, 관리 기관",
                "활용": "안전 인프라 분석, 범죄 예방 연구"
            },
            {
                "이름": "보안등",
                "설명": "대구시 보안등 설치 정보",
                "주요 컬럼": "설치 위치, 좌표, 등 종류",
                "활용": "야간 안전 분석, 조명 인프라 연구"
            },
            {
                "이름": "어린이 보호구역",
                "설명": "학교 주변 어린이 보호구역 정보",
                "주요 컬럼": "구역 위치, 좌표, 학교명",
                "활용": "교통 안전 분석, 보호구역 효과성 연구"
            },
            {
                "이름": "주차장",
                "설명": "대구시 공영 및 민영 주차장 정보",
                "주요 컬럼": "주차장 위치, 좌표, 주차 면수",
                "활용": "주차 인프라 분석, 교통 정책 연구"
            },
            {
                "이름": "사고",
                "설명": "전국 교통사고 데이터",
                "주요 컬럼": "사고 위치, 날짜, 사상자 수",
                "활용": "교통 안전 분석, 위험 지역 식별"
            },
            {
                "이름": "기차",
                "설명": "기차역 및 노선 정보",
                "주요 컬럼": "역명, 좌표, 노선 정보",
                "활용": "대중교통 접근성 분석"
            },
            {
                "이름": "테스트",
                "설명": "샘플 데이터셋 (테스트용)",
                "주요 컬럼": "다양한 테스트 컬럼",
                "활용": "기능 테스트 및 데모"
            }
        ]

        # Display as expandable sections
        for dataset in dataset_info:
            with st.expander(f"**{dataset['이름']}** - {dataset['설명']}"):
                st.markdown(f"**주요 컬럼**: {dataset['주요 컬럼']}")
                st.markdown(f"**활용 예시**: {dataset['활용']}")

        # How to Use
        st.subheader("📚 사용 방법")

        st.markdown("""
        ### 1️⃣ 개별 데이터셋 탐색
        1. 상단 탭에서 원하는 데이터셋을 선택합니다
        2. 기본 통계와 데이터 미리보기를 확인합니다
        3. 지도에서 지리적 분포를 확인합니다
        4. 숫자형/범주형 컬럼을 선택하여 분포를 시각화합니다

        ### 2️⃣ 교차 데이터 분석
        1. "교차 데이터 분석" 탭으로 이동합니다
        2. 비교할 데이터셋을 2개 이상 선택합니다
        3. 통합 지도에서 여러 데이터셋의 공간적 관계를 확인합니다
        4. 레이어 컨트롤을 사용하여 개별 데이터셋을 켜고 끌 수 있습니다
        5. 근접성 분석을 통해 두 데이터셋 간의 거리 관계를 분석합니다

        ### 3️⃣ 인사이트 발견하기
        - 🔍 **패턴 찾기**: 데이터의 지리적 분포에서 패턴을 찾아보세요
        - 📈 **상관관계 분석**: 여러 데이터셋을 겹쳐 상관관계를 탐색하세요
        - 🎯 **가설 검증**: 궁금한 점을 가설로 만들고 데이터로 검증해보세요
        - 💡 **질문하기**: "왜 이런 패턴이 나타날까?" 질문을 던져보세요
        """)

        # Technical Information
        st.subheader("🔧 기술 스택")

        tech_col1, tech_col2, tech_col3 = st.columns(3)

        with tech_col1:
            st.markdown("""
            **프론트엔드**
            - Streamlit
            - Plotly
            - Folium
            """)

        with tech_col2:
            st.markdown("""
            **데이터 처리**
            - Pandas
            - NumPy
            """)

        with tech_col3:
            st.markdown("""
            **기타**
            - Python 3.10+
            - streamlit-folium
            """)

        # Tips and Best Practices
        st.subheader("💡 유용한 팁")

        tip_col1, tip_col2 = st.columns(2)

        with tip_col1:
            st.info("""
            **데이터 탐색 팁**
            - 먼저 데이터 미리보기로 컬럼 구조를 파악하세요
            - 결측값 비율을 확인하여 데이터 품질을 평가하세요
            - 지도 시각화는 최대 5,000개 지점으로 샘플링됩니다
            """)

        with tip_col2:
            st.warning("""
            **성능 고려사항**
            - 대용량 데이터셋은 로딩에 시간이 걸릴 수 있습니다
            - 근접성 분석은 계산 집약적이므로 인내심을 가지세요
            - 여러 레이어를 동시에 표시하면 지도가 느려질 수 있습니다
            """)

        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center'>
            <p><strong>대구 공공데이터 시각화</strong></p>
            <p>데이터로 세상을 이해하는 즐거움을 경험하세요</p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
