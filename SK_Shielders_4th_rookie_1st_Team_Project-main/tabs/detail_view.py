import streamlit as st
from data_manager import get_animal_details, load_data # load_data 임포트 추가

def show(filtered_data, selected_shelter_from_map=None): # 인자 추가
    st.subheader("📋 보호소 상세 현황")

    # 보호소 목록에서 선택
    shelter_names = filtered_data['shelter_name'].unique().tolist()

    if not shelter_names: # 보호소 목록이 비어있는 경우
        st.info("선택된 필터에 해당하는 보호소가 없습니다.")
        return

    # selected_shelter_from_map이 있다면 해당 보호소를 기본값으로 선택
    if selected_shelter_from_map and selected_shelter_from_map in shelter_names:
        default_index = shelter_names.index(selected_shelter_from_map)
    else:
        # 기존 selected_shelter 세션 상태를 활용하거나, 첫 번째 항목을 기본으로
        if "selected_shelter" in st.session_state and st.session_state.selected_shelter in shelter_names:
            default_index = shelter_names.index(st.session_state.selected_shelter)
        else:
            default_index = 0

    selected_shelter = st.selectbox(
        "상세 정보를 볼 보호소를 선택하세요:",
        options=shelter_names,
        index=default_index, # 기본 선택 값 설정
        key="detail_shelter_select"
    )

    # st.session_state.selected_shelter 값 업데이트 (selectbox 선택값으로)
    st.session_state.selected_shelter = selected_shelter

    if selected_shelter:
        st.markdown(f"### 🏠 {selected_shelter}")

        # 선택된 보호소의 동물 정보 가져오기
        animal_details = get_animal_details(selected_shelter)

        if not animal_details.empty:
            for _, animal in animal_details.iterrows():
                cols = st.columns([1, 3])
                with cols[0]:
                    st.image(animal["image_url"], width=150, caption=animal['animal_name'])
                with cols[1]:
                    # 찜하기 버튼 로직
                    # 찜 목록은 animal['animal_name'] 문자열로 저장되어 있으므로, 그에 맞춰 확인
                    is_favorited = animal['animal_name'] in st.session_state.favorites
                    button_text = "❤️ 찜 취소" if is_favorited else "🤍 찜하기"
                    if st.button(button_text, key=f"fav_add_{animal['animal_name']}"):
                        if is_favorited:
                            st.session_state.favorites.remove(animal['animal_name'])
                        else:
                            st.session_state.favorites.append(animal['animal_name'])
                        st.rerun()

                    st.markdown(f"**{animal['animal_name']}** ({animal['species']}, {animal['age']})")
                    
                    # 성격 및 스토리 표시
                    st.markdown(f"**💖 성격:** {animal.get('personality', '정보 없음')}")
                    st.markdown(f"**🐾 발견 이야기:** {animal.get('story', '정보 없음')}")
                st.markdown("---")
        else:
            st.warning("이 보호소에 등록된 동물 정보가 없습니다.")

    else:
        st.info("지도에서 보호소 마커를 클릭하여 상세 정보를 확인하세요.")

    # --- 데이터 다운로드 ---
    st.markdown("---")
    st.download_button(
        label="📥 현재 필터링된 보호소 목록 다운로드 (CSV)",
        data=filtered_data.to_csv(index=False).encode('utf-8-sig'),
        file_name="filtered_shelter_data.csv",
        mime="text/csv"
    )