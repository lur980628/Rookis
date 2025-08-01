# ==============================================================================
# update_data.py - 데이터 수집 및 데이터베이스 업데이트 스크립트
# ==============================================================================
# 이 스크립트는 독립적으로 실행되어 외부 API(공공데이터포털, 카카오)
# 및 로컬 JSON 파일로부터 최신 데이터를 가져와 가공한 후,
# MySQL 데이터베이스에 저장하는 ETL(Extract, Transform, Load) 파이프라인 역할을 합니다.
#
# [주요 실행 흐름]
# 1. **설정 로드:** `config.ini`에서 API 키와 DB 접속 정보를 가져옵니다.
# 2. **데이터 추출 (Extract):**
#    - `load_local_json_data`: 로컬 `data` 폴더의 JSON 파일에서 유기동물 데이터를 가져옵니다.
#    - `fetch_abandoned_animals`: 공공데이터포털에서 유기동물 정보를 조회합니다.
#    - `fetch_shelters`: 전국의 모든 동물보호소 정보를 조회합니다.
#    - `get_coordinates_from_address`: 카카오 지도 API를 사용하여 주소를
#      위도/경도 좌표로 변환(지오코딩)합니다.
# 3. **데이터 변환 (Transform):**
#    - `preprocess_data`: API와 JSON으로부터 받은 모든 원본 데이터를 분석하기 좋은 형태로
#      가공하고 결합합니다.
# 4. **데이터 적재 (Load):**
#    - `update_database`: 가공된 데이터를 Pandas DataFrame 형태로 만든 후,
#      SQLAlchemy를 통해 `shelters`와 `animals` 테이블에 저장합니다.
#
# [실행 방법]
# - 터미널에서 `python update_data.py` 명령으로 직접 실행합니다.
# - 주기적으로 자동 실행되도록 스케줄링(예: Cron, Windows Scheduler)하여
#   데이터를 최신 상태로 유지할 수 있습니다.
# ==============================================================================

import json
from data_manager import DataManager
import pandas as pd
import xml.etree.ElementTree as ET
import mysql.connector
from sqlalchemy import create_engine
import configparser
import os
from datetime import datetime, timedelta
import subprocess
import tempfile
from urllib.parse import quote
import requests
import json

# --- 경로 설정 ---
current_script_path = os.path.abspath(__file__)
streamlit_web_dir = os.path.dirname(current_script_path)
project_root = os.path.dirname(streamlit_web_dir)
CONFIG_PATH = os.path.join(project_root, 'config.ini')

# --- 설정 정보 로드 함수 ---
def get_db_config():
    """`config.ini`에서 [DB] 섹션의 설정을 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['DB']

def get_api_key():
    """`config.ini`에서 공공데이터포털 API 키를 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['API']['service_key']

