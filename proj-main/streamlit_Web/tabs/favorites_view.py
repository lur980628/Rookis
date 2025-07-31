# ==============================================================================
# favorites_view.py - 찜한 동물 목록 탭
# ==============================================================================
# 이 파일은 사용자가 '찜하기' 버튼을 눌러 선택한 동물들의 목록을 보여주는
# 화면을 구성합니다.
#
# [주요 기능]
# 1. **찜 목록 확인:** `st.session_state.favorites`에 저장된 동물들의 고유 ID
#    (`desertion_no`) 리스트를 가져옵니다.
# 2. **전체 동물 데이터 로드:** `data_manager.load_data("animals")`를 통해
#    DB에 저장된 모든 동물 데이터를 불러옵니다.
# 3. **찜한 동물 필터링:** 전체 동물 데이터 중에서, `session_state`에 저장된
#    ID 목록과 일치하는 동물들만 필터링하여 `favorite_animals` 데이터프레임을
#    생성합니다.
# 4. **목록 표시 및 찜 취소:** 필터링된 동물 목록을 순회하며 각 동물의 정보
#    (사진, 이름, 보호소 등)를 표시하고, 옆에 '찜 취소' 버튼을 제공합니다.
#    - 사용자가 '찜 취소' 버튼을 누르면 해당 동물의 ID를 `session_state`에서
#      제거하고, `st.rerun()`으로 화면을 즉시 새로고침합니다.
# ==============================================================================

import streamlit as st
from data_manager import load_data

def show():
    """
    '찜한 동물' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다.
    """
    # 탭의 제목을 찜한 동물의 수와 함께 동적으로 표시합니다.
    st.subheader(f"❤️ 찜한 동물 ({len(st.session_state.favorites)})마리")

    # 찜한 동물이 없는 경우 안내 메시지를 표시하고 함수를 종료합니다.
    if not st.session_state.favorites:
        st.info("아직 찜한 동물이 없습니다. 상세 정보 탭에서 하트 버튼을 눌러 추가해보세요!")
        return

    # 1. 전체 동물 데이터를 DB에서 로드합니다.
    all_animals = load_data("animals")
    
    # 2. 찜 목록(st.session_state.favorites)에 있는 desertion_no를 기준으로
    #    전체 동물 데이터에서 해당하는 행들만 필터링합니다.
    favorite_animals = all_animals[all_animals["desertion_no"].isin(st.session_state.favorites)]

    if not favorite_animals.empty:
        # 3. 필터링된 찜한 동물 목록을 순회하며 화면에 표시합니다.
        for _, animal in favorite_animals.iterrows():
            cols = st.columns([1, 3]) # 이미지와 텍스트 영역을 나눕니다.
            with cols[0]:
                st.image(animal["image_url"], width=150, caption=animal['animal_name'])
            with cols[1]:
                st.markdown(f"**{animal['animal_name']}** ({animal['species']}, {animal['age']})")
                st.markdown(f"**🏠 보호소:** {animal['shelter_name']}")
                st.markdown(f"**💖 성격:** {animal.get('personality', '정보 없음')}")
                st.markdown(f"**🐾 발견 이야기:** {animal.get('story', '정보 없음')}")

                # --- 찜 취소 버튼 로직 ---
                # 각 버튼의 고유성을 보장하기 위해 key에 동물의 desertion_no를 포함시킵니다.
                if st.button(f"❤️ 찜 취소", key=f"fav_remove_{animal['desertion_no']}"):
                    st.session_state.favorites.remove(animal['desertion_no'])
                    # 화면을 새로고침하여 목록에서 즉시 제거된 것처럼 보이게 합니다.
                    st.rerun()
            st.markdown("---") # 동물 정보 사이에 구분선을 추가합니다.
    else:
        # 세션에는 찜 ID가 있지만, DB에서 해당 동물을 찾지 못한 경우 (예: 데이터 업데이트로 삭제됨)
        st.warning("찜한 동물을 찾을 수 없습니다. 데이터가 변경되었을 수 있습니다.")