# ==============================================================================
# app.py - Streamlit 메인 애플리케이션
# ==============================================================================
# 이 파일은 전체 웹 애플리케이션의 시작점(entry point)입니다.
# Streamlit을 사용하여 사용자 인터페이스(UI)를 구성하고, 각 탭(페이지)을
# 관리하며, 사용자 입력에 따라 데이터를 필터링하고 시각화하는 역할을 합니다.
#
# [주요 흐름]
# 1. **페이지 설정 및 초기화:** 웹페이지의 기본 설정(제목, 레이아웃)을 지정하고,
#    데이터베이스 연결을 확인하며, 세션 상태(찜 목록 등)를 초기화합니다.
# 2. **사이드바 필터:** 사용자가 데이터를 필터링할 수 있는 모든 컨트롤(날짜, 텍스트,
#    지역, 축종 선택 등)과 정렬 옵션을 하나의 확장 가능한 섹션 안에 배치합니다.
# 3. **데이터 필터링 및 정렬:** 사용자가 선택한 조건과 정렬 옵션에 따라
#    DB에서 로드한 전체 데이터 중 필요한 부분만 필터링하고 정렬합니다.
# 4. **핵심 지표(KPI) 표시:** 필터링된 결과를 바탕으로 주요 수치(보호소 수,
#    보호 동물 수 등)를 계산하여 화면 상단에 표시합니다.
# 5. **탭 구성 및 화면 전환:** 사용자가 선택한 탭에 따라 `map_view`, `stats_view`,
#    `detail_view`, `favorites_view` 모듈의 `show()` 함수를 호출하여
#    해당하는 화면을 동적으로 보여줍니다.
# ==============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 각 탭(페이지)에 해당하는 화면 구성 모듈들을 임포트합니다.
from tabs import map_view, stats_view, detail_view, favorites_view

# 데이터 로딩 및 관리를 위한 함수들을 임포트합니다.
from data_manager import init_db, load_data, get_sido_list, get_sigungu_list, get_kind_list

import streamlit.web.server.component_request_handler as crh

_original_get = crh.ComponentRequestHandler.get

def safe_get(self, abspath):
    try:
        return _original_get(self, abspath)
    except FileNotFoundError:
        return None

crh.ComponentRequestHandler.get = safe_get

# --- 1. 페이지 설정 및 초기화 ---
st.markdown("""
<div style='
    text-align: center;
    color: black;
    font-size: 2.2rem;
    font-weight: bold;
    margin-top: -3rem;
    margin-bottom: 1.5rem;
'>
    Hello Home
</div>
""", unsafe_allow_html=True)

st.set_page_config(page_title="입양 대기 동물 분석", layout="wide")

# --- 2. 앱 전체 및 사이드바 배경 이미지/스타일 설정 ---
st.markdown("""
<style>
/* 전체 앱 배경 설정 */
.stApp {
    background-image: linear-gradient(rgba(0,0,0,0.10), rgba(0,0,0,0.10)),
                     url("https://cdn.pixabay.com/photo/2023/01/30/05/14/pink-7754670_1280.jpg");
    background-size: cover;
    background-repeat: no-repeat;
    background-attachment: fixed;
    background-position: center;
    color: black;
}

/* 사이드바에 들어갈 이미지 스타일 */
.sidebar-img {
    width: 100%;
    border-radius: 10px;
    margin-bottom: 15px;
}

/* 화면 크기 줄어들면 이미지 위치 조정 */
@media (max-width: 768px) {
    .stApp {
        background-position: top;
        background-size: cover;
    }
}

/* 사이드바 배경 이미지 */
[data-testid="stSidebar"] {
    background-image: url("https://cdn.pixabay.com/photo/2023/01/30/05/14/pink-7754670_1280.jpg");
    background-size: cover;
    background-repeat: no-repeat;
    background-position: center;
    color: white;
}

/* 사이드바 내부 콘텐츠 여백 및 텍스트 가독성 확보 */
[data-testid="stSidebar"] > div {
    background-color: rgba(0,0,0,0.1);
    padding: 1rem;
    border-radius: 10px;
}

/* --- 툴바 스타일링 시작 --- */
[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
    box-shadow: none !important;
}

[data-testid="stToolbar"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stToolbar"] > div {
    position: relative;
    z-index: 2;
}

[data-testid="stToolbarActions"] {
    background-color: transparent !important;
}

.stApp h1 {
    font-size: 3.5em;
    color: #6A0DAD;
    text-align: center;
    margin-top: 0;
    text-shadow: 2px 2px 5px rgba(0,0,0,0.3);
}

.main .block-container {
    padding-top: 5rem;
}
/* --- 툴바 스타일링 끝 --- */

</style>
""", unsafe_allow_html=True)

