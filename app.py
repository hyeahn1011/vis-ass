from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="마감 직전 인류 보고서", page_icon="⏰", layout="wide")

# ---------- 데이터 ----------
@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(Path(__file__).parent / "submissions.csv")
    bins = [-1e9, 0, 1, 6, 24, 72, 1e9]
    labels = ["지각", "1시간 이내", "1~6시간", "6~24시간", "1~3일", "3일 이상"]
    df["bucket"] = pd.cut(df["hours_before"], bins=bins, labels=labels, right=False)
    return df


df = load_data()

TYPE_ORDER = ["전공", "교양", "팀플", "실습"]
COLORS = {"전공": "#2E5BBA", "교양": "#27AE60", "팀플": "#E74C3C", "실습": "#8E44AD"}
BUCKET_ORDER = ["지각", "1시간 이내", "1~6시간", "6~24시간", "1~3일", "3일 이상"]
EXAM_WEEKS = [7, 8, 14, 15, 16]

# ---------- 사이드바 ----------
with st.sidebar:
    st.header("조회 조건")
    types = st.multiselect("과목 유형", TYPE_ORDER, default=TYPE_ORDER)
    w_start, w_end = st.slider("주차 범위", 1, 16, (1, 16))
    metric_label = st.selectbox(
        "추이 지표", ["마감 전 남은 시간(중앙값)", "벼락치기 비율", "평균 점수"]
    )
    st.caption("벼락치기 = 마감 1시간 이내 제출 또는 지각 제출")

# ---------- 헤더 ----------
st.title("과제는 마감 몇 시간 전에 제출되는가")
st.caption(
    "출처: 수업용 가상 데이터(submissions.csv) · 2026년 2학기 16주 · e-Class 과제 제출 로그 "
    "· 모든 과제 마감은 23:59 · 시험기간: 7·8주, 14~16주"
)

if not types:
    st.warning("왼쪽에서 과목 유형을 하나 이상 선택하세요.")
    st.stop()

f = df[df["course_type"].isin(types) & df["week"].between(w_start, w_end)].copy()
f["cram"] = f["hours_before"] < 1

# ---------- 지표 ----------
st.subheader(f"{w_start}~{w_end}주차 · {', '.join(types)}")

c1, c2, c3 = st.columns(3)
c1.metric("제출 건수", f"{len(f):,} 건")
c2.metric("벼락치기 비율", f"{f['cram'].mean() * 100:.1f} %")
c3.metric("마감 전 남은 시간(중앙값)", f"{f['hours_before'].median():.1f} 시간")

st.caption("한 행은 과제 제출 1건입니다. 남은 시간이 음수면 마감 후(지각) 제출입니다.")

# ---------- 차트 ----------
g1, g2, g3 = st.columns(3)

with g1:  # Plotly 라인: 주차별 추이
    weekly = (
        f.groupby(["week", "course_type"])
        .agg(median_h=("hours_before", "median"),
             cram=("cram", "mean"),
             score=("score", "mean"))
        .reset_index()
    )
    weekly["cram"] *= 100
    ycol, ylab = {
        "마감 전 남은 시간(중앙값)": ("median_h", "남은 시간 중앙값 (시간)"),
        "벼락치기 비율": ("cram", "벼락치기 비율 (%)"),
        "평균 점수": ("score", "평균 점수 (점)"),
    }[metric_label]
    fig1 = px.line(
        weekly, x="week", y=ycol, color="course_type", markers=True,
        category_orders={"course_type": TYPE_ORDER}, color_discrete_map=COLORS,
        labels={"week": "주차", ycol: ylab, "course_type": "과목 유형"},
        title="주차별 추이",
    )
    for w in EXAM_WEEKS:  # 시험기간 음영
        if w_start <= w <= w_end:
            fig1.add_vrect(x0=w - 0.5, x1=w + 0.5, fillcolor="gray",
                           opacity=0.12, line_width=0)
    fig1.update_xaxes(dtick=1)
    if ycol != "score":
        fig1.update_yaxes(rangemode="tozero")
    fig1.update_layout(legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig1, width="stretch")

with g2:  # Matplotlib 막대: 제출 시각 분포
    hourly = f["submit_hour"].value_counts().reindex(range(24), fill_value=0)
    fig2, ax = plt.subplots(figsize=(5, 4.2))
    colors = ["#E74C3C" if h >= 22 else "#95A5A6" for h in hourly.index]
    ax.bar(hourly.index, hourly.values, color=colors)
    ax.set_title("Submissions by hour of day")
    ax.set_xlabel("Hour (deadline = 23:59)")
    ax.set_ylabel("submissions")
    ax.set_xticks(range(0, 24, 3))
    ax.spines[["top", "right"]].set_visible(False)
    late_night = hourly.loc[22:23].sum() / max(hourly.sum(), 1) * 100
    ax.text(0.02, 0.95, f"22-24h: {late_night:.0f}% of all", transform=ax.transAxes,
            va="top", fontsize=9, color="#E74C3C")
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close(fig2)

with g3:  # Plotly 박스: 일찍 낼수록 점수가 높을까
    fig3 = px.box(
        f, x="bucket", y="score",
        category_orders={"bucket": BUCKET_ORDER},
        labels={"bucket": "제출 시점 (마감 기준)", "score": "점수"},
        title="일찍 내면 점수가 높을까",
        color_discrete_sequence=["#2E5BBA"],
    )
    st.plotly_chart(fig3, width="stretch")

# ---------- 한 줄 해석 ----------
early = f.loc[f["hours_before"] >= 24, "score"].mean()
cram = f.loc[f["cram"], "score"].mean()
if pd.notna(early) and pd.notna(cram):
    st.info(
        f"하루 이상 일찍 낸 과제 평균 **{early:.1f}점** vs 벼락치기 과제 평균 **{cram:.1f}점** "
        f"→ 차이 **{early - cram:+.1f}점**"
    )

with st.expander("원본 데이터 보기"):
    st.dataframe(f.drop(columns=["cram"]), width="stretch", hide_index=True)