def get_kakao_rest_api_key():
    """`config.ini`에서 카카오 지도 API 키를 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['API']['kakao_rest_api_key']

def fetch_abandoned_animals(api_key, bgnde, endde, upkind=''):
    """공공데이터포털에서 특정 기간과 축종의 유기동물 정보를 가져옵니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/abandonmentPublic_v2"

    all_items = []
    page_no = 1
    num_of_rows = 1000 # API가 허용하는 최대 요청 개수

    while True:
        # API 요청 URL 구성
        url = f"{endpoint}?serviceKey={api_key_encoded}&bgnde={bgnde}&endde={endde}&pageNo={page_no}&numOfRows={num_of_rows}&_type=xml"
        if upkind:
            url += f"&upkind={upkind}"

        print(f"[DEBUG] API 요청 URL: {url}")

        # PowerShell을 사용하여 데이터를 임시 파일로 다운로드
        fp, temp_path = tempfile.mkstemp(suffix=".xml")
        os.close(fp)

        try:
            command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
            subprocess.run(command, check=True, shell=True, capture_output=True, text=True)

            with open(temp_path, 'rb') as f:
                xml_data = f.read()

            if not xml_data:
                print(f"경고: 페이지 {page_no}에서 빈 응답을 받았습니다.")
                break

            root = ET.fromstring(xml_data.decode('utf-8'))

            # API 응답 코드 확인
            result_code = root.findtext('.//resultCode', 'N/A')
            if result_code != '00':
                print(f"API 오류 발생 (코드: {result_code}, 메시지: {root.findtext('.//resultMsg', 'N/A')})")
                break

            items_in_page = root.findall('.//item')
            if not items_in_page:
                print(f"정보: 페이지 {page_no}에 더 이상 데이터가 없습니다.")
                break

            # 수집된 데이터를 리스트에 추가
            for item in items_in_page:
                item_dict = {child.tag: child.text for child in item}
                all_items.append(item_dict)

            total_count = int(root.findtext('.//totalCount', '0'))
            print(f"페이지 {page_no}에서 {len(items_in_page)}건 데이터 수집. (현재까지 총 {len(all_items)} / 전체 {total_count}건)")

            # 모든 데이터를 수집했으면 반복 종료
            if len(all_items) >= total_count:
                break

            page_no += 1

        except subprocess.CalledProcessError as e:
            print(f"PowerShell을 통한 데이터 다운로드 중 오류 발생: {e.stderr}")
            return None # 오류 발생 시 None 반환
        except ET.ParseError as e:
            print(f"XML 파싱 오류: {e}")
            return None
        except Exception as e:
            print(f"알 수 없는 오류 발생: {e}")
            return None
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return all_items

def _fetch_sido_list(api_key):
    """보호소 목록 조회를 위해 내부적으로 사용되는 시/도 목록 조회 함수입니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sido_v2"
    url = f"{endpoint}?serviceKey={api_key_encoded}&numOfRows=100&_type=xml"
    
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        
        if not xml_data:
            return []
            
        root = ET.fromstring(xml_data.decode('utf-8'))
        sido_list = []
        for item in root.findall('.//item'):
            sido_list.append({"code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
        return sido_list
    except Exception as e:
        print(f"시/도 목록 조회 중 오류 발생: {e}")
        return []
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def _fetch_sigungu_list(api_key, sido_code):
    """특정 시/도에 속한 시/군/구 목록을 조회하는 내부 함수입니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/sigungu_v2"
    url = f"{endpoint}?serviceKey={api_key_encoded}&upr_cd={sido_code}&_type=xml"
    
    fp, temp_path = tempfile.mkstemp(suffix=".xml")
    os.close(fp)
    
    try:
        command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
        subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        
        with open(temp_path, 'rb') as f:
            xml_data = f.read()
        
        if not xml_data:
            return []
            
        root = ET.fromstring(xml_data.decode('utf-8'))
        sigungu_list = []
        for item in root.findall('.//item'):
            sigungu_list.append({"upr_code": item.findtext("uprCd"), "code": item.findtext("orgCd"), "name": item.findtext("orgdownNm")})
        return sigungu_list
    except Exception as e:
        print(f"시/군/구 목록 조회 중 오류 발생: {e}")
        return []
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def fetch_shelters(api_key):
    """전국의 모든 동물보호소 정보를 시/도 및 시/군/구별로 순회하며 가져옵니다."""
    api_key_encoded = quote(api_key)
    endpoint = "https://apis.data.go.kr/1543061/abandonmentPublicService_v2/shelter_v2"
    all_shelters = []
    sido_list = _fetch_sido_list(api_key)

    if not sido_list:
        print("경고: 시도 목록을 가져오지 못하여 보호소 데이터를 수집할 수 없습니다.")
        return []

    for sido_info in sido_list:
        sido_code = sido_info['code']
        sido_name = sido_info['name']
        print(f"--- {sido_name} ({sido_code}) 보호소 데이터 수집 시작 ---")

        page_no = 1
        collected_in_sido = 0
        total_in_sido = -1 # -1로 초기화하여 아직 totalCount를 받지 않았음을 표시

        while True:
            url = f"{endpoint}?serviceKey={api_key_encoded}&upr_cd={sido_code}&pageNo={page_no}&numOfRows=1000&_type=xml"
            print(f"[DEBUG] 보호소 API 요청 URL: {url}") # 디버깅을 위한 URL 출력

            fp, temp_path = tempfile.mkstemp(suffix=".xml")
            os.close(fp)

            try:
                command = f"powershell -Command \"(New-Object System.Net.WebClient).DownloadFile('{url}', '{temp_path}')\""
                subprocess.run(command, check=True, shell=True, capture_output=True, text=True)

                with open(temp_path, 'rb') as f:
                    xml_data = f.read()

                if not xml_data:
                    print(f"경고: {sido_name} 페이지 {page_no}에서 빈 응답을 받았습니다.")
                    break

                root = ET.fromstring(xml_data.decode('utf-8'))
                result_code = root.findtext('.//resultCode', 'N/A')

                if result_code != '00':
                    print(f"API 오류 (코드: {result_code}, 메시지: {root.findtext('.//resultMsg', 'N/A')})")
                    break

                items_in_page = root.findall('.//item')
                if not items_in_page:
                    print(f"정보: {sido_name} 페이지 {page_no}에 더 이상 데이터가 없습니다.")
                    break

                for item in items_in_page:
                    item_dict = {child.tag: child.text for child in item}
                    all_shelters.append(item_dict)
                
                collected_in_sido += len(items_in_page)

                if total_in_sido == -1: # 첫 요청 시에만 totalCount를 설정
                    total_in_sido = int(root.findtext('.//totalCount', '0'))

                print(f"{sido_name} 페이지 {page_no}에서 {len(items_in_page)}건 수집. (현재 시/도 누적 {collected_in_sido} / 전체 {total_in_sido}건)")

                if collected_in_sido >= total_in_sido:
                    break
                
                page_no += 1

            except Exception as e:
                print(f"{sido_name} 보호소 조회 중 오류 발생: {e}")
                break
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
    
    return all_shelters

