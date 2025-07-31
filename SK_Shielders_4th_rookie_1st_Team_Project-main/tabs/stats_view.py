import streamlit as st
import plotly.express as px

def show(filtered_data):
    st.subheader("📊 통계 차트")

    if filtered_data.empty:
        st.warning("표시할 데이터가 없습니다.")
        return

    # --- 품종별 보호 동물 수 ---
    st.markdown("#### 품종별 보호 동물 수")
    species_chart_data = filtered_data.groupby("species")["count"].sum().reset_index()
    fig_bar = px.bar(
        species_chart_data,
        x="species",
        y="count",
        color="species",
        text="count",
        template="plotly_white"
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_bar, use_container_width=True)

    # --- 지역별 장기 보호 동물 비율 ---
    st.markdown("#### 지역별 장기 보호 동물 비율")
    # '전체'가 아닐 때만 의미가 있음
    if len(filtered_data['region'].unique()) > 1:
        long_term_chart_data = filtered_data.groupby("region")["long_term"].sum().reset_index()
        fig_pie = px.pie(
            long_term_chart_data,
            values="long_term",
            names="region",
            template="plotly_white"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("단일 지역에 대한 비율 차트는 의미가 없습니다.")

