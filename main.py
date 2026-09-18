import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="전국 고령화 지도", layout="wide")
st.title("🗺️ 전국 고령화 지도")
st.caption("시군구별 65세 이상 인구 비율 (행정안전부 주민등록 인구)")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"

@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():
    # '코드' 열은 앞자리 0이 사라지지 않게 글자로 읽습니다
    return pd.read_csv(POP_URL, dtype={"코드": str})

@st.cache_data(show_spinner="지도 경계를 불러오는 중입니다...")
def load_geojson():
    return requests.get(GEO_URL, timeout=30).json()

df = load_population()
geojson = load_geojson()

# 1. 가장 최신 연도만 사용
latest_year = int(df["연도"].max())
df = df[df["연도"] == latest_year].copy()

# 2. '계_'로 시작하는 나이 열만 (남_·여_ 열까지 더하면 두 배가 됩니다)
total_cols = [c for c in df.columns if c.startswith("계_")]

def age_of(col):
    m = re.match(r"계_(\d+)세", col)
    return int(m.group(1)) if m else None

# 3. 그중 65세 이상 열만 ('계_65세' ~ '계_100세 이상')
elderly_cols = [c for c in total_cols if age_of(c) is not None and age_of(c) >= 65]

# 4. 동 단위로 전체 인구·고령 인구 계산
df["전체인구"] = df[total_cols].sum(axis=1)
df["고령인구"] = df[elderly_cols].sum(axis=1)

# 5. '코드' 앞 5자리 = 시군구 코드 → 시군구별로 묶어 비율 계산
df["시군구코드"] = df["코드"].str[:5]
grouped = df.groupby("시군구코드")[["전체인구", "고령인구"]].sum().reset_index()
grouped["고령화율"] = (grouped["고령인구"] / grouped["전체인구"] * 100).round(2)

# 경계 파일에서 코드 → 시군구·시도 이름 짝 만들기
names = pd.DataFrame([
    {
        "시군구코드": str(f["properties"]["코드"]),
        "시군구": f["properties"]["시군구"],
        "시도": f["properties"]["시도"],
    }
    for f in geojson["features"]
])
merged = grouped.merge(names, on="시군구코드", how="left")

# 6. 5단계 색 구간 (전국 시군구를 다섯 덩어리로 나눈 실제 경계값)
BINS = [0, 19, 23, 28, 38, 100]
LABELS = ["19% 미만", "19~23%", "23~28%", "28~38%", "38% 이상"]
COLORS = {
    "19% 미만": "#fee6ce",
    "19~23%": "#fdc086",
    "23~28%": "#f79646",
    "28~38%": "#e8590c",
    "38% 이상": "#a63603",
}
merged["단계"] = pd.cut(merged["고령화율"], bins=BINS, labels=LABELS, right=False)

# 7. 단계구분도 그리기 (배경 지도 타일 없이 경계만)
fig = px.choropleth(
    merged,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="단계",
    category_orders={"단계": LABELS},
    color_discrete_map=COLORS,
    hover_name="시군구",
    hover_data={"고령화율": True, "시도": True, "시군구코드": False, "단계": False},
    labels={"고령화율": "65세 이상 비율(%)"},
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    height=700,
    legend_title_text=f"65세 이상 비율 ({latest_year}년)",
)

st.plotly_chart(fig, width="stretch")

# 8. 지도 아래 순위 표 두 개
c1, c2 = st.columns(2)
cols = ["시도", "시군구", "고령화율"]
with c1:
    st.subheader("🔴 고령화율 높은 곳 10")
    st.dataframe(merged.nlargest(10, "고령화율")[cols].reset_index(drop=True))
with c2:
    st.subheader("🟢 고령화율 낮은 곳 10")
    st.dataframe(merged.nsmallest(10, "고령화율")[cols].reset_index(drop=True))
# 📊 고령화율에 따른 공공보건·복지 시설 접근성 비교 탐구

> **탐구 주제:** 지역별 65세 이상 고령인구 비율과 노인 복지 인프라(경로당, 노인복지관, 보건소 등)의 공간적 배치 불균형 분석

