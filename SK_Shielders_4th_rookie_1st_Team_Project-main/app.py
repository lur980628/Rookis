import streamlit as st
from tabs import map_view, stats_view, detail_view, favorites_view
from data_manager import init_db, get_filtered_data

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
    color: black;  /* 글자색을 진하게 설정 */
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
    color: white;  /* 텍스트 색상 흰색으로 */
}

/* 사이드바 내부 콘텐츠 여백 및 텍스트 가독성 확보 */
[data-testid="stSidebar"] > div {
    background-color: rgba(0,0,0,0.1);  /* 반투명 검정 배경 추가 */
    padding: 1rem;
    border-radius: 10px;
}

/* --- 툴바 스타일링 시작 --- */

/* Streamlit의 전체 헤더 영역을 투명하게 만듭니다.
   이 요소가 툴바를 포함하며, 배경색을 가장 효과적으로 제어할 수 있습니다. */
[data-testid="stHeader"] {
    background: transparent !important; /* 배경을 완전히 투명하게 설정 */
    border-bottom: none !important; /* 하단 테두리 제거 */
    box-shadow: none !important;     /* 그림자 제거 */
}

/* 기존 툴바 요소 자체도 투명하게 유지합니다. (혹시 모를 내부 배경 방지) */
[data-testid="stToolbar"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}


/* 툴바의 기존 버튼(메뉴, 배포 등)들이 텍스트와 겹치지 않도록 위치와 z-index를 조정합니다. */
/* Streamlit의 내부 버튼 컨테이너에 높은 z-index를 부여하여 텍스트 위에 표시되도록 합니다. */
[data-testid="stToolbar"] > div {
    position: relative;
    z-index: 2; /* 버튼들이 'Hello Home' 텍스트 위에 오도록 설정 */
}

/* stToolbarActions (Streamlit 내부의 빈 div)도 투명화 */
[data-testid="stToolbarActions"] {
    background-color: transparent !important;
}

/* 메인 타이틀 (st.title) 스타일 (Hello Home이 툴바에 있으므로, 이 타이틀은 툴바 아래에 위치) */
.stApp h1 { /* st.title은 h1 태그로 렌더링됩니다. */
    font-size: 3.5em; /* 글자 크기 조정 */
    color: #6A0DAD; /* 보라색 계열 */
    text-align: center; /* 가운데 정렬 */
    margin-top: 0; /* 위 여백 제거 */
    text-shadow: 2px 2px 5px rgba(0,0,0,0.3); /* 가독성을 위한 그림자 */
}

/* 메인 콘텐츠가 헤더 아래로 충분히 내려오도록 패딩을 추가합니다.
   'Hello Home' 텍스트가 메인 콘텐츠와 겹치지 않도록 공간을 확보합니다. */
.main .block-container {
    padding-top: 5rem; /* 필요에 따라 이 값을 조절하세요 */
}

/* --- 툴바 스타일링 끝 --- */

</style>
""", unsafe_allow_html=True)

# --- 3. 데이터베이스 및 세션 상태 초기화 ---
init_db() # DB 초기화 (최초 실행 시 테이블 생성 및 데이터 삽입)

if 'favorites' not in st.session_state:
    st.session_state.favorites = [] # 세션 상태 초기화 (찜 목록)

# --- 4. 앱 제목 표시 (Hello Home은 CSS로 툴바에 삽입되었으므로 여기서는 제거) ---
# st.header("Hello Home") # 이 줄은 이제 필요 없습니다.
st.title("🐾 전국 입양 대기 동물 현황")

# --- 5. 사이드바 필터 섹션 ---
st.sidebar.header("🔍 검색 및 필터")

search_query = st.sidebar.text_input(
    "동물 이름으로 검색",
    placeholder="예: 초코, 하양이",
    help="검색어와 일치하는 이름을 가진 동물이 있는 보호소를 찾습니다."
)

st.sidebar.markdown("---") # 구분선

region_filter = st.sidebar.selectbox(
    "지역 선택",
    options=["전체"] + ["서울", "부산", "대구", "인천"],
    help="분석할 지역을 선택하세요."
)

species_filter = st.sidebar.multiselect(
    "품종 선택",
    options=["개", "고양이"],
    help="분석할 품종을 선택하세요. 여러 개 선택할 수 있습니다."
)

# 필터링된 데이터 가져오기
filtered_data = get_filtered_data(region_filter, species_filter, search_query)

# --- 6. KPI 카드 (핵심 성과 지표) ---
col_a, col_b, col_c, col_d = st.columns(4)
col_a.metric("보호소 수", filtered_data['shelter_name'].nunique())
col_b.metric("보호 동물 수", int(filtered_data['count'].sum()))
col_c.metric("장기 보호 동물 수", int(filtered_data['long_term'].sum()))
col_d.metric("입양 완료 수", int(filtered_data['adopted'].sum()))

# --- 7. 탭 구성 및 탭 전환 로직 ---
tab_labels = ["📍 지도 & 분석", "� 통계 차트", "📋 보호소 상세 현황", f"❤️ 찜한 동물 ({len(st.session_state.favorites)})" ]

# st.session_state를 사용하여 탭 인덱스 관리
if "active_tab_idx" not in st.session_state:
    st.session_state.active_tab_idx = 0 # 기본값은 첫 번째 탭

# map_view에서 보낸 신호(active_tab)를 받아 인덱스 업데이트
# 그리고 selected_shelter_name도 함께 처리
if "active_tab" in st.session_state:
    try:
        st.session_state.active_tab_idx = tab_labels.index(st.session_state.active_tab)
    except ValueError:
        st.session_state.active_tab_idx = 0
    del st.session_state.active_tab # 신호 처리 후 삭제
    st.rerun() # 탭 변경을 위해 재실행

# st.radio를 사용하여 탭 UI 생성
active_tab = st.radio(
    "탭 선택",
    tab_labels,
    index=st.session_state.active_tab_idx,
    key="tab_selection",
    horizontal=True,
)

# --- 8. 선택된 탭에 따라 해당 모듈의 함수 호출 ---
if active_tab.startswith("📍 지도 & 분석"):
    map_view.show(filtered_data)
elif active_tab.startswith("📊 통계 차트"):
    stats_view.show(filtered_data)
elif active_tab.startswith("📋 보호소 상세 현황"):
    # map_view에서 전달된 selected_shelter_name이 있다면, detail_view에 전달
    selected_shelter_from_map = st.session_state.get('selected_shelter_name', None)
    detail_view.show(filtered_data, selected_shelter_from_map=selected_shelter_from_map)
    # 사용 후 초기화
    if 'selected_shelter_name' in st.session_state:
        del st.session_state.selected_shelter_name
elif active_tab.startswith("❤️ 찜한 동물"):
    favorites_view.show()