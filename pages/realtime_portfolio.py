import streamlit as st
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import pathlib

st.set_page_config(
    page_title="💰 실시간 포트폴리오",
    page_icon="💰",
    layout="wide"
)

st.markdown("# 💰 실시간 포트폴리오 현황")

# JSON 데이터 로드
try:
    data_path = pathlib.Path(__file__).parent.parent / "portfolio_data.json"
    with open(data_path, "r", encoding="utf-8") as f:
        portfolio_data = json.load(f)
except FileNotFoundError:
    st.error(f"포트폴리오 데이터를 찾을 수 없습니다")
    st.stop()
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

exchange_rates = portfolio_data["metadata"]["exchange_rates"]

@st.cache_data(ttl=600)
def get_current_price(ticker):
    try:
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

all_holdings = {}
total_cash = 0

for account_key, account in portfolio_data["accounts"].items():
    all_holdings.update(account["holdings"])
    cash = account.get("cash", {})
    if isinstance(cash, dict):
        total_cash += cash.get("KRW", 0)
        total_cash += cash.get("CAD", 0) * exchange_rates["CAD_KRW"]
        total_cash += cash.get("AUD", 0) * exchange_rates["AUD_KRW"]

total_investment = total_cash
total_current_value = total_cash
total_profit = 0

holdings_results = []

# 종목별 손익 계산
for ticker, info in all_holdings.items():
    if "current_price" in info and info["current_price"]:
        current_price = info["current_price"]
    else:
        current_price = get_current_price(ticker)
    
    if info["currency"] == "USD":
        exchange = exchange_rates["USD_KRW"]
    elif info["currency"] == "CAD":
        exchange = exchange_rates["CAD_KRW"]
    elif info["currency"] == "AUD":
        exchange = exchange_rates["AUD_KRW"]
    else:
        exchange = 1
    
    investment = info["avg_price"] * info["quantity"] * exchange
    total_investment += investment
    
    if current_price:
        current_value = current_price * info["quantity"] * exchange
        profit = current_value - investment
        profit_pct = (profit / investment * 100) if investment > 0 else 0
        
        total_current_value += current_value
        total_profit += profit
        
        holdings_results.append({
            "종목": ticker,
            "통화": info["currency"],
            "평단": f"{info['avg_price']:.4f}",
            "수량": f"{info['quantity']:,.0f}",
            "현재가": f"{current_price:.4f}",
            "평가금액": f"₩{current_value:,.0f}",
            "손익": f"₩{profit:,.0f}",
            "수익율": f"{profit_pct:+.2f}%"
        })
    else:
        holdings_results.append({
            "종목": ticker,
            "통화": info["currency"],
            "평단": f"{info['avg_price']:.4f}",
            "수량": f"{info['quantity']:,.0f}",
            "현재가": "조회중",
            "평가금액": "조회중",
            "손익": "-",
            "수익율": "-"
        })

# 현금 항목 추가
holdings_results.append({
    "종목": "💵 현금",
    "통화": "KRW",
    "평단": "-",
    "수량": "-",
    "현재가": "-",
    "평가금액": f"₩{total_cash:,.0f}",
    "손익": "-",
    "수익율": "-"
})

avg_profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0

# 메인 지표
st.markdown("### 📊 포트폴리오 통합 현황")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("총자산", f"₩{total_current_value:,.0f}", f"+₩{total_profit:,.0f}")

with col2:
    st.metric("평가손익", f"₩{total_profit:,.0f}", f"{avg_profit_rate:+.2f}%")

with col3:
    st.metric("투자원금", f"₩{total_investment:,.0f}", "-")

with col4:
    st.metric("수익율", f"{avg_profit_rate:+.2f}%", "실시간")

st.markdown("---")

KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)

col_update1, col_update2 = st.columns(2)
with col_update1:
    st.info(f"⏰ **마지막 업데이트**: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST")

with col_update2:
    if now_kst.hour >= 15 and now_kst.minute >= 30:
        market = "🇰🇷 한국장"
    elif now_kst.hour >= 5:
        market = "🇺🇸 미국장"
    else:
        market = "🌙 장 폐장"
    st.info(f"🔄 **현재 시장**: {market}")

st.markdown("---")
st.markdown("### 📈 종목별 실시간 현황")

if holdings_results:
    df = pd.DataFrame(holdings_results)
    try:
        df_sorted = df.sort_values("수익율", key=lambda x: x.str.rstrip('%').astype(float), ascending=False)
    except:
        df_sorted = df
    
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)
else:
    st.warning("보유 종목이 없습니다.")

st.markdown("---")
st.markdown("### 🏦 계좌별 요약")

for account_key, account in portfolio_data["accounts"].items():
    account_investment = 0
    account_current = 0
    
    cash = account.get("cash", {})
    if isinstance(cash, dict):
        account_current += cash.get("KRW", 0)
        account_current += cash.get("CAD", 0) * exchange_rates["CAD_KRW"]
        account_current += cash.get("AUD", 0) * exchange_rates["AUD_KRW"]
        account_investment += cash.get("KRW", 0)
        account_investment += cash.get("CAD", 0) * exchange_rates["CAD_KRW"]
        account_investment += cash.get("AUD", 0) * exchange_rates["AUD_KRW"]
    
    for ticker, info in account["holdings"].items():
        if "current_price" in info and info["current_price"]:
            current_price = info["current_price"]
        else:
            current_price = get_current_price(ticker)
        
        if info["currency"] == "USD":
            exchange = exchange_rates["USD_KRW"]
        elif info["currency"] == "CAD":
            exchange = exchange_rates["CAD_KRW"]
        elif info["currency"] == "AUD":
            exchange = exchange_rates["AUD_KRW"]
        else:
            exchange = 1
        
        inv = info["avg_price"] * info["quantity"] * exchange
        account_investment += inv
        
        if current_price:
            curr = current_price * info["quantity"] * exchange
            account_current += curr
    
    account_profit = account_current - account_investment
    account_rate = (account_profit / account_investment * 100) if account_investment > 0 else 0
    
    st.metric(
        account["name"],
        f"₩{account_current:,.0f}",
        f"₩{account_profit:+,.0f} ({account_rate:+.2f}%)"
    )

st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #888; margin-top: 40px;">
    <strong>💰 실시간 포트폴리오 시스템</strong><br>
    yfinance 실시간 주가 + 자동 손익 계산<br>
    <small>환율: USD={exchange_rates["USD_KRW"]:,.0f}, CAD={exchange_rates["CAD_KRW"]:,.0f}, AUD={exchange_rates["AUD_KRW"]:,.0f}</small>
</div>
""", unsafe_allow_html=True)
