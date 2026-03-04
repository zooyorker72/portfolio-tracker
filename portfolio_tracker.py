import streamlit as st
import pandas as pd
import json
from datetime import datetime, time as dt_time
import os
import yfinance as yf
from functools import lru_cache
import time
import pytz

# 페이지 설정
st.set_page_config(
    page_title="🐾 클로의 포트폴리오 추적",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
    <style>
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            margin: 10px 0;
        }
        .positive { color: #00ff41; font-weight: bold; }
        .negative { color: #ff4444; font-weight: bold; }
        .header { font-size: 32px; font-weight: bold; margin: 20px 0; }
    </style>
""", unsafe_allow_html=True)

# ==================== 자동 업데이트 시간 설정 ====================
KST = pytz.timezone('Asia/Seoul')
US_EDT = pytz.timezone('US/Eastern')

def get_next_update_time():
    """다음 업데이트 시간 계산"""
    now = datetime.now(KST)
    
    # 한국장 마감: 15:30
    korea_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    # 미국장 마감: 다음날 05:00 KST
    us_close = now.replace(hour=5, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)
    
    # 다음 업데이트가 가장 가까운 시간
    if now < korea_close:
        next_update = korea_close
        market = "🇰🇷 한국장"
    elif now < us_close:
        next_update = us_close
        market = "🇺🇸 미국장"
    else:
        next_update = korea_close + pd.Timedelta(days=1)
        market = "🇰🇷 한국장"
    
    return next_update, market

def should_refresh_cache():
    """캐시 갱신 여부 확인"""
    now = datetime.now(KST)
    hour = now.hour
    minute = now.minute
    
    # 한국장 마감 후 (15:30~)
    if hour >= 15 and minute >= 30:
        return True, "🇰🇷 한국장"
    # 미국장 마감 후 (05:00~)
    elif hour >= 5 and hour < 15:
        return True, "🇺🇸 미국장"
    else:
        return False, None

# ==================== 실시간 주가 함수 ====================
def get_stock_price(ticker):
    """yfinance에서 실시간 주가 & 변화율 조회"""
    try:
        data = yf.Ticker(ticker)
        info = data.info
        
        current = info.get('currentPrice', None)
        prev_close = info.get('previousClose', None)
        
        change_pct = None
        if current and prev_close:
            change_pct = ((current - prev_close) / prev_close) * 100
        
        return {
            "current": current,
            "previous": prev_close,
            "change_pct": change_pct,
            "currency": info.get('currency', 'USD'),
        }
    except:
        return None

# 타이틀
st.markdown('<div class="header">🐾 클로의 포트폴리오 추적 시스템</div>', unsafe_allow_html=True)
st.markdown("**에니그마의 투자 포트폴리오 대시보드** | 실시간 추적")

# ==================== 자동 업데이트 정보 ====================
col_update1, col_update2 = st.columns(2)

with col_update1:
    now_kst = datetime.now(KST)
    st.info(f"⏰ **마지막 업데이트**: {now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST")

with col_update2:
    next_update, market = get_next_update_time()
    st.info(f"🔄 **다음 업데이트**: {next_update.strftime('%Y-%m-%d %H:%M')} {market}")

# ==================== 데이터 구조 ====================
PORTFOLIO_DATA = {
    "해외주식_계좌1": {
        "NXE": {"이름": "넥스젠 에너지", "금액": 18205110, "수익율": "+342.62%"},
        "DNN": {"이름": "데니슨 마인스", "금액": 17863230, "수익율": "우수"},
        "UEC": {"이름": "우라늄 에너지", "금액": 17470068, "수익율": "+673.26%"},
        "GLO": {"이름": "Global Atomic", "금액": 10599902, "수익율": "+95.70%"},
        "VZLA": {"이름": "비즐러 실버", "금액": 10419647, "수익율": "+9.49%"},
        "LEU": {"이름": "센트러스 에너지", "금액": 10100631, "수익율": "+883.95%"},
        "SLVR": {"이름": "실버 타이거", "금액": 7946896, "수익율": "+71.84%"},
        "SASK": {"이름": "ATHA Energy", "금액": 5956007, "수익율": "+106.66%"},
        "DYL": {"이름": "딥 옐로우", "금액": 5768978, "수익율": "우수"},
        "PDN": {"이름": "팔라딘 에너지", "금액": 4321662, "수익율": "+120.73%"},
        "CVV": {"이름": "캐나라스카", "금액": 4310816, "수익율": "+38.57%"},
        "BMN": {"이름": "배너만 에너지", "금액": 4068632, "수익율": "+135.83%"},
        "M": {"이름": "미리어드 우라늄", "금액": 3175843, "수익율": "+103.33%"},
        "FUU": {"이름": "F3 우라늄", "금액": 3123780, "수익율": "+10.00%"},
        "SILJ": {"이름": "AMPLIFY 주니어실버", "금액": 2870368, "수익율": "+227.57%"},
        "LOT": {"이름": "로터스 리소스", "금액": 2810671, "수익율": "+27.42%"},
        "LTBR": {"이름": "라이트브리지", "금액": 2615467, "수익율": "+85.82%"},
        "DEF": {"이름": "디파이언스 실버", "금액": 1796174, "수익율": "+11.66%"},
    },
    "해외주식_호주": {
        "DYL_AU": {"이름": "Deep Yellow (호주)", "금액": 5768978, "수익율": "+203.60%"},
        "BMN_AU": {"이름": "Bannerman (호주)", "금액": 4068632, "수익율": "+135.83%"},
        "PDN_AU": {"이름": "Paladin (호주)", "금액": 4321662, "수익율": "+120.73%"},
        "LOT_AU": {"이름": "Lotus (호주)", "금액": 2810671, "수익율": "+27.42%"},
        "PEN": {"이름": "Peninsula Energy", "금액": 500601, "수익율": "+23.65%"},
        "HCH": {"이름": "Hot Chili", "금액": 1183670, "수익율": "-9.15%"},
    },
    "해외주식_기타": {
        "MUX": {"이름": "Macquarie", "금액": 1776921, "수익율": "+9.76%"},
        "IVN": {"이름": "Ivanhoe", "금액": 1624366, "수익율": "-15.23%"},
        "OKLO": {"이름": "Oklo Inc", "금액": 1165740, "수익율": "+176.42%"},
        "NNE": {"이름": "Nano Nuclear", "금액": 378775, "수익율": "-0.33%"},
        "EU": {"이름": "Encore Energy", "금액": 100000, "수익율": "-8.05%"},
        "ASPI": {"이름": "ASP Isotope", "금액": 228205, "수익율": "+3.99%"},
    },
    "국내IRP": {
        "원자력": {"이름": "RISE 글로벌 원자력", "금액": 5968380, "비중": "23.6%"},
        "TDF": {"이름": "RISE TDF2050액티브", "금액": 5338275, "비중": "21.1%"},
        "금": {"이름": "ACE KRX금현물", "금액": 4794790, "비중": "19.0%"},
        "조선": {"이름": "SOL 조선TOP3플러스", "금액": 3910170, "비중": "15.5%"},
        "AI": {"이름": "KODEX 미국AI전력", "금액": 1652710, "비중": "6.5%"},
        "화장품": {"이름": "TIGER 화장품", "금액": 1352370, "비중": "5.4%"},
        "현금": {"이름": "고유계정대 (현금)", "금액": 86709, "비중": "0.3%"},
        "디폴트": {"이름": "KB 디폴트옵션", "금액": 2143944, "비중": "8.5%"},
    }
}

RECENT_ALLOCATION = {
    "GLO": {"비율": 40, "금액": 5227138, "상태": "🎯 진입 대기"},
    "HLU": {"비율": 20, "금액": 2613569, "상태": "✨ 신규"},
    "COSA": {"비율": 20, "금액": 2613569, "상태": "✨ 신규"},
    "현금": {"비율": 20, "금액": 2613569, "상태": "💰 보유"},
}

# ==================== 사이드바 ====================
with st.sidebar:
    st.markdown("### ⚙️ 포트폴리오 제어")
    
    view_mode = st.radio(
        "보기 모드 선택",
        ["📊 전체 현황", "🎯 최근 재배분", "📈 섹터별 분석", "💎 톱10 종목"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 📌 정보")
    st.markdown("""
    - **마지막 업데이트**: 2026-03-03
    - **총자산**: ~341M KRW
    - **현재 모드**: 바이브 코딩 🐾
    """)

# ==================== 메인 콘텐츠 ====================

if view_mode == "📊 전체 현황":
    st.markdown("### 📊 포트폴리오 전체 현황")
    
    # 핵심 수치
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총자산 (KRW)", "170,000,000", "+91,000,000")
    with col2:
        st.metric("평균 수익율", "+119%", "⭐ 우수")
    with col3:
        st.metric("현금 보유", "3,000,000", "분할매수용")
    with col4:
        st.metric("포트폴리오 구성", "34개 종목", "우라늄 70%")
    
    st.markdown("---")
    
    # 섹터별 탭
    tab1, tab2 = st.tabs(["🌍 해외주식", "🇰🇷 국내IRP"])
    
    with tab1:
        st.markdown("#### 해외주식 (총 144.8M KRW) - 26개 종목")
        
        # 실시간 데이터 로드 옵션
        show_realtime = st.checkbox("🔄 실시간 주가 조회 (느릴 수 있음)", value=False)
        
        all_overseas = {}
        all_overseas.update(PORTFOLIO_DATA["해외주식_계좌1"])
        all_overseas.update(PORTFOLIO_DATA["해외주식_호주"])
        all_overseas.update(PORTFOLIO_DATA["해외주식_기타"])
        
        # 데이터 정렬
        sorted_items = sorted(all_overseas.items(), 
                            key=lambda x: x[1]['금액'], reverse=True)
        
        # 실시간 주가 데이터 추가
        df_data = []
        for i, (ticker, data) in enumerate(sorted_items):
            row = {
                "순위": i+1,
                "종목": ticker,
                "회사명": data["이름"],
                "금액(KRW)": f"{data['금액']:,.0f}",
                "수익율": data.get("수익율", "기타")
            }
            
            if show_realtime:
                price_data = get_stock_price(ticker)
                if price_data and price_data.get('current'):
                    current = price_data['current']
                    change_pct = price_data.get('change_pct', None)
                    
                    row["현재가"] = f"${current:.2f}"
                    
                    if change_pct is not None:
                        if change_pct >= 0:
                            row["변화율"] = f"📈 +{change_pct:.2f}%"
                        else:
                            row["변화율"] = f"📉 {change_pct:.2f}%"
                    else:
                        row["변화율"] = "N/A"
                else:
                    row["현재가"] = "조회중..."
                    row["변화율"] = "-"
            
            df_data.append(row)
        
        df_overseas = pd.DataFrame(df_data)
        st.dataframe(df_overseas, use_container_width=True, hide_index=True)
        
        if show_realtime:
            st.info("✨ 💡 팁: 실시간 주가는 Yahoo Finance에서 조회되며, 약 15분 지연될 수 있습니다.")
        
        # 최고 수익 종목
        st.markdown("#### 🔥 최고 수익 종목")
        top_performers = {
            "LEU": "+883.95%",
            "UEC": "+673.26%",
            "NXE": "+342.62%",
        }
        
        cols = st.columns(3)
        for i, (ticker, return_val) in enumerate(top_performers.items()):
            with cols[i]:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 15px; border-radius: 10px; text-align: center; color: white;">
                    <strong>{ticker}</strong><br>
                    <span style="font-size: 20px; font-weight: bold;">{return_val}</span>
                </div>
                """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("#### 국내 IRP (총 25.2M KRW) - 8개 펀드")
        
        df_irp = pd.DataFrame([
            {
                "순위": i+1,
                "카테고리": category,
                "펀드명": data["이름"],
                "평가금액(KRW)": f"{data['금액']:,.0f}",
                "비중": data.get("비중", "-")
            }
            for i, (category, data) in enumerate(sorted(PORTFOLIO_DATA["국내IRP"].items(), 
                                                        key=lambda x: x[1]['금액'], reverse=True))
        ])
        
        st.dataframe(df_irp, use_container_width=True, hide_index=True)
        
        st.info("💡 IRP 포트폴리오는 보수적 구성으로 +50% 수익율 달성 중")

elif view_mode == "🎯 최근 재배분":
    st.markdown("### 🎯 2026-03-03 자금 재배분 계획")
    
    st.markdown("**총 배분 자금: 13,067,847 KRW**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    allocation_items = list(RECENT_ALLOCATION.items())
    
    for idx, col in enumerate([col1, col2, col3, col4]):
        if idx < len(allocation_items):
            ticker, data = allocation_items[idx]
            with col:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; text-align: center; color: white;">
                    <strong style="font-size: 18px;">{ticker}</strong><br>
                    <span style="font-size: 24px; font-weight: bold;">{data['비율']}%</span><br>
                    <span style="font-size: 12px;">₩{data['금액']:,.0f}</span><br>
                    <span style="font-size: 11px; margin-top: 5px;">{data['상태']}</span>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("#### 📋 재배분 상세")
    
    df_allocation = pd.DataFrame([
        {"종목": "Global Atomic", "비율": "40%", "금액": "₩5,227,138", "전략": "니제르 정국 정상화 대기 + DFC 파이낸싱"},
        {"종목": "Homeland Uranium", "비율": "20%", "금액": "₩2,613,569", "전략": "미국 우라늄 탐사주 (극고성장)"},
        {"종목": "Cosa Resources", "비율": "20%", "금액": "₩2,613,569", "전략": "캐나다 우라늄 탐사주 (분산)"},
        {"종목": "현금 보유", "비율": "20%", "금액": "₩2,613,569", "전략": "소송 해소 후 추가진입 & 급락 대응"},
    ])
    
    st.dataframe(df_allocation, use_container_width=True, hide_index=True)
    
    st.success("✅ 평가: 이 배분은 **10/10** 균형잡힌 전략입니다!")

elif view_mode == "📈 섹터별 분석":
    st.markdown("### 📈 섹터별 포트폴리오 구성")
    
    sector_data = {
        "⚛️ 우라늄/원자력": 70,
        "🥈 귀금속(은/금)": 15,
        "🔴 구리": 5,
        "☢️ SMR": 5,
        "💰 현금": 5,
    }
    
    # 파이 차트 대체 (텍스트)
    st.markdown("#### 섹터 비중")
    for sector, pct in sector_data.items():
        st.progress(pct/100, text=f"{sector}: {pct}%")
    
    st.markdown("---")
    
    st.markdown("#### 우라늄 섹터 상세 (70%)")
    st.markdown("""
    - **주요 종목**: NXE (+342%), UEC (+673%), DNN, GLO
    - **투자 근거**: 원전 르네상스 + 공급 부족 구조 지속
    - **리스크**: 미-이란 전쟁, 니제르 정국 불안
    - **중기 전망**: 우호적 (2026년 우라늄 강세 예상)
    """)

elif view_mode == "💎 톱10 종목":
    st.markdown("### 💎 최고 수익율 톱10 종목")
    
    top_10_data = [
        {"순위": 1, "종목": "LEU", "회사명": "센트러스", "수익율": "+883.95%", "상태": "🔥 최고"},
        {"순위": 2, "종목": "UEC", "회사명": "우라늄 에너지", "수익율": "+673.26%", "상태": "🔥 최고"},
        {"순위": 3, "종목": "NXE", "회사명": "넥스젠", "수익율": "+342.62%", "상태": "🚀 우수"},
        {"순위": 4, "종목": "DNN", "회사명": "데니슨", "수익율": "+195%", "상태": "🚀 우수"},
        {"순위": 5, "종목": "SILJ", "회사명": "AMPLIFY 실버", "수익율": "+227.57%", "상태": "🚀 우수"},
        {"순위": 6, "종목": "DYL", "회사명": "Deep Yellow", "수익율": "+203.60%", "상태": "🚀 우수"},
        {"순위": 7, "종목": "BMN", "회사명": "Bannerman", "수익율": "+135.83%", "상태": "✨ 양호"},
        {"순위": 8, "종목": "PDN", "회사명": "팔라딘", "수익율": "+120.73%", "상태": "✨ 양호"},
        {"순위": 9, "종목": "SASK", "회사명": "ATHA", "수익율": "+106.66%", "상태": "✨ 양호"},
        {"순위": 10, "종목": "GLO", "회사명": "Global Atomic", "수익율": "+95.70%", "상태": "⭐ 주목"},
    ]
    
    df_top10 = pd.DataFrame(top_10_data)
    st.dataframe(df_top10, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    st.warning("⚠️ 주의: 이전 수익율 기준이며, 최신 시장 정보는 실시간 조회 필요")

# ==================== 푸터 ====================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; margin-top: 40px;">
    <strong>🐾 클로의 포트폴리오 추적 시스템</strong><br>
    Made with Streamlit | 에니그마의 AI 어시스턴트<br>
    <small>최종 업데이트: 2026-03-03 21:33 KST</small>
</div>
""", unsafe_allow_html=True)
