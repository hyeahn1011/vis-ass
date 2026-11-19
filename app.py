from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="카페 음료 판매 탐색", page_icon="☕", layout="wide")

# ---------- 데이터 ----------
@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_csv(Path(__file__).parent / "cafe_sales.csv")


df = load_data()

MENU_ORDER = ["아이스 아메리카노", "따뜻한 아메리카노", "아이스티", "핫초코"]
MENU_EN = {  # matplotlib은 한글 폰트가 없으면 깨지므로 영문 라벨 사용
    "아이스 아메리카노": "Iced Americano",
    "따뜻한 아메리카노": "Hot Americano",
    "아이스티": "Iced Tea",
    "핫초코": "Hot Chocolate",
}
COLORS = {
    "아이스 아메리카노": "#2E86C1",
    "따뜻한 아메리카노": "#C0392B",
    "아이스티": "#48C9B0",
    "핫초코": "#E67E22",
}
METRICS = {"판매량": ("cups", "잔"), "매출": ("revenue", "천원")}

# ---------- 사이드바 ----------
with st.sidebar:
    st.header("조회 조건")
    menus = st.multiselect("메뉴", MENU_ORDER, default=MENU_ORDER)
    m_start, m_end = st.slider("월 범위", 1, 12, (1, 12))
    metric_label = st.selectbox("표시 지표", list(METRICS.keys()))

col, unit = METRICS[metric_label]

# ---------- 헤더 ----------
st.title("날이 더우면 아이스 음료가 더 팔릴까")
st.caption(
    "출처: 수업용 가상 데이터(cafe_sales.csv) · 2026년 1~12월 교내 카페 메뉴별 월 판매 · "
    "매출 단위: 천원 · 기온: 월 평균기온(℃)"
)

if not menus:
    st.warning("왼쪽에서 메뉴를 하나 이상 선택하세요.")
    st.stop()

f = df[df["menu"].isin(menus) & df["month"].between(m_start, m_end)]

# ---------- 지표 ----------
st.subheader(f"{m_start}~{m_end}월 {metric_label} · {len(menus)}개 메뉴")

c1, c2, c3 = st.columns(3)
c1.metric(f"기간 {metric_label} 합계", f"{f[col].sum():,.0f} {unit}")
c2.metric("표시 관측 수", f"{len(f)} 행")
ice_share = f.loc[f["type"] == "ICE", "cups"].sum() / f["cups"].sum() * 100
c3.metric("아이스 음료 비중", f"{ice_share:.1f} %")

st.caption("한 행은 한 달·한 메뉴입니다. 아이스 비중은 선택 기간 ICE 판매량 ÷ 전체 판매량입니다.")

# ---------- 차트 ----------
g1, g2, g3 = st.columns(3)

with g1:  # Plotly 라인: 월별 추이
    fig1 = px.line(
        f, x="month", y=col, color="menu", markers=True,
        category_orders={"menu": MENU_ORDER}, color_discrete_map=COLORS,
        labels={"month": "월", col: f"{metric_label} ({unit})", "menu": "메뉴"},
        title="월별 추이",
    )
    fig1.update_xaxes(dtick=1)
    fig1.update_yaxes(rangemode="tozero")
    fig1.update_layout(legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig1, width="stretch")

with g2:  # Matplotlib 막대: 기간 합계
    totals = f.groupby("menu")[col].sum().reindex([m for m in MENU_ORDER if m in menus])
    fig2, ax = plt.subplots(figsize=(5, 4.2))
    bars = ax.bar(
        [MENU_EN[m] for m in totals.index], totals.values,
        color=[COLORS[m] for m in totals.index],
    )
    ax.bar_label(bars, fmt="{:,.0f}", fontsize=8)
    ax.set_title("Period total")
    ax.set_ylabel("cups" if col == "cups" else "revenue (thousand KRW)")
    ax.set_xlabel("Menu")
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

with g3:  # Plotly 산점도: 기온 vs 판매량
    fig3 = px.scatter(
        f, x="avg_temp", y="cups", color="menu",
        category_orders={"menu": MENU_ORDER}, color_discrete_map=COLORS,
        hover_data={"month": True},
        labels={"avg_temp": "월 평균기온 (℃)", "cups": "판매량 (잔)", "menu": "메뉴", "month": "월"},
        title="기온과 판매량",
    )
    fig3.update_traces(marker=dict(size=9))
    fig3.update_layout(legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig3, width="stretch")

# ---------- 한 줄 해석 ----------
corr = f.groupby("menu")[["avg_temp", "cups"]].corr().unstack().iloc[:, 1]
if len(f["month"].unique()) >= 3:
    lines = [f"**{m}** {corr[m]:+.2f}" for m in MENU_ORDER if m in corr.index]
    st.info("기온–판매량 상관계수: " + " · ".join(lines) + "  \n(+는 더울수록, −는 추울수록 더 팔린다는 뜻)")

with st.expander("원본 데이터 보기"):
    st.dataframe(f, width="stretch", hide_index=True)