def get_coordinates_from_address(address):
    """
    카카오 로컬 API를 사용하여 주어진 주소 문자열을 위도, 경도 좌표로 변환합니다.
    지도 시각화를 위해 필수적인 기능입니다.
    """
    kakao_api_key = get_kakao_rest_api_key()
    if not kakao_api_key:
        print("카카오 REST API 키가 설정되지 않았습니다.")
        return None, None

    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {kakao_api_key}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status() # HTTP 오류 발생 시 예외 처리
        data = response.json()
        
        if data and data['documents']:
            coords = data['documents'][0]
            return float(coords['y']), float(coords['x']) # (위도, 경도) 순서로 반환
        else:
            print(f"주소에 대한 좌표를 찾을 수 없습니다: {address}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"카카오 지오코딩 API 호출 중 오류 발생: {e}")
        return None, None
    except json.JSONDecodeError:
        print(f"카카오 지오코딩 API 응답 파싱 오류: {response.text}")
        return None, None

def preprocess_data(animal_df_raw, shelter_api_df_raw):
    print(f"[DEBUG] preprocess_data 시작. animal_df_raw 타입: {type(animal_df_raw)}, shelter_api_df_raw 타입: {type(shelter_api_df_raw)}")

    # -------------------------------------
    # 1. 동물 데이터 처리 (DataFrame/리스트 모두 대응)
    # -------------------------------------
    if isinstance(animal_df_raw, pd.DataFrame):
        animals_df = animal_df_raw.copy()
    else:
        animals_df = pd.DataFrame(animal_df_raw)

    if animals_df.empty:
        animals_df = pd.DataFrame()
        shelter_df_from_animals = pd.DataFrame()
    else:
        # 컬럼 이름 변경
        rename_map = {
            'desertionNo': 'desertion_no', 'careNm': 'shelter_name', 'age': 'age',
            'popfile': 'image_url', 'kindCd': 'species', 'specialMark': 'story',
            'sexCd': 'sex', 'noticeSdt': 'notice_date', 'processState': 'process_state',
            'careAddr': 'careAddr'
        }
        animals_df.rename(columns={k: v for k, v in rename_map.items() if k in animals_df.columns}, inplace=True)

        # 날짜 변환
        if 'notice_date' in animals_df.columns:
            animals_df['notice_date'] = pd.to_datetime(animals_df['notice_date'], format='%Y%m%d', errors='coerce')

        # 파생 컬럼 생성
        if 'species' in animals_df.columns and 'sex' in animals_df.columns:
            animals_df['animal_name'] = animals_df['species'] + ' (' + animals_df['sex'] + ')'
        else:
            animals_df['animal_name'] = '정보 없음'

        animals_df['personality'] = '정보 없음'

        # 보호소 단위로 집계
        agg_dict = {
            'careAddr_animal': ('careAddr', 'first'),
            'region': ('careAddr', lambda x: x.iloc[0].split()[0] if x.notna().any() else '정보 없음'),
            'count': ('desertion_no', 'count'),
            'long_term': ('notice_date', lambda x: (x < pd.Timestamp.now() - pd.Timedelta(days=30)).sum()),
            'adopted': ('process_state', lambda x: (x == '종료(입양)').sum()),
            'species': ('species', lambda x: x.value_counts().index[0] if not x.empty else '정보 없음')
        }
        if 'image_url' in animals_df.columns:
            agg_dict['image_url'] = ('image_url', 'first')
        
        # `animals_df`에 필요한 컬럼이 모두 있는지 확인
        if all(col in animals_df.columns for col in ['shelter_name', 'desertion_no', 'notice_date', 'process_state']):
            shelter_df_from_animals = animals_df.groupby('shelter_name').agg(**agg_dict).reset_index()

            if 'image_url' not in shelter_df_from_animals.columns:
                shelter_df_from_animals['image_url'] = None
        else:
            shelter_df_from_animals = pd.DataFrame()


    # -------------------------------------
    # 2. 보호소 데이터 처리
    # -------------------------------------
    if isinstance(shelter_api_df_raw, pd.DataFrame):
        shelter_api_df_processed = shelter_api_df_raw.copy()
    else:
        shelter_api_df_processed = pd.DataFrame(shelter_api_df_raw)

    if not shelter_api_df_processed.empty:
        rename_cols = {
            'careNm': 'shelter_name', 'careRegNo': 'care_reg_no', 'careAddr': 'careAddr_api',
            'careTel': 'care_tel', 'dataStdDt': 'data_std_dt', 'lat': 'lat_api', 'lon': 'lon_api'
        }
        shelter_api_df_processed.rename(columns={k: v for k, v in rename_cols.items() if k in shelter_api_df_processed.columns}, inplace=True)

        # 좌표 타입 변환
        shelter_api_df_processed['lat_api'] = pd.to_numeric(shelter_api_df_processed.get('lat_api', pd.NA), errors='coerce')
        shelter_api_df_processed['lon_api'] = pd.to_numeric(shelter_api_df_processed.get('lon_api', pd.NA), errors='coerce')
    else:
        shelter_api_df_processed = pd.DataFrame()

    # -------------------------------------
    # 3. 데이터 병합
    # -------------------------------------
    if shelter_df_from_animals.empty:
        merged_shelter_df = shelter_api_df_processed
    elif shelter_api_df_processed.empty:
        merged_shelter_df = shelter_df_from_animals
    else:
        merged_shelter_df = pd.merge(shelter_df_from_animals, shelter_api_df_processed, on='shelter_name', how='outer')

    # 좌표 채우기 + 주소 결합
    if not merged_shelter_df.empty:
        careAddr_api = merged_shelter_df['careAddr_api'] if 'careAddr_api' in merged_shelter_df.columns else pd.Series(index=merged_shelter_df.index)
        careAddr_animal = merged_shelter_df['careAddr_animal'] if 'careAddr_animal' in merged_shelter_df.columns else pd.Series(index=merged_shelter_df.index)
        merged_shelter_df['careAddr'] = careAddr_api.fillna(careAddr_animal)

        # lat/lon 초기화
        merged_shelter_df['lat'] = merged_shelter_df['lat_api'] if 'lat_api' in merged_shelter_df.columns else pd.NA
        merged_shelter_df['lon'] = merged_shelter_df['lon_api'] if 'lon_api' in merged_shelter_df.columns else pd.NA

        # **중복 제거 + 캐싱**
        cache = {} # 주소별로 좌표 저장
        unique_addresses = merged_shelter_df.loc[
            merged_shelter_df['careAddr'].notna() & 
            (merged_shelter_df['lat'].isna() | merged_shelter_df['lon'].isna()), 
            'careAddr'
        ].unique()

        for addr in unique_addresses:
            if addr not in cache:
                lat, lon = get_coordinates_from_address(addr)
                cache[addr] = (lat, lon)

        # 좌표 채워 넣기
        for index, row in merged_shelter_df.iterrows():
            if pd.isna(row['lat']) or pd.isna(row['lon']):
                addr = row['careAddr']
                if addr in cache:
                    merged_shelter_df.at[index, 'lat'], merged_shelter_df.at[index, 'lon'] = cache[addr]

        # 좌표 못 찾은 주소는 lat/lon = 0으로 기본값 처리 (선택 사항)
        merged_shelter_df['lat'] = merged_shelter_df['lat'].fillna(0)
        merged_shelter_df['lon'] = merged_shelter_df['lon'].fillna(0)

        # 불필요한 컬럼 제거
        merged_shelter_df.drop(columns=['careAddr_api', 'careAddr_animal', 'lat_api', 'lon_api'], inplace=True, errors='ignore')

    # -------------------------------------
    # 4. 최종 컬럼 정리 및 반환
    # -------------------------------------
    # image_url 컬럼이 없으면 추가 (NaN으로 채움)
    if 'image_url' not in animals_df.columns:
        animals_df['image_url'] = None
    
    final_animal_cols = [
        'desertion_no', 'shelter_name', 'animal_name', 'species', 'age',
        'image_url', 'personality', 'story', 'notice_date', 'sex', 'process_state'
    ]
    existing_final_cols = [col for col in final_animal_cols if col in animals_df.columns]

    return merged_shelter_df, animals_df[existing_final_cols]

# --- 로컬 JSON 데이터 로드 함수 추가 ---
def load_local_json_data():
    """
    로컬 'data' 폴더의 JSON 파일들에서 데이터를 읽어와 리스트로 반환합니다.
    """
    all_data = []
    data_dir = os.path.join(project_root, 'data')
    
    try:
        if os.path.exists(data_dir):
            for file_name in ['cat_info.json', 'dog_info.json']:
                file_path = os.path.join(data_dir, file_name)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        print(f"정보: 로컬 파일 '{file_name}'에서 데이터 로드 중...")
                        data = json.load(f)
                        all_data.extend(data)
                else:
                    print(f"경고: 로컬 파일 '{file_name}'을 찾을 수 없습니다.")
        else:
            print("경고: 'data' 폴더를 찾을 수 없습니다. 로컬 데이터는 로드되지 않습니다.")
    except Exception as e:
        print(f"로컬 JSON 데이터 로드 중 오류 발생: {e}")
        all_data = []
        
    return all_data

# --- 데이터 적재 (Load) 함수 ---
def update_database(shelter_df, animal_df):
    """
    가공된 데이터프레임을 데이터베이스의 테이블에 저장합니다.
    `if_exists='replace'` 옵션은 기존 테이블이 있다면 삭제하고 새로 만들기 때문에,
    항상 최신 데이터만 유지됩니다.
    """
    if shelter_df.empty and animal_df.empty:
        print("업데이트할 데이터가 없습니다.")
        return
        
    try:
        db_config = get_db_config()
        engine = create_engine(f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")
        
        with engine.connect() as conn:
            # to_sql 메소드는 DataFrame을 SQL 테이블로 매우 편리하게 변환해줍니다.
            if not shelter_df.empty:
                shelter_df.to_sql('shelters', conn, if_exists='replace', index=False)
                print(f"보호소 데이터 {len(shelter_df)}건이 'shelters' 테이블에 업데이트되었습니다.")
            if not animal_df.empty:
                animal_df.to_sql('animals', conn, if_exists='replace', index=False)
                print(f"유기동물 데이터 {len(animal_df)}건이 'animals' 테이블에 업데이트되었습니다.")
        
    except Exception as e:
        print(f"데이터베이스 오류: {e}")

# --- 메인 실행 블록 ---
if __name__ == "__main__":
    print("데이터 수집 및 DB 업데이트를 시작합니다...")
    try:
        API_KEY = get_api_key()
        if not API_KEY or 'YOUR_API_KEY' in API_KEY:
            print("!!! 경고: config.ini 파일에 실제 API 키를 입력하세요.")
            
        # 1. 로컬 JSON 데이터 로드
        local_animals_data = load_local_json_data()

        # 2. 외부 API 데이터 수집
        all_animals_data_from_api = []
        # API 키가 유효할 경우에만 API 데이터를 가져옵니다.
        if API_KEY and 'YOUR_API_KEY' not in API_KEY:
            # 수집 기간 설정 (실제 데이터가 있는 과거 날짜로 고정)
            bgnde_str = '20240501'
            endde_str = '20240531'
            animal_types = {'개': '417000', '고양이': '422400', '기타': '429900'}

            for animal_name, animal_code in animal_types.items():
                print(f"--- {animal_name} 데이터 수집 시작 (기간: {bgnde_str} ~ {endde_str}) ---")
                items = fetch_abandoned_animals(API_KEY, bgnde_str, endde_str, upkind=animal_code)
                if isinstance(items, list):
                    all_animals_data_from_api.extend(items)
                    print(f"성공: {animal_name} 데이터 {len(items)}건 수집")
                else:
                    print(f"경고: {animal_name} 데이터를 가져오지 못했습니다.")

        # 3. 동물 보호소 API 데이터 수집
        all_shelters_data = []
        if API_KEY and 'YOUR_API_KEY' not in API_KEY:
            print("--- 보호소 데이터 수집 시작 ---")
            all_shelters_data = fetch_shelters(API_KEY)
            if isinstance(all_shelters_data, list):
                print(f"성공: 보호소 데이터 {len(all_shelters_data)}건 수집")
            else:
                print("경고: 보호소 데이터를 가져오지 못했습니다.")
                all_shelters_data = []

        # 4. 로컬 데이터와 API 데이터 결합
        # 로컬 JSON 데이터의 키와 API 데이터의 키가 다르므로, Pandas를 사용하여 전처리 과정에서 통일시킬 것입니다.
        combined_animals_data = local_animals_data + all_animals_data_from_api
        
        # 5. 데이터 전처리 및 DB 업데이트
        if combined_animals_data or all_shelters_data:
            raw_animal_df = pd.DataFrame(combined_animals_data)
            raw_shelter_api_df = pd.DataFrame(all_shelters_data)

            if not raw_animal_df.empty or not raw_shelter_api_df.empty:
                print("데이터 전처리를 시작합니다...")
                shelters, animals = preprocess_data(raw_animal_df, raw_shelter_api_df)

                print("데이터베이스 업데이트를 시작합니다...")
                update_database(shelters, animals)
            else:
                print("로컬 파일 및 API에서 수집된 동물 데이터가 없어 업데이트를 건너뜁니다.")
        else:
            print("수집할 데이터가 없어 업데이트를 건너뜁니다. API 키와 로컬 파일을 확인하세요.")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")