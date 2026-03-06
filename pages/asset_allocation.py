import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import pathlib

st.set_page_config(
    page_title="📊 자산 비중",
    page_icon="📊",
    layout="wide"
)

st.markdown("# 📊 포트폴리오 자산 비중")

# JSON 데이터 로드
try:
    data_path = pathlib.Path(__file__).parent.parent / "portfolio_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        portfolio_data = json.load(f)
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

exchange_rates = portfolio_data["metadata"]["exchange_rates"]

def get_current_price(ticker):
    """yfinance에서 실시간 주가 조회"""
    try:
        import yfinance as yf
        data = yf.Ticker(ticker)
        price = data.info.get('currentPrice')
        if price:
            return price
        else:
            hist = data.history(period='1d')
            if not hist.empty:
                return hist['Close'].iloc[-1]
        return None
    except:
        return None

# 계좌별 자산 계산
def calculate_portfolio():
    """전체 포트폴리오 계산"""
    
    accounts_breakdown = {
        "한국투자증권": 0,
        "미래에셋증권": 0,
        "나무증권": 0,
        "국내_IRP": 0
    }
    
    account_short_names = {
        "korean_investment": "한국투자증권",
        "mirae_asset": "미래에셋증권",
        "namu_securities": "나무증권",
        "domestic_irp": "국내_IRP"
    }
    
    # 각 계좌별 총자산 계산
    for account_key, account in portfolio_data["accounts"].items():
        short_name = account_short_names.get(account_key, "")
        account_value = 0
        
        # 현금
        cash = account.get("cash", {})
        if isinstance(cash, dict):
            account_value += cash.get("KRW", 0)
            account_value += cash.get("CAD", 0) * exchange_rates["CAD_KRW"]
            account_value += cash.get("AUD", 0) * exchange_rates["AUD_KRW"]
        
        # 종목
        for ticker, info in account["holdings"].items():
            pure_ticker = ticker.split(" (")[0]
            
            if "current_price" in info and info["current_price"]:
                current_price = info["current_price"]
            else:
                current_price = get_current_price(pure_ticker)
            
            if info["currency"] == "USD":
                exchange = exchange_rates["USD_KRW"]
            elif info["currency"] == "CAD":
                exchange = exchange_rates["CAD_KRW"]
            elif info["currency"] == "AUD":
                exchange = exchange_rates["AUD_KRW"]
            else:
                exchange = 1
            
            if current_price:
                current_value = current_price * info["quantity"] * exchange
                account_value += current_value
        
        if short_name in accounts_breakdown:
            accounts_breakdown[short_name] = account_value
    
    return accounts_breakdown

accounts_breakdown = calculate_portfolio()

# ==================== 1. 국외 vs 국내 비율 ====================
st.markdown("### 1️⃣ 국외 vs 국내 자산 비율")

국외 = accounts_breakdown["한국투자증권"] + accounts_breakdown["미래에셋증권"] + accounts_breakdown["나무증권"]
국내 = accounts_breakdown["국내_IRP"]
총자산 = 국외 + 국내

fig_overview = go.Figure(data=[go.Pie(
    labels=["🌍 국외 투자", "🇰🇷 국내 IRP"],
    values=[국외, 국내],
    marker=dict(colors=['#1f77b4', '#ff7f0e']),
    textposition='inside',
    textinfo='label+percent+value',
    hovertemplate='<b>%{label}</b><br>₩%{value:,.0f}<br>%{percent:.1%}<extra></extra>'
)])

fig_overview.update_layout(
    showlegend=True,
    height=400,
    font=dict(size=12)
)

st.plotly_chart(fig_overview, use_container_width=True)

col_stats1, col_stats2, col_stats3 = st.columns(3)
with col_stats1:
    st.metric("🌍 국외 총자산", f"₩{국외:,.0f}", f"{국외/총자산*100:.1f}%")
with col_stats2:
    st.metric("🇰🇷 국내 총자산", f"₩{국내:,.0f}", f"{ 국내/총자산*100:.1f}%")
