#!/usr/bin/env python3
"""
매일 장마감 후 포트폴리오 일일 수익율을 기록하는 스크립트

실행 시간:
- 한국장 마감: 15:30 KST
- 미국장 마감: 05:00 KST (다음날)

GitHub Actions로 자동 실행 또는 cron job으로 스케줄링
"""

import json
import yfinance as yf
from datetime import datetime
import pytz
import pathlib
import os

KST = pytz.timezone('Asia/Seoul')
DATA_FILE = pathlib.Path(__file__).parent / "portfolio_data.json"


def get_current_price(ticker):
    """yfinance에서 실시간 주가 조회"""
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
    except Exception as e:
        print(f"⚠️ {ticker} 주가 조회 실패: {e}")
        return None


def calculate_portfolio_value(portfolio_data):
    """현재 포트폴리오 평가액 계산 (JSON의 current_price 기반)"""
    exchange_rates = portfolio_data["metadata"]["exchange_rates"]
    
    total_investment = 0  # 투자 원금
    total_current_value = 0  # 현재 평가액
    
    for account_key, account in portfolio_data["accounts"].items():
        # 현금
        cash = account.get("cash", {})
        if isinstance(cash, dict):
            cash_krw = cash.get("KRW", 0)
            cash_krw += cash.get("CAD", 0) * exchange_rates["CAD_KRW"]
            cash_krw += cash.get("AUD", 0) * exchange_rates["AUD_KRW"]
            total_current_value += cash_krw
            total_investment += cash_krw
        
        # 종목
        for ticker, info in account["holdings"].items():
            pure_ticker = ticker.split(" (")[0]
            
            # ✅ JSON의 current_price를 우선 사용 (저장된 가장 최신 가격)
            if "current_price" in info and info["current_price"]:
                current_price = info["current_price"]
            else:
                # 없으면 평단가를 임시로 사용 (실시간 주가 없을 때)
                current_price = info.get("avg_price", None)
            
            # 환율 적용
            if info["currency"] == "USD":
                exchange = exchange_rates["USD_KRW"]
            elif info["currency"] == "CAD":
                exchange = exchange_rates["CAD_KRW"]
            elif info["currency"] == "AUD":
                exchange = exchange_rates["AUD_KRW"]
            else:
                exchange = 1
            
            # 투자 원금
            investment = info["avg_price"] * info["quantity"] * exchange
            total_investment += investment
            
            # 현재 평가액
            if current_price:
                current_value = current_price * info["quantity"] * exchange
                total_current_value += current_value
    
    return {
        "total_investment": total_investment,
        "total_current_value": total_current_value,
        "cumulative_profit": total_current_value - total_investment,
        "cumulative_return_pct": ((total_current_value - total_investment) / total_investment * 100) if total_investment > 0 else 0
    }


def determine_market():
    """현재 시간에 해당하는 장 결정"""
    now = datetime.now(KST)
    hour = now.hour
    minute = now.minute
    
    # 한국장 마감 (15:30)
    if hour == 15 and minute >= 30:
        return "한국장"
    elif hour == 16:
        return "한국장"
    # 미국장 마감 (05:00 - 06:30)
    elif hour >= 5 and hour < 15:
        return "미국장"
    else:
        return "폐장"


def update_daily_returns():
    """포트폴리오 일일 수익율 업데이트"""
    
    # 1. 포트폴리오 데이터 로드
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            portfolio_data = json.load(f)
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return False
    
    # 2. 포트폴리오 평가액 계산
    print("📊 포트폴리오 평가 중...")
    portfolio_value = calculate_portfolio_value(portfolio_data)
    
    # 3. daily_history 섹션이 없으면 생성
    if "daily_history" not in portfolio_data:
        portfolio_data["daily_history"] = []
    
    # 4. 어제 종가 조회 (일일 변화율 계산용)
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    yesterday_close = None
    
    # 최신 기록이 어제인지 확인
    if portfolio_data["daily_history"]:
        last_record = portfolio_data["daily_history"][-1]
        if last_record["date"] != today:  # 어제 데이터가 있으면
            yesterday_close = last_record["total_current_value"]
    
    # 5. 일일 수익율/손익 계산
    if yesterday_close is not None:
        daily_profit = portfolio_value["total_current_value"] - yesterday_close
        daily_return_pct = (daily_profit / yesterday_close * 100) if yesterday_close > 0 else 0
    else:
        # 첫 기록이거나 첫 날인 경우 0으로 설정
        daily_profit = 0
        daily_return_pct = 0
    
    # 6. 일일 수익율 레코드 생성
    daily_record = {
        "date": today,
        "time": now.strftime("%H:%M:%S"),
        "market": determine_market(),
        "total_investment": portfolio_value["total_investment"],
        "total_current_value": portfolio_value["total_current_value"],
        "cumulative_profit": portfolio_value["cumulative_profit"],
        "cumulative_return_pct": round(portfolio_value["cumulative_return_pct"], 2),
        "daily_profit": daily_profit,
        "daily_return_pct": round(daily_return_pct, 2)
    }
    
    # 7. 오늘 데이터가 이미 있으면 업데이트, 없으면 추가
    today_record_exists = False
    
    for i, record in enumerate(portfolio_data["daily_history"]):
        if record["date"] == today:
            portfolio_data["daily_history"][i] = daily_record
            today_record_exists = True
            print(f"🔄 {today} 데이터 업데이트됨")
            break
    
    if not today_record_exists:
        portfolio_data["daily_history"].append(daily_record)
        print(f"✅ {today} 데이터 추가됨")
    
    # 8. metadata 업데이트
    portfolio_data["metadata"]["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 9. 파일에 저장
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio_data, f, indent=2, ensure_ascii=False)
        print(f"💾 데이터 저장 완료")
        
        # 10. 결과 출력
        print("\n" + "="*50)
        print(f"📈 일일 수익율 업데이트 완료")
        print("="*50)
        print(f"📅 날짜: {daily_record['date']}")
        print(f"🕐 시간: {daily_record['time']}")
        print(f"🏢 장: {daily_record['market']}")
        print(f"💰 투자원금: ₩{daily_record['total_investment']:,.0f}")
        print(f"📊 현재가치: ₩{daily_record['total_current_value']:,.0f}")
        print(f"📈 누적손익: ₩{daily_record['cumulative_profit']:,.0f} ({daily_record['cumulative_return_pct']:+.2f}%)")
        print(f"📊 일일손익: ₩{daily_record['daily_profit']:,.0f}")
        print(f"📈 일일수익율: {daily_record['daily_return_pct']:+.2f}%")
        print("="*50)
        
        return True
    
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False


if __name__ == "__main__":
    print(f"🐾 클로의 포트폴리오 일일 수익율 업데이트")
    print(f"⏰ 실행 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} KST")
    print("-" * 50)
    
    success = update_daily_returns()
    
    if success:
        print("\n✅ 작업 완료")
    else:
        print("\n❌ 작업 실패")
        exit(1)