init_db()

if 'favorites' not in st.session_state:
    st.session_state.favorites = []

st.title("🐾 전국 입양 대기 동물 현황")

# --- 2. 사이드바 필터 ---
with st.sidebar.expander("🔍 필터", expanded=True):
    st.markdown("### 🗓️ 공고일 기준")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("시작일", datetime.now() - timedelta(days=30), label_visibility="collapsed")
    with col2:
        end_date = st.date_input("종료일", datetime.now(), label_visibility="collapsed")
    
    st.markdown("### 🐶 동물 정보")
    search_query = st.text_input(
        "이름으로 검색",
        placeholder="예: 초코, 하양이",
        label_visibility="collapsed"
    )

    st.markdown("### 🗺️ 지역 선택")
    col3, col4 = st.columns(2)
    with col3:
        sido_list = get_sido_list()
        sido_names = ["전체"] + [s['name'] for s in sido_list]
        selected_sido_name = st.selectbox("시도", sido_names, label_visibility="collapsed")
    
    with col4:
        selected_sigungu_name = "전체"
        if selected_sido_name != "전체":
            selected_sido_code = next((s['code'] for s in sido_list if s['name'] == selected_sido_name), None)
            if selected_sido_code:
                sigungu_list = get_sigungu_list(selected_sido_code)
                sigungu_names = ["전체"] + [s['name'] for s in sigungu_list]
                selected_sigungu_name = st.selectbox("시군구", sigungu_names, label_visibility="collapsed")
        else:
            st.selectbox("시군구", ["전체"], disabled=True, label_visibility="collapsed")

    kind_list = get_kind_list()
    kind_names = [k['name'] for k in kind_list]
    species_filter = st.multiselect(
        "🐾 축종 선택",
        options=kind_names,
        help="분석할 축종을 선택하세요. 여러 개 선택할 수 있습니다."
    )

    st.markdown("### 🔄 정렬 기준")
    sort_by_option = st.selectbox(
        "정렬",
        options=[
            "최신 공고일 순", 
            "오래된 공고일 순", 
            "나이 어린 순", 
            "나이 많은 순"
        ],
        label_visibility="collapsed"
    )