---

## 📌 1. 탐구 동기 및 목적

- **동기:** 초고령화 사회 진입에 따라 지역별 복지 인프라 격차 문제가 심화되고 있습니다. 내가 살고 있는 지자체 내에서 실제로 고령인구 비율이 높은 지역에 복지 인프라가 충분히 배치되어 있는지 검증하고자 본 탐구를 시작하였습니다.
- **목적:** 
  - 읍·면·동별 고령인구 데이터와 복지시설 위치 데이터를 결합하여 분석합니다.
  - 단순 시설 수가 아닌 **'노인 인구 1,000명당 복지시설 수'** 지표를 산출합니다.
  - 인구 대비 복지 인프라가 부족한 **복지 사각지대**를 발굴하고 실효성 있는 개선안을 제안합니다.

---

## 📖 2. 이론적 배경 및 관련 개념

### 주요 개념 정리
1. **고령화율 (Aging Rate):** 전체 인구 중 65세 이상 인구가 차지하는 비율
   - 고령화사회: 7% 이상
   - 고령사회: 14% 이상
   - 초고령사회: 20% 이상
2. **노인 복지 인프라:** 노인복지관, 경로당, 보건소 및 보건지소 등 공공보건 및 여가 복지 시설.
3. **인구 표준화 지표의 필요성:** 단순 시설 개수 비교는 동별 전체 인구 규모 차이를 반영하지 못하므로, 인구 대비 상대적 지표 활용이 필수적입니다.

---

## 🛠️ 3. 데이터 수집 및 분석 방법

### 데이터 출처
- **인구 데이터:** 통계청 KOSIS (행정구역별/연령별 주민등록인구)
- **시설 데이터:** 공공데이터포털(data.go.kr) 또는 지자체 개방 데이터 (노인복지시설 및 보건기관 현황)

### 데이터 가공 및 분석 절차
1. **인구 데이터 정리:** 엑셀(Excel)을 활용해 읍·면·동별 전체 인구 및 65세 이상 인구 수 정리
2. **고령화율 계산:** 
   $$\text{고령화율(\%)} = \left( \frac{\text{65세 이상 인구}}{\text{전체 인구}} \right) \times 100$$
3. **인프라 지수 산출 (노인 1,000명당 복지시설 수):**
   $$\text{노인 1,000명당 시설 수} = \left( \frac{\text{지역 내 복지시설 총수}}{\text{65세 이상 인구 수}} \right) \times 1,000$$

---

## 📈 4. 데이터 분석 결과 및 시각화

- **동별 고령화율 현황:** 고령인구 비율 상위 3개 동 vs 하위 3개 동 비교 분석
- **인프라 지수 비교:** 고령화율은 높으나 인구 대비 시설 수가 평균 이하인 지역(복지 사각지대) 도출
- **공간적 격차:** 원도심과 신도심 간의 인구 구조 차이 및 시설 배치 불균형 패턴 확인

---

## 💡 5. 결론 및 정책 제안

### 분석 결과 요약
- 분석 결과, 고령인구 밀집 지역과 실제 복지시설 공급량 간에 지역적 불균형이 존재하는 것으로 나타났습니다.

### 정책 제안
1. **공간 재활용:** 복지 인프라 사각지대 지역 내 기존 공공건물(동주민센터 등) 공간을 활용한 팝업 복지 공간 설치
2. **이동성 개선:** 거동이 불편한 고령층을 위한 순환형 복지 셔틀버스 운행 및 찾아가는 보건 복지 서비스 확대

---

## 🔍 6. 느낀 점 및 한계점

- **느낀 점:** 공공데이터를 직접 가공하고 비율 지표를 생성해 보면서, 단순 수치 너머의 사회적 불평등 문제를 구체적으로 시각화하는 방법을 배웠습니다.
- **한계점:** 본 탐구는 시설의 '개수'만을 다루었으며, 시설의 실제 규모(면적)나 운영 프로그램의 질적 수준까지는 반영하지 못했다는 한계가 있습니다.
