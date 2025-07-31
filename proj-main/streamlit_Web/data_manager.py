# ==============================================================================
# data_manager.py - 데이터 관리 모듈
# ==============================================================================
# 이 파일은 애플리케이션의 모든 데이터 관련 작업을 총괄합니다.
# 데이터베이스 연결, 데이터 로딩, 외부 API 호출 및 데이터 캐싱 등
# 데이터의 흐름을 관리하는 핵심적인 역할을 수행합니다.
#
# [주요 기능]
# 1. **설정 관리 (`get_config`):** `config.ini` 파일에서 DB 정보 및 API 키를
#    안전하게 읽어옵니다.
# 2. **데이터베이스 연결 (`get_db_engine`):** SQLAlchemy를 사용하여 데이터베이스
#    연결 엔진을 생성하고, `@st.cache_resource`를 통해 연결을 재사용하여
#    성능을 최적화합니다.
# 3. **데이터 로딩 (`load_data`):** 데이터베이스의 특정 테이블에서 데이터를
#    Pandas DataFrame으로 읽어오며, `@st.cache_data`를 통해 이미 로드된
#    데이터는 다시 로드하지 않고 캐시된 버전을 사용합니다.
# 4. **외부 API 연동:**
#    - `fetch_api_data_powershell`: PowerShell을 사용하여 안정적으로 외부 API의
#      XML 데이터를 가져옵니다. (Windows 환경에 특화된 방식)
#    - `get_sido_list`, `get_sigungu_list`, `get_kind_list`: 공공데이터포털 API를
#      호출하여 시/도, 시/군/구, 품종 목록을 가져옵니다. 이 데이터 역시 캐싱됩니다.
# 5. **데이터베이스 초기화 (`init_db`):** 앱 시작 시 데이터베이스 테이블이
#    존재하는지 확인하고, 없을 경우 경고 메시지를 표시합니다.
# ==============================================================================

import pandas as pd
import streamlit as st
import configparser
import os
from sqlalchemy import create_engine
import xml.etree.ElementTree as ET
from urllib.parse import quote
import subprocess
import tempfile

# --- 경로 및 설정 로드 ---
# 스크립트의 위치를 기준으로 프로젝트 루트와 설정 파일의 절대 경로를 계산합니다.
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

# `@st.cache_resource` 데코레이터:
# 이 함수가 반환하는 리소스(DB 엔진)를 캐시에 저장하고 재사용합니다.
# DB 연결과 같은 무거운 작업을 반복적으로 수행하는 것을 방지하여 앱 성능을 향상시킵니다.
@st.cache_resource
def get_db_engine():
    """설정 파일을 바탕으로 SQLAlchemy DB 엔진을 생성하고 반환합니다."""
    config = get_config()
    if not config or 'DB' not in config:
        st.error("DB 설정이 올바르지 않습니다.")
        return None
    db_config = config['DB']
    try:
        # f-string을 사용하여 연결 문자열을 생성합니다.
        engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config.get('port', 3306)}/{db_config['database']}"
        )
        # 연결 테스트
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
    # 임시 파일을 생성하여 API 응답을 저장합니다.
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    try:
        # PowerShell의 WebClient를 사용하여 지정된 URL에서 파일을 다운로드합니다.
        # 이 방식은 특정 네트워크 환경에서 requests보다 안정적일 수 있습니다.
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        # 다운로드된 임시 파일을 읽고 XML로 파싱합니다.
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
        # 작업 완료 후 임시 파일을 반드시 삭제합니다.
        if os.path.exists(temp_path):
            os.remove(temp_path)

# `@st.cache_data` 데코레이터:
# 이 함수가 반환하는 데이터(여기서는 시/도 목록)를 캐시에 저장합니다.
# 동일한 인자로 함수가 다시 호출될 때, 실제 함수를 실행하지 않고 캐시된 결과를 즉시 반환합니다.
# API 호출 횟수를 줄여 앱의 응답 속도를 크게 향상시킵니다.
@st.cache_data
def get_sido_list():
    """공공데이터 API를 통해 전국의 시/도 목록을 가져옵니다."""
    api_key = get_api_key()
    if not api_key:
        return []
    encoded_key = quote(api_key, safe='/') # URL에 포함될 수 있도록 API 키를 인코딩합니다.
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
    
    # 특정 축종 코드가 없으면 개, 고양이, 기타를 모두 조회합니다.
    codes_to_fetch = [upkind_code] if upkind_code else ['417000', '422400', '429900']
    
    all_kinds = []
    for code in codes_to_fetch:
        # API가 페이징을 지원하므로, 모든 데이터를 가져오기 위해 반복문을 사용합니다.
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
            
    # 중복된 품종을 제거하고 반환합니다.
    return list({v['code']:v for v in all_kinds}.values())

def init_db():
    """애플리케이션 시작 시 DB 연결 및 테이블 존재 여부를 확인합니다."""
    engine = get_db_engine()
    if engine is None:
        st.error("DB 엔진을 초기화할 수 없어 앱 실행이 불가능합니다.")
        return
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            # 'shelters' 테이블이 존재하는지 확인하는 쿼리를 실행합니다.
            cursor = conn.execute(text("SHOW TABLES LIKE 'shelters'"))
            if cursor.fetchone() is None:
                st.warning("'shelters' 테이블이 DB에 존재하지 않습니다. `update_data.py`를 먼저 실행해주세요.")
    except Exception as e:
        st.error(f"DB 초기화 중 오류 발생: {e}")

@st.cache_data
def load_data(table_name):
    """데이터베이스에서 지정된 테이블의 모든 데이터를 DataFrame으로 로드합니다."""
    engine = get_db_engine()
    if engine is None:
        return pd.DataFrame() # DB 연결 실패 시 빈 DataFrame 반환
    try:
        with engine.connect() as conn:
            data = pd.read_sql(f"SELECT * FROM {table_name}", conn)
            # 'shelters' 테이블의 경우, 위도(lat)와 경도(lon) 컬럼을 숫자 타입으로 변환합니다.
            if table_name == 'shelters':
                data['lat'] = pd.to_numeric(data['lat'], errors='coerce')
                data['lon'] = pd.to_numeric(data['lon'], errors='coerce')
        return data
    except Exception as e:
        st.warning(f"'{table_name}' 테이블 로딩 중 오류: {e}. 빈 데이터를 반환합니다.")
        return pd.DataFrame()

# 아래 함수들은 app.py의 get_filtered_data 함수와 기능이 중복되어 현재는 사용되지 않는 것으로 보입니다.
# 코드 통일성을 위해 app.py의 필터링 로직을 사용하고, 이 부분은 제거하거나 리팩토링하는 것을 고려해볼 수 있습니다.
def get_filtered_data(sido_name, sigungu_name, species, search_query=""):
    shelters = load_data("shelters")
    # ... (이하 로직은 app.py의 것과 유사)
    return shelters

def get_animal_details(shelter_name):
    """특정 보호소 이름에 해당하는 동물들의 상세 정보를 조회합니다."""
    animals = load_data("animals")
    if animals.empty:
        return pd.DataFrame()
    return animals[animals["shelter_name"] == shelter_name]
