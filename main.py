import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# 페이지 설정
st.set_page_config(page_title="전국 시군구별 고령화 지도", layout="wide")


# 1. 데이터 로드 (캐싱 적용)
@st.cache_data
def load_data():
    # 인구 데이터 불러오기 (코드 열은 10자리 문자열로 지정)
    pop_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
    df_pop = pd.read_csv(pop_url, compression="gzip", dtype={"코드": str})

    # 지도 경계 GeoJSON 데이터 불러오기
    geo_url = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"
    geojson_data = requests.get(geo_url).json()

    return df_pop, geojson_data


# 데이터 불러오기
df_raw, geojson_data = load_data()

# 2. 최신 연도 추출 및 필터링
latest_year = df_raw["연도"].max()
df_latest = df_raw[df_raw["연도"] == latest_year].copy()

# 3. 5자리 시군구 코드 생성
df_latest["sigungu_code"] = df_latest["코드"].str[:5]

# 4. 전체 인구 및 65세 이상 인구 계산
# '계_'로 시작하는 나이별 열 추출
total_pop_cols = [c for c in df_latest.columns if c.startswith("계_")]

# '계_65세'부터 '계_100세 이상'까지의 열 추출 (65세 이상)
elderly_pop_cols = []
for c in total_pop_cols:
    age_str = c.replace("계_", "").replace("세", "")
    if age_str == "100 이상":
        elderly_pop_cols.append(c)
    elif age_str.isdigit() and int(age_str) >= 65:
        elderly_pop_cols.append(c)

# 행정동 단위 인구합 계산
df_latest["전체인구"] = df_latest[total_pop_cols].sum(axis=1)
df_latest["고령인구"] = df_latest[elderly_pop_cols].sum(axis=1)

# 5. 시군구 단위로 합산하여 고령화율 산출
df_sigungu = (
    df_latest.groupby(["sigungu_code", "시도", "시군구"], as_index=False)[
        ["전체인구", "고령인구"]
    ].sum()
)

df_sigungu["고령화율"] = (
    df_sigungu["고령인구"] / df_sigungu["전체인구"] * 100
).round(2)

# 6. 고령화율 5단계 범주화 (경계값: 19%, 23%, 28%, 38%)
bins = [-float("inf"), 19, 23, 28, 38, float("inf")]
labels = ["19% 미만", "19% 이상 ~ 23% 미만", "23% 이상 ~ 28% 미만", "28% 이상 ~ 38% 미만", "38% 이상"]

df_sigungu["고령화율_구간"] = pd.cut(
    df_sigungu["고령화율"], bins=bins, labels=labels, right=False
)

# --- 화면 구성 ---
st.title(f"📊 {latest_year}년 전국 시군구별 고령화 지도")
st.markdown(
    "시군구별 65세 이상 인구 비율(고령화율)을 5단계로 나눈 단계구분도입니다."
)

# 7. Plotly 단계구분도(Choropleth) 지도 생성
color_discrete_map = {
    "19% 미만": "#FEF0D9",
    "19% 이상 ~ 23% 미만": "#FDCC8A",
    "23% 이상 ~ 28% 미만": "#FC8D59",
    "28% 이상 ~ 38% 미만": "#E34A33",
    "38% 이상": "#B30000",
}

fig = px.choropleth_map(
    df_sigungu,
    geojson=geojson_data,
    locations="sigungu_code",
    featureidkey="properties.코드",
    color="고령화율_구간",
    color_discrete_map=color_discrete_map,
    category_orders={"고령화율_구간": labels},
    hover_name="시군구",
    hover_data={"시도": True, "고령화율": ":.2f%", "sigungu_code": False, "고령화율_구간": False},
    map_style="white-bg",  # mapbox_style 대신 map_style로 변경
    center={"lat": 35.9, "lon": 127.8},
    zoom=6.2,
    opacity=0.8,
)

# 지도 스타일 및 레이아웃 수정
fig.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    legend_title_text="고령화율 구간",
    legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02),
)

# Streamlit에 지도 표시
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# 8. 고령화율 상위/하위 10개 시군구 표 표시
col1, col2 = st.columns(2)

df_sorted = df_sigungu.sort_values(by="고령화율", ascending=False)

with col1:
    st.subheader("🔴 고령화율 가장 높은 곳 10곳")
    top10 = df_sorted[["시도", "시군구", "고령화율"]].head(10).reset_index(drop=True)
    st.dataframe(top10, use_container_width=True)

with col2:
    st.subheader("🔵 고령화율 가장 낮은 곳 10곳")
    bottom10 = df_sorted[["시도", "시군구", "고령화율"]].tail(10).iloc[::-1].reset_index(drop=True)
    st.dataframe(bottom10, use_container_width=True)
