#!/usr/bin/env python3
"""
포트폴리오 데이터의 현재가를 업데이트하는 스크립트
매일 주가 마감 후 실행
"""

import json
import yfinance as yf
from datetime import datetime
import pytz
import pathlib
import time

KST = pytz.timezone('Asia/Seoul')
DATA_FILE = pathlib.Path(__file__).parent / "portfolio_data.json"


def get_current_price(ticker, retries=3):
    """yfinance에서 현재가 조회 (재시도 로직 포함)"""
    for attempt in range(retries):
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
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # 2초, 4초, 8초
                print(f"⏳ {ticker} 재시도 대기 중... ({wait_time}초)")
                time.sleep(wait_time)
            else:
                print(f"⚠️ {ticker} 조회 실패: {str(e)[:80]}")
                return None
    return None


def update_portfolio_prices():
    """포트폴리오의 모든 종목 현재가 업데이트"""
    
    # 1. 데이터 로드
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            portfolio_data = json.load(f)
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return False
    
    print("📊 포트폴리오 현재가 업데이트 중...")
    print("-" * 50)
    
    updated_count = 0
    failed_count = 0
    
    # 2. 모든 계좌의 종목 순회
    for account_key, account in portfolio_data["accounts"].items():
        account_name = account.get("name", account_key)
        
        for ticker, info in account["holdings"].items():
            pure_ticker = ticker.split(" (")[0]
            
            # 현재가 조회
            current_price = get_current_price(pure_ticker)
            
            if current_price:
                info["current_price"] = round(current_price, 4)
                updated_count += 1
                print(f"✅ {pure_ticker:12} → ${current_price:.4f}")
            else:
                failed_count += 1
                print(f"⚠️  {pure_ticker:12} → 조회 실패")
    
    # 3. metadata 업데이트
    now = datetime.now(KST)
    portfolio_data["metadata"]["last_update"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 4. 파일 저장
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio_data, f, indent=2, ensure_ascii=False)
        print("-" * 50)
        print(f"💾 데이터 저장 완료")
        print(f"✅ 성공: {updated_count}개 | ⚠️ 실패: {failed_count}개")
        return True
    except Exception as e:
        print(f"❌ 파일 저장 실패: {e}")
        return False


if __name__ == "__main__":
    print(f"🐾 포트폴리오 현재가 업데이트")
    print(f"⏰ 실행 시간: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} KST")
    print()
    
    success = update_portfolio_prices()
    
    if success:
        print("\n✅ 현재가 업데이트 완료")
    else:
        print("\n❌ 현재가 업데이트 실패")
        exit(1)
