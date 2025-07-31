import streamlit as st
from data_manager import load_data

def show():
    st.subheader(f"❤️ 찜한 동물 ({len(st.session_state.favorites)})마리")

    if not st.session_state.favorites:
        st.info("아직 찜한 동물이 없습니다. 상세 정보 탭에서 하트 버튼을 눌러 추가해보세요!")
        return

    # 전체 동물 데이터 로드
    all_animals = load_data("animals")
    # 찜한 동물만 필터링
    favorite_animals = all_animals[all_animals["animal_name"].isin(st.session_state.favorites)]

    if not favorite_animals.empty:
        for _, animal in favorite_animals.iterrows():
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(animal["image_url"], width=150, caption=animal['animal_name'])
            with cols[1]:
                st.markdown(f"**{animal['animal_name']}** ({animal['species']}, {animal['age']})")
                st.markdown(f"**🏠 보호소:** {animal['shelter_name']}")

                # 성격 및 스토리 표시
                st.markdown(f"**💖 성격:** {animal.get('personality', '정보 없음')}")
                st.markdown(f"**🐾 발견 이야기:** {animal.get('story', '정보 없음')}")

                # 찜 취소 버튼
                if st.button(f"❤️ 찜 취소", key=f"fav_remove_{animal['animal_name']}"):
                    st.session_state.favorites.remove(animal['animal_name'])
                    st.rerun()
            st.markdown("---")
    else:
        st.warning("찜한 동물을 찾을 수 없습니다. 데이터가 변경되었을 수 있습니다.")
