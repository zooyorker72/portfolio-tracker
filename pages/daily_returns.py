import streamlit as st
import json
import pandas as pd
import pathlib
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="📈 일일 수익율",
    page_icon="📈",
    layout="wide"
)

st.markdown("# 📈 일일 수익율 트래킹")

# JSON 데이터 로드
try:
    data_path = pathlib.Path(__file__).parent.parent / "portfolio_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        portfolio_data = json.load(f)
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

# daily_history 확인
if "daily_history" not in portfolio_data or not portfolio_data["daily_history"]:
    st.warning("📭 아직 기록된 일일 수익율이 없습니다. 매일 장마감 후 자동으로 기록됩니다.")
    st.stop()

daily_history = portfolio_data["daily_history"]

# DataFrame으로 변환
df_history = pd.DataFrame(daily_history)
df_history["date"] = pd.to_datetime(df_history["date"])

# 정렬 (최신순)
df_history = df_history.sort_values("date", ascending=False).reset_index(drop=True)

# ==================== 주요 지표 ====================
col1, col2, col3, col4 = st.columns(4)

with col1:
    latest = df_history.iloc[0]
    st.metric("최신 수익율", f"{latest['daily_return_pct']:+.2f}%", 
              f"₩{latest['daily_profit']:,.0f}")

with col2:
    avg_return = df_history["daily_return_pct"].mean()
    st.metric("평균 수익율", f"{avg_return:+.2f}%", "누적 평균")

with col3:
    max_return = df_history["daily_return_pct"].max()
    st.metric("최고 수익율", f"{max_return:+.2f}%", "최고 기록")

with col4:
    min_return = df_history["daily_return_pct"].min()
    st.metric("최저 수익율", f"{min_return:+.2f}%", "최저 기록")

st.markdown("---")

# ==================== 차트 ====================
st.markdown("### 📊 수익율 추이")

# 수익율 라인 차트
fig_return, ax = plt.subplots(figsize=(12, 5))

df_sorted = df_history.sort_values("date")
ax.plot(df_sorted["date"], df_sorted["daily_return_pct"], 
        marker='o', linewidth=2, markersize=6, color='#667eea')
ax.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='기준점')
ax.fill_between(df_sorted["date"], df_sorted["daily_return_pct"], alpha=0.3, color='#667eea')

ax.set_xlabel("날짜", fontsize=11)
ax.set_ylabel("수익율 (%)", fontsize=11)
ax.set_title("일일 수익율 추이", fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig_return)

st.markdown("---")

# ==================== 자산가치 추이 ====================
st.markdown("### 💰 자산가치 추이")

fig_assets, ax = plt.subplots(figsize=(12, 5))

df_sorted = df_history.sort_values("date")
ax.plot(df_sorted["date"], df_sorted["total_current_value"]/1_000_000, 
        marker='o', linewidth=2, markersize=6, color='#f093fb', label='현재가치')
ax.plot(df_sorted["date"], df_sorted["total_investment"]/1_000_000, 
        marker='s', linewidth=2, markersize=6, color='#764ba2', label='투자원금', linestyle='--')

ax.set_xlabel("날짜", fontsize=11)
ax.set_ylabel("자산가치 (백만 원)", fontsize=11)
ax.set_title("총자산 vs 투자원금", fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend()

plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig_assets)

st.markdown("---")

# ==================== 상세 테이블 ====================
st.markdown("### 📋 일일 수익율 상세 기록")

# 표시용 DataFrame 생성
df_display = df_history.copy()
df_display["날짜"] = df_display["date"].dt.strftime("%Y-%m-%d")
df_display["시간"] = df_display["time"]
df_display["장"] = df_display["market"]
df_display["투자원금"] = df_display["total_investment"].apply(lambda x: f"₩{x:,.0f}")
df_display["현재가치"] = df_display["total_current_value"].apply(lambda x: f"₩{x:,.0f}")
df_display["손익"] = df_display["daily_profit"].apply(lambda x: f"₩{x:,.0f}")
df_display["수익율"] = df_display["daily_return_pct"].apply(lambda x: f"{x:+.2f}%")

display_cols = ["날짜", "시간", "장", "투자원금", "현재가치", "손익", "수익율"]
df_display_final = df_display[display_cols].reset_index(drop=True)
df_display_final.index = df_display_final.index + 1
df_display_final.index.name = "No"

st.dataframe(df_display_final, use_container_width=True)

# ==================== 통계 ====================
st.markdown("---")
st.markdown("### 📊 통계")

col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

with col_stats1:
    st.metric("기록 날짜 수", f"{len(df_history)}")

with col_stats2:
    positive_days = (df_history["daily_return_pct"] > 0).sum()
    st.metric("수익 날짜", f"{positive_days}일", f"{positive_days/len(df_history)*100:.1f}%")

with col_stats3:
    total_gain = df_history["daily_profit"].sum()
    st.metric("누적 손익", f"₩{total_gain:,.0f}", "전 기간")

with col_stats4:
    volatility = df_history["daily_return_pct"].std()
    st.metric("수익율 변동성", f"{volatility:.2f}%", "표준편차")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; margin-top: 40px;">
    <strong>📈 일일 수익율 트래킹</strong><br>
    매일 장마감 후 자동으로 업데이트됩니다<br>
    <small>GitHub Actions로 자동화된 데이터 수집</small>
</div>
""", unsafe_allow_html=True)
