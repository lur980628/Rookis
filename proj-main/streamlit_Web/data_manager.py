# ==============================================================================
# data_manager.py - 데이터 관리 모듈
# ==============================================================================
# 이 파일은 애플리케이션의 모든 데이터 관련 작업을 총괄합니다.
# 데이터베이스 연결, 데이터 로딩, 외부 API 호출 및 데이터 캐싱 등
# 데이터의 흐름을 관리하는 핵심적인 역할을 수행합니다.
#
# [주요 기능]
# 1. **설정 관리 (`get_config`):** `config.ini` 파일에서 DB 정보 및 API 키를
#     안전하게 읽어옵니다.
# 2. **데이터베이스 연결 (`get_db_engine`):** SQLAlchemy를 사용하여 데이터베이스
#     연결 엔진을 생성하고, `@st.cache_resource`를 통해 연결을 재사용하여
#     성능을 최적화합니다.
# 3. **데이터 로딩 (`load_data`):** 데이터베이스의 특정 테이블에서 데이터를
#     Pandas DataFrame으로 읽어오며, `@st.cache_data`를 통해 이미 로드된
#     데이터는 다시 로드하지 않고 캐시된 버전을 사용합니다.
# 4. **외부 API 연동:**
#     - `fetch_api_data_powershell`: PowerShell을 사용하여 안정적으로 외부 API의
#       XML 데이터를 가져옵니다. (Windows 환경에 특화된 방식)
#     - `get_sido_list`, `get_sigungu_list`, `get_kind_list`: 공공데이터포털 API를
#       호출하여 시/도, 시/군/구, 품종 목록을 가져옵니다. 이 데이터 역시 캐싱됩니다.
# 5. **데이터베이스 초기화 (`init_db`):** 앱 시작 시 데이터베이스 테이블이
#     존재하는지 확인하고, 없을 경우 경고 메시지를 표시합니다.
# ==============================================================================

import pandas as pd
import streamlit as st
import configparser
import os
from sqlalchemy import create_engine, text
import xml.etree.ElementTree as ET
from urllib.parse import quote
import subprocess
import tempfile
import requests # 추가: 이미지를 다운로드하기 위해 requests 라이브러리 import

# --- 경로 및 설정 로드 ---
current_script_path = os.path.abspath(__file__)
streamlit_web_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(streamlit_web_dir)
CONFIG_PATH = os.path.join(project_root, 'config.ini')

