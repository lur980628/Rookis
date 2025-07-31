import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "data/shelter_data.db"

# ---- Mock Data 정의 ----
mock_shelter_data = pd.DataFrame({
    "shelter_name": ["서울 보호소", "부산 보호소", "대구 보호소", "인천 보호소"],
    "region": ["서울", "부산", "대구", "인천"],
    "lat": [37.5665, 35.1796, 35.8714, 37.4563],
    "lon": [126.9780, 129.0756, 128.6014, 126.7052],
    "species": ["개", "고양이", "개", "고양이"],
    "count": [12, 8, 5, 6],
    "long_term": [3, 2, 1, 2],
    "adopted": [9, 6, 4, 4],
    "image_url": [
        "https://cdn.pixabay.com/photo/2017/02/20/18/03/dog-2083492_960_720.jpg",
        "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg",
        "https://cdn.pixabay.com/photo/2014/12/10/21/01/dog-563282_960_720.jpg",
        "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg"
    ]
})

mock_animal_data = pd.DataFrame([
    {"shelter_name": "서울 보호소", "animal_name": "초코", "species": "개", "age": "2살",
     "image_url": "https://cdn.pixabay.com/photo/2017/02/20/18/03/dog-2083492_960_720.jpg",
     "personality": "사람을 좋아하고 활발해요. 산책과 공놀이가 특기랍니다!",
     "story": "주택가에서 길을 잃은 채 발견되었어요. 주인을 애타게 기다렸지만 나타나지 않아 보호소에 입소하게 되었습니다."},
    {"shelter_name": "서울 보호소", "animal_name": "하양이", "species": "고양이", "age": "1살",
     "image_url": "https://cdn.pixabay.com/photo/2016/02/19/10/00/cat-1209813_960_720.jpg",
     "personality": "조용하고 낯을 조금 가리지만, 친해지면 최고의 애교쟁이가 돼요. 츄르를 가장 좋아해요.",
     "story": "어미를 잃은 형제들과 함께 구조되었습니다. 지금은 건강하게 잘 자라 새로운 가족을 기다리고 있어요."},
    {"shelter_name": "부산 보호소", "animal_name": "콩이", "species": "개", "age": "3살",
     "image_url": "https://cdn.pixabay.com/photo/2014/12/10/21/01/dog-563282_960_720.jpg",
     "personality": "똑똑하고 듬직한 친구입니다. '앉아', '기다려' 같은 기본 훈련이 되어있어요.",
     "story": "이전 보호자님의 건강 문제로 더 이상 키울 수 없게 되어 저희 보호소로 오게 되었습니다. 사람의 손길을 그리워해요."}
])

@st.cache_resource
def get_db_connection():
    """데이터베이스 커넥션을 생성하고 반환합니다."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    """데이터베이스를 초기화하고 목 데이터를 삽입합니다."""
    conn = get_db_connection()
    # 테이블이 이미 있는지 확인
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shelters'")
    if cursor.fetchone() is None:
        with conn:
            mock_shelter_data.to_sql("shelters", conn, index=False, if_exists='replace')
            mock_animal_data.to_sql("animals", conn, index=False, if_exists='replace')

@st.cache_data
def load_data(table_name):
    """지정된 테이블에서 데이터를 로드합니다."""
    conn = get_db_connection()
    data = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    return data

def get_filtered_data(region, species, search_query=""):
    """검색 및 필터 조건에 따라 보호소 데이터를 반환합니다."""
    shelters = load_data("shelters")

    # 1. 검색어 필터링 (동물 이름 기반)
    if search_query:
        animals = load_data("animals")
        # 검색어를 포함하는 동물 찾기 (대소문자 구분 없이)
        matching_animals = animals[animals['animal_name'].str.contains(search_query, case=False, na=False)]
        # 해당 동물들이 있는 보호소의 고유한 이름 목록 가져오기
        shelters_with_matching_animals = matching_animals['shelter_name'].unique()
        # 보호소 목록 필터링
        shelters = shelters[shelters['shelter_name'].isin(shelters_with_matching_animals)]

    # 2. 지역 필터링
    if region != "전체":
        shelters = shelters[shelters["region"] == region]

    # 3. 품종 필터링
    if species:
        shelters = shelters[shelters["species"].isin(species)]
        
    return shelters

def get_animal_details(shelter_name):
    """특정 보호소의 동물 상세 정보를 반환합니다."""
    animals = load_data("animals")
    return animals[animals["shelter_name"] == shelter_name]