with col_stats3:
    st.metric("💰 전체 자산", f"₩{총자산:,.0f}")

st.markdown("---")

# ==================== 2. 국외 내부 비중 ====================
st.markdown("### 2️⃣ 국외 자산 내부 비중")

overseas_data = {
    "한국투자증권": accounts_breakdown["한국투자증권"],
    "미래에셋증권": accounts_breakdown["미래에셋증권"],
    "나무증권": accounts_breakdown["나무증권"]
}

fig_overseas = go.Figure(data=[go.Bar(
    x=list(overseas_data.keys()),
    y=list(overseas_data.values()),
    marker=dict(color=['#1f77b4', '#2ca02c', '#d62728']),
    text=[f"₩{v:,.0f}<br>({v/국외*100:.1f}%)" for v in overseas_data.values()],
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>₩%{y:,.0f}<extra></extra>'
)])

fig_overseas.update_layout(
    xaxis_title="증권사",
    yaxis_title="자산가치 (₩)",
    height=400,
    showlegend=False
)

st.plotly_chart(fig_overseas, use_container_width=True)

# 국외 계좌별 상세
col_overseas1, col_overseas2, col_overseas3 = st.columns(3)
with col_overseas1:
    st.metric("한국투자증권", f"₩{overseas_data['한국투자증권']:,.0f}", 
              f"{overseas_data['한국투자증권']/국외*100:.1f}%")
with col_overseas2:
    st.metric("미래에셋증권", f"₩{overseas_data['미래에셋증권']:,.0f}",
              f"{overseas_data['미래에셋증권']/국외*100:.1f}%")
with col_overseas3:
    st.metric("나무증권", f"₩{overseas_data['나무증권']:,.0f}",
              f"{overseas_data['나무증권']/국외*100:.1f}%")

st.markdown("---")

# ==================== 3. 국내 IRP 비중 ====================
st.markdown("### 3️⃣ 국내 IRP 자산 내부 비중")

irp_account = portfolio_data["accounts"]["domestic_irp"]
irp_breakdown = {}

exchange_rates = portfolio_data["metadata"]["exchange_rates"]

for ticker, info in irp_account["holdings"].items():
    if "current_price" in info and info["current_price"]:
        current_price = info["current_price"]
    else:
        current_price = get_current_price(ticker)
    
    if current_price:
        current_value = current_price * info.get("quantity", 1)
        irp_breakdown[ticker] = current_value

# 현금
cash = irp_account.get("cash", {})
if isinstance(cash, dict):
    cash_krw = cash.get("KRW", 0)
    if cash_krw > 0:
        irp_breakdown["현금"] = cash_krw

fig_irp = px.pie(
    values=list(irp_breakdown.values()),
    names=list(irp_breakdown.keys()),
    title="IRP 내부 자산 구성",
    hole=0,
    text_info="label+percent"
)

fig_irp.update_traces(
    hovertemplate='<b>%{label}</b><br>₩%{value:,.0f}<br>%{percent:.1%}<extra></extra>'
)

fig_irp.update_layout(
    height=400,
    font=dict(size=11)
)

st.plotly_chart(fig_irp, use_container_width=True)

# IRP 항목별 상세
st.markdown("#### IRP 항목별 상세")
irp_df = pd.DataFrame([
    {
        "항목": name,
        "자산가치": f"₩{value:,.0f}",
        "비중": f"{value/국내*100:.2f}%"
    }
    for name, value in sorted(irp_breakdown.items(), key=lambda x: x[1], reverse=True)
])

st.dataframe(irp_df, use_container_width=True, hide_index=True)

st.markdown("---")

# ==================== 요약 ====================
st.markdown("### 📊 포트폴리오 요약")

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    st.metric("전체 자산", f"₩{총자산:,.0f}")

with summary_col2:
    st.metric("국외 비중", f"{국외/총자산*100:.1f}%")

with summary_col3:
    st.metric("국내 비중", f"{국내/총자산*100:.1f}%")

with summary_col4:
    st.metric("계좌 수", "4개")