def get_config():
    """`config.ini` 설정 파일을 읽어와 ConfigParser 객체로 반환합니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        st.error("설정 파일(config.ini)을 찾을 수 없습니다.")
        return None
    config.read(CONFIG_PATH)
    return config

# --- DB 및 API 클라이언트 ---
@st.cache_resource
def get_db_engine():
    """설정 파일을 바탕으로 SQLAlchemy DB 엔진을 생성하고 반환합니다."""
    config = get_config()
    if not config or 'DB' not in config:
        st.error("DB 설정이 올바르지 않습니다.")
        return None
    db_config = config['DB']
    try:
        engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config.get('port', 3306)}/{db_config['database']}"
        )
        with engine.connect() as _:
            pass
        return engine
    except Exception as e:
        st.error(f"DB 연결에 실패했습니다: {e}")
        return None

def get_api_key():
    """설정 파일에서 공공데이터포털 API 서비스 키를 가져옵니다."""
    config = get_config()
    if not config or 'API' not in config:
        st.error("API 키 설정이 올바르지 않습니다.")
        return None
    return config['API']['service_key']

def fetch_api_data_powershell(url):
    """PowerShell을 사용하여 API 데이터를 가져오고 XML Element로 반환합니다."""
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        if not xml_data:
            return None
        return ET.fromstring(xml_data)

    except subprocess.CalledProcessError as e:
        st.warning(f"PowerShell을 통한 데이터 다운로드 중 오류 발생: {e.stderr}")
        return None
    except Exception as e:
        st.warning(f"API 데이터 처리 중 알 수 없는 오류 발생: {e}")
        return None
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 이미지 다운로드 함수 추가 ---
def download_image(url, desertion_no):
    """
    주어진 URL에서 이미지를 다운로드하여 'images' 폴더에 저장하고 로컬 경로를 반환합니다.
    """
    if not url:
        return None
    
    images_dir = "images"
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    file_extension = url.split('.')[-1].split('?')[0]
    filename = f"{desertion_no}.{file_extension}"
    filepath = os.path.join(images_dir, filename)

    if os.path.exists(filepath):
        return filepath
        
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"이미지 다운로드 성공: {url} -> {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"이미지 다운로드 실패: {url} - {e}")
        return None

# --- API 연동 함수 (수정 없음) ---
@st.cache_data
def get_sido_list():
    """공공데이터 API를 통해 전국의 시/도 목록을 가져옵니다."""
    api_key = get_api_key()
    if not api_key:
        return []
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sido_v2"
    url = f"{endpoint}?serviceKey={encoded_key}&numOfRows=100&_type=xml"
    root = fetch_api_data_powershell(url)
    if root is None:
        return []
    sido_list = []
    for item in root.findall('.//item'):
        sido_list.append({"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
    return sido_list

@st.cache_data
def get_sigungu_list(sido_code):
    """선택된 시/도 코드에 해당하는 시/군/구 목록을 가져옵니다."""
    if not sido_code:
        return []
    api_key = get_api_key()
    if not api_key:
        return []
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sigungu_v2"
    url = f"{endpoint}?serviceKey={encoded_key}&upr_cd={sido_code}&_type=xml"
    root = fetch_api_data_powershell(url)
    if root is None:
        return []
    sigungu_list = []
    for item in root.findall('.//item'):
        sigungu_list.append({"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
    return sigungu_list

@st.cache_data
def get_kind_list(upkind_code=''):
    """공공데이터 API를 통해 축종 및 품종 목록을 가져옵니다."""
    api_key = get_api_key()
    if not api_key:
        return []
    
    encoded_key = quote(api_key, safe='/')
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/kind_v2"
    
    codes_to_fetch = [upkind_code] if upkind_code else ['417000', '422400', '429900']
    
    all_kinds = []
    for code in codes_to_fetch:
        page_no = 1
        while True:
            url = f"{endpoint}?serviceKey={encoded_key}&up_kind_cd={code}&pageNo={page_no}&numOfRows=1000&_type=xml"
            root = fetch_api_data_powershell(url)
            if root is None or root.find('.//resultCode').text != '00':
                break

            items_in_page = root.findall('.//item')
            if not items_in_page:
                break

            for item in items_in_page:
                all_kinds.append({"code": item.findtext("kindCd"), "name": item.findtext("kindNm")})
            
            total_count = int(root.find('.//totalCount').text)
            if len(all_kinds) >= total_count:
                break
            page_no += 1
            
    return list({v['code']:v for v in all_kinds}.values())

def init_db():
    """애플리케이션 시작 시 DB 연결 및 테이블 존재 여부를 확인합니다."""
    engine = get_db_engine()
    if engine is None:
        st.error("DB 엔진을 초기화할 수 없어 앱 실행이 불가능합니다.")
        return
    try:
        with engine.connect() as conn:
            cursor = conn.execute(text("SHOW TABLES LIKE 'shelters'"))
            if cursor.fetchone() is None:
                st.warning("'shelters' 테이블이 DB에 존재하지 않습니다. `update_data.py`를 먼저 실행해주세요.")
    except Exception as e:
        st.error(f"DB 초기화 중 오류 발생: {e}")

@st.cache_data
def load_data(table_name):
    """데이터베이스에서 지정된 테이블의 모든 데이터를 DataFrame으로 로드하고 전처리합니다."""
    engine = get_db_engine()
    if engine is None:
        return pd.DataFrame()
    try:
        with engine.connect() as conn:
            data = pd.read_sql(f"SELECT * FROM {table_name}", conn)

            if table_name == 'shelters':
                data['lat'] = pd.to_numeric(data['lat'], errors='coerce')
                data['lon'] = pd.to_numeric(data['lon'], errors='coerce')
            
            # --- 'animals' 테이블에 대한 이미지 및 품종 전처리 로직 ---
            if table_name == 'animals':
                # 1. 품종 코드(숫자)를 한글 이름으로 변환
                kind_list_data = get_kind_list()
                kind_map = {k['code']: k['name'] for k in kind_list_data}
                data['species'] = data['species'].map(kind_map).fillna('기타')
                
                # 2. 이미지를 다운로드하여 로컬 경로를 저장
                data['image_path'] = data.apply(
                    lambda row: download_image(row['image_url'], row['desertion_no']),
                    axis=1
                )
            
        return data
    except Exception as e:
        st.warning(f"'{table_name}' 테이블 로딩 중 오류: {e}. 빈 데이터를 반환합니다.")
        return pd.DataFrame()

def get_filtered_data(sido_name, sigungu_name, species, search_query=""):
    shelters = load_data("shelters")
    return shelters

def get_animal_details(shelter_name):
    """특정 보호소 이름에 해당하는 동물들의 상세 정보를 조회합니다."""
    animals = load_data("animals")
    if animals.empty:
        return pd.DataFrame()
    return animals[animals["shelter_name"] == shelter_name]