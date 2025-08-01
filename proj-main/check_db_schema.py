# ==============================================================================
# check_db_schema.py - 데이터베이스 스키마 확인 스크립트
# ==============================================================================
# 이 스크립트는 데이터베이스에 연결하여 'shelters' 테이블의 구조(스키마)를
# 확인하고, 컬럼 목록을 출력하는 역할을 합니다.
#
# [주요 기능]
# 1. `config.ini` 파일에서 데이터베이스 접속 정보를 읽어옵니다.
# 2. 설정 정보를 사용하여 MySQL 데이터베이스에 연결합니다.
# 3. `DESCRIBE shelters` 쿼리를 실행하여 'shelters' 테이블의 컬럼 정보를 조회합니다.
# 4. 조회된 컬럼들의 이름을 콘솔에 출력합니다.
#
# [사용 목적]
# - 데이터베이스 테이블이 올바르게 생성되었는지 확인할 때
# - 테이블의 컬럼 구성을 빠르게 파악하고 싶을 때
# - 데이터베이스 연결 설정을 테스트할 때
# ==============================================================================

import mysql.connector
import configparser
import os
import pandas as pd

# --- 경로 설정 ---
# 이 스크립트 파일의 현재 위치를 기준으로 프로젝트 루트 경로를 계산합니다.
# 이를 통해 어디서 스크립트를 실행하든 `config.ini` 파일의 위치를 정확히 찾을 수 있습니다.
current_script_path = os.path.abspath(__file__)
project_root = os.path.dirname(current_script_path)
CONFIG_PATH = os.path.join(project_root, 'config.ini')

def get_db_config():
    """
    `config.ini` 파일에서 데이터베이스 설정 정보를 읽어와 반환합니다.
    파일이 존재하지 않을 경우, FileNotFoundError 예외를 발생시킵니다.
    """
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    config.read(CONFIG_PATH)
    return config['DB']

conn = None
try:
    # 1. 설정 파일에서 DB 정보 가져오기
    db_config = get_db_config()
    db_config_dict = {k: v for k, v in db_config.items()} # mysql.connector가 요구하는 딕셔너리 형태로 변환
    
    # 2. 데이터베이스 연결
    conn = mysql.connector.connect(**db_config_dict)
    cursor = conn.cursor()
    
    # 3. 'shelters' 테이블 스키마 확인 및 출력
    print("--- Columns in `shelters` table ---")
    cursor.execute('DESCRIBE shelters')
    columns = [col[0] for col in cursor.fetchall()] # 쿼리 결과에서 컬럼 이름만 추출
    print(columns)

except mysql.connector.Error as e:
    # 데이터베이스 연결 또는 쿼리 실행 중 오류 발생 시 처리
    print(f'Database error: {e}')
except FileNotFoundError as e:
    # 설정 파일을 찾을 수 없을 때 오류 처리
    print(e)
finally:
    # 4. 모든 작업 완료 후 데이터베이스 연결 종료
    # 오류 발생 여부와 상관없이 항상 실행되어 리소스를 안전하게 해제합니다.
    if conn and conn.is_connected():
        conn.close()
