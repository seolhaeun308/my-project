import json
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="시군구별 고령화율 단계구분도", layout="wide")

st.title("📊 대한민국 시군구별 65세 이상 인구 비율")
st.markdown("시군구별 고령화율(%)을 색상으로 나타낸 단계구분도(Choropleth) 지도입니다.")

# 1. 샘플 데이터 생성 (실제 프로젝트 시 KOSIS 데이터 등으로 교체)
@st.cache_data
def load_data():
    # 행정구역코드(SIG_CD) 및 고령화율 데이터 예시
    data = {
        "SIG_CD": ["11110", "11140", "11170", "26110", "27110"],
        "SIG_KOR_NM": ["종로구", "중구", "용산구", "중구(부산)", "중구(대구)"],
        "elderly_ratio": [18.2, 19.5, 17.1, 26.8, 22.4]
    }
    return pd.DataFrame(data)

df = load_data()

# 2. GeoJSON 데이터 로드 (대한민국 시군구 경계 데이터)
@st.cache_data
def load_geojson():
    # 인터넷에서 대한민국 시군구 GeoJSON을 바로 불러옵니다.
    url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_municipalities_2013_geo.json"
    return url

geojson_url = load_geojson()

# Sidebar: 데이터 확인 및 필터링
st.sidebar.header("데이터 확인")
st.sidebar.dataframe(df)

# 3. 지도 생성 (대한민국 중심 좌표)
m = folium.Map(location=[36.5, 127.5], zoom_start=7, tiles="cartodbpositron")

# 4. 단계구분도(Choropleth) 레이어 추가
folium.Choropleth(
    geo_data=geojson_url,
    data=df,
    columns=["SIG_CD", "elderly_ratio"],
    key_on="feature.properties.code",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name="65세 이상 인구 비율 (%)",
    nan_fill_color="white"
).add_to(m)

# 5. Streamlit에 지도 출력
st_folium(m, width="100%", height=600)
