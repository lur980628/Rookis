# ==============================================================================
# stats_view.py - 통계 차트 탭
# ==============================================================================
# 이 파일은 필터링된 데이터를 기반으로 다양한 통계 차트를 생성하여
# 사용자에게 인사이트를 제공하는 화면을 구성합니다.
# Plotly Express 라이브러리를 사용하여 인터랙티브한 차트를 생성합니다.
#
# [주요 기능]
# 1. **데이터 준비:** `app.py`에서 전달받은 필터링된 보호소 데이터
#    (`filtered_data`)를 기반으로 각 차트에 맞는 형태로 데이터를 가공(group by, sum 등)합니다.
# 2. **품종별 보호 동물 수 막대 차트:**
#    - 보호소별로 집계된 주요 품종(`species`)과 동물 수(`count`)를 그룹화하여
#      전체 품종별 총 동물 수를 계산합니다.
#    - `px.bar`를 사용하여 막대 차트를 생성하고, 각 막대에 수치를 표시하여
#      가독성을 높입니다.
# 3. **지역별 장기 보호 동물 비율 파이 차트:**
#    - 보호소 주소(`careAddr`)에서 시/도 정보만 추출하여 새로운 'sido' 컬럼을 만듭니다.
#    - 시/도별로 장기 보호 동물 수(`long_term`)의 합계를 계산합니다.
#    - `px.pie`를 사용하여 지역별 장기 보호 동물의 분포를 한눈에 파악할 수 있는
#      파이 차트를 생성합니다.
#    - 단일 지역만 선택된 경우 비율 비교가 의미 없으므로, 차트를 표시하지 않고
#      안내 메시지를 보여줍니다.
# ==============================================================================

import streamlit as st
import plotly.express as px

def show(filtered_data):
    """
    '통계 차트' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다.

    Args:
        filtered_data (pd.DataFrame): app.py에서 필터링된 보호소 데이터.
    """
    st.subheader("📊 통계 차트")

    # 필터링된 데이터가 없는 경우, 경고 메시지를 표시하고 함수를 종료합니다.
    if filtered_data.empty:
        st.warning("표시할 데이터가 없습니다. 필터 조건을 변경해보세요.")
        return

    # --- 1. 품종별 보호 동물 수 (막대 차트) ---
    st.markdown("#### 품종별 보호 동물 수")
    
    # 'species' 컬럼으로 그룹화하고, 각 품종의 'count'를 합산합니다.
    species_chart_data = filtered_data.groupby("species")["count"].sum().reset_index()
    
    # Plotly Express를 사용하여 막대 차트를 생성합니다.
    fig_bar = px.bar(
        species_chart_data,
        x="species",        # x축: 품종
        y="count",          # y축: 동물 수
        color="species",    # 각 막대를 품종별로 다른 색으로 표시
        text="count",       # 막대 위에 수치(count)를 텍스트로 표시
        template="plotly_white" # 깔끔한 흰색 배경의 템플릿 사용
    )
    fig_bar.update_traces(textposition="outside") # 텍스트를 막대 바깥쪽에 표시
    fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=10)) # 범례는 숨기고, 차트 여백을 조절
    st.plotly_chart(fig_bar, use_container_width=True) # Streamlit에 차트를 렌더링

    # --- 2. 지역별 장기 보호 동물 비율 (파이 차트) ---
    st.markdown("#### 지역별 장기 보호 동물 비율")
    
    # 원본 데이터를 복사하여 작업합니다 (원본 데이터 보존).
    chart_data = filtered_data.copy()
    # 'careAddr' 컬럼에서 첫 단어(시/도)를 추출하여 'sido' 컬럼을 생성합니다.
    chart_data['sido'] = chart_data['careAddr'].str.split().str[0]
    
    # 여러 지역이 선택되어 비교가 의미 있을 때만 파이 차트를 그립니다.
    if chart_data['sido'].nunique() > 1:
        # 'sido' 컬럼으로 그룹화하고, 각 지역의 'long_term' 수를 합산합니다.
        long_term_chart_data = chart_data.groupby("sido")["long_term"].sum().reset_index()
        
        # Plotly Express를 사용하여 파이 차트를 생성합니다.
        fig_pie = px.pie(
            long_term_chart_data,
            values="long_term", # 각 조각의 크기: 장기 보호 동물 수
            names="sido",      # 각 조각의 이름: 시/도
            template="plotly_white",
            title="시도별 장기 보호 동물 비율"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        # 단일 지역만 선택되었을 경우 안내 메시지를 표시합니다.
        st.info("여러 지역을 함께 선택해야 비율 차트를 볼 수 있습니다.")