# --- 3. 데이터 필터링 및 정렬 로직 ---
def get_filtered_data(start_date, end_date, sido, sigungu, species, query, sort_by):
    animals = load_data("animals")
    shelters = load_data("shelters")

    if animals.empty or shelters.empty:
        return pd.DataFrame(), pd.DataFrame(), 0, 0, 0, 0

    # ⭐ 중요: 품종 코드(숫자)를 한글 이름으로 변환하는 로직을
    # `data_manager.py`의 `load_data` 함수로 옮겼기 때문에
    # 아래 코드는 제거합니다.
    # kind_list = get_kind_list()
    # kind_map = {kind['code']: kind['name'] for kind in kind_list}
    # animals['species'] = animals['species'].map(kind_map).fillna(animals['species'])

    # 1. 날짜 필터링 (공고일 기준)
    animals['notice_date'] = pd.to_datetime(animals['notice_date'])
    mask = (animals['notice_date'].dt.date >= start_date) & (animals['notice_date'].dt.date <= end_date)
    filtered_animals = animals[mask]

    # 2. 텍스트 검색 필터링 (동물 이름)
    if query:
        filtered_animals = filtered_animals[filtered_animals['animal_name'].str.contains(query, case=False, na=False)]

    # 3. 축종 필터링
    if species:
        filtered_animals = filtered_animals[filtered_animals['species'].isin(species)]

    # 필터링된 동물 목록을 기반으로, 해당 동물들이 있는 보호소 목록을 구합니다.
    shelter_names_with_animals = filtered_animals['shelter_name'].unique()
    filtered_shelters = shelters[shelters['shelter_name'].isin(shelter_names_with_animals)]

    # 4. 지역 필터링 (보호소 주소 기준)
    if sido != "전체":
        filtered_shelters = filtered_shelters[filtered_shelters["careAddr"].str.startswith(sido, na=False)]
    if sigungu != "전체":
        full_region_name = f"{sido} {sigungu}"
        filtered_shelters = filtered_shelters[filtered_shelters["careAddr"].str.startswith(full_region_name, na=False)]

    # 최종적으로 필터링된 보호소에 소속된 동물들만 다시 추립니다.
    final_animal_shelters = filtered_shelters['shelter_name'].unique()
    final_animals = filtered_animals[filtered_animals['shelter_name'].isin(final_animal_shelters)]

    # 5. 정렬 로직 적용
    if not final_animals.empty:
        if sort_by == "최신 공고일 순":
            final_animals = final_animals.sort_values(by='notice_date', ascending=False)
        elif sort_by == "오래된 공고일 순":
            final_animals = final_animals.sort_values(by='notice_date', ascending=True)
        elif sort_by in ["나이 어린 순", "나이 많은 순"]:
            final_animals['year_of_birth'] = pd.to_numeric(
                final_animals['age'].str.extract('(\d{4})')[0], 
                errors='coerce'
            )
            ascending = (sort_by == "나이 어린 순")
            final_animals = final_animals.sort_values(by='year_of_birth', ascending=ascending, na_position='last')
            final_animals = final_animals.drop(columns=['year_of_birth'])

    shelter_count = filtered_shelters['shelter_name'].nunique()
    animal_count = len(final_animals)
    long_term_count = int(filtered_shelters['long_term'].sum())
    adopted_count = int(filtered_shelters['adopted'].sum())

    return final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count

# 위에서 정의한 함수를 호출하여 필터링된 데이터를 가져옵니다.
final_animals, filtered_shelters, shelter_count, animal_count, long_term_count, adopted_count = get_filtered_data(
    start_date, end_date, selected_sido_name, selected_sigungu_name, species_filter, search_query, sort_by_option
)

# --- 4. KPI 카드 ---
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("보호소 수", shelter_count)
col_b.metric("보호 동물 수", animal_count)
col_c.metric("장기 보호 동물 수", long_term_count)
col_d.metric("입양 완료 수", adopted_count)

# --- 5. 탭 구성 ---
tab_labels = ["📍 지도 & 분석", "📊 통계 차트", "📋 보호소 상세 현황", f"❤️ 찜한 동물 ({len(st.session_state.favorites)})" ]

if "active_tab_idx" not in st.session_state:
    st.session_state.active_tab_idx = 0

active_tab_selection = st.radio(
    "탭 선택",
    tab_labels,
    index=st.session_state.active_tab_idx,
    key="tab_selection",
    horizontal=True,
)

if active_tab_selection != tab_labels[st.session_state.active_tab_idx]:
    st.session_state.active_tab_idx = tab_labels.index(active_tab_selection)

if st.session_state.active_tab_idx == 0:
    map_view.show(filtered_shelters, final_animals, tab_labels)
elif st.session_state.active_tab_idx == 1:
    stats_view.show(filtered_shelters)
elif st.session_state.active_tab_idx == 2:
    detail_view.show(filtered_shelters)
elif st.session_state.active_tab_idx == 3:
    favorites_view.show()