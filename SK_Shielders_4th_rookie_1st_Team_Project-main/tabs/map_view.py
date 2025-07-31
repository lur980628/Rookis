import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap

def show(data):
    st.header("📍 보호소 위치 지도")

    # 데이터가 비어있으면 경고 메시지 표시 후 종료
    if data.empty:
        st.warning("선택하신 조건에 해당하는 보호소가 없습니다. 필터를 조정해보세요.")
        return

    # 맵의 중심 좌표 계산 (데이터가 없거나 위도/경도 값이 없으면 기본값 사용)
    map_center_lat = data['lat'].mean() if not data['lat'].isnull().all() else 36.5
    map_center_lon = data['lon'].mean() if not data['lon'].isnull().all() else 127.8

    # Folium 맵 초기화
    m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=7)

    # 마커 클러스터링 플러그인 추가
    marker_cluster = MarkerCluster().add_to(m)

    # --- 개별 마커 아이콘 설정 (Font Awesome 사용) ---
    # 배경 없이 파란색 마커만 표시하기 위해 Folium의 기본 Icon 클래스를 사용합니다.
    # 이 클래스는 Font Awesome 아이콘을 사용하며, 배경이 투명하고 색상을 쉽게 변경할 수 있습니다.
    # 'map-marker' 아이콘을 파란색으로 설정합니다.
    blue_map_marker_icon = folium.Icon(color='blue', icon='map-marker', prefix='fa') # 'fa'는 Font Awesome 아이콘을 의미

    # 각 보호소 데이터를 순회하며 마커 추가
    for idx, row in data.iterrows():
        # 데이터 추출 (변수명 간결화)
        shelter_name = row["shelter_name"]
        region = row["region"]
        count = row["count"]
        long_term = row["long_term"]
        adopted = row["adopted"]
        # 팝업에 표시될 이미지 URL. 이 또한 유효한 URL이어야 합니다.
        popup_image_url = row["image_url"]

        # 팝업에 들어갈 HTML 내용 구성
        # 불투명한 연핑크 배경색 및 가독성 확보를 위한 스타일 적용
        popup_html = f"""
        <div style="background-color: rgba(255, 204, 229, 0.8); padding: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); color: #333; font-family: Arial, sans-serif;">
            <h4 style="margin-top:0; margin-bottom:5px; color:#666;"><b>{shelter_name}</b></h4>
            <p style="margin-bottom:2px;">지역: {region}</p>
            <p style="margin-bottom:2px;">보호 동물 수: {count}마리</p>
            <p style="margin-bottom:2px;">장기 보호 동물: {long_term}마리</p>
            <p style="margin-bottom:10px;">입양 완료: {adopted}마리</p>
            <img src="{popup_image_url}" alt="보호소 대표 이미지" style="width:100%; max-width:150px; height:auto; margin-top:5px; display: block; margin-left: auto; margin-right: auto; border-radius: 3px;"><br>
            <button onclick="parent.postMessage({{
                streamlit: {{
                    command: 'setSessionState',
                    args: {{ active_tab: '📋 보호소 상세 현황', selected_shelter_name: '{shelter_name}' }}
                }}
            }}, '*');" style="margin-top:10px; padding: 8px 15px; cursor: pointer; background-color: #FF99CC; color: white; border: none; border-radius: 5px; font-weight: bold; width: 100%;">상세 정보 보기</button>
        </div>
        """
        # 팝업 높이를 늘려 스크롤바가 생기지 않도록 조정
        iframe = folium.IFrame(popup_html, width=280, height=360)
        popup = folium.Popup(iframe, max_width=300)

        # 마커 생성 및 클러스터에 추가
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=popup,
            tooltip=shelter_name,
            icon=blue_map_marker_icon # Font Awesome 아이콘 적용
        ).add_to(marker_cluster)

    # --- 지도 옵션: 히트맵 레이어 추가 ---
    st.sidebar.subheader("지도 옵션")
    show_heatmap = st.sidebar.checkbox("보호소 밀집도 히트맵 표시", False, help="보호소가 많은 지역을 색상으로 표시합니다.")

    if show_heatmap:
        # 히트맵 데이터 (위도, 경도, 가중치 - 여기서는 동물 수)
        heat_data = data[['lat', 'lon', 'count']].dropna().values.tolist()
        if heat_data:
            HeatMap(heat_data).add_to(m)
        else:
            st.sidebar.warning("히트맵을 위한 데이터(위도, 경도, 동물 수)가 불완전하거나 없습니다.")

    # --- Streamlit에 Folium 지도 렌더링 ---
    # 지도가 Streamlit 앱의 너비에 맞게 자동으로 조절되도록 '100%' 설정
    st_data = st_folium(m, width='100%', height=500)