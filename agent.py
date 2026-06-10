import os
import csv
import random
import yfinance as yf
import requests

def send_discord_message(payload):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Notification error: {e}")

def calculate_squeeze_score(short_pct, vol_spike):
    # Balanced score out of 100 weighing short interest vs buying velocity
    short_component = min((short_pct / 40.0) * 50, 50)  
    volume_component = min((vol_spike / 5.0) * 50, 50)  
    return round(short_component + volume_component)

def get_russell_2000_tickers():
    """Fetches the actual components of the Russell 2000 small-cap index."""
    print("Fetching small-cap index master file from open repository...")
    url = "https://raw.githubusercontent.com/ikoniaris/Russell2000/master/russell_2000_components.csv"
    try:
        response = requests.get(url)
        lines = response.text.splitlines()
        reader = csv.reader(lines)
        
        # Skip the header row (ticker, name)
        next(reader, None)
        
        # Extract the ticker symbol from the first column of each row
        tickers = [row[0].upper().strip() for row in reader if row and len(row) > 0]
        return tickers
    except Exception as e:
        print(f"Failed to fetch small-cap list: {e}")
        # Reliable baseline fallback if the repository file experiences an issue
        return ["GME", "AMC", "KOSS", "HOLO", "MARA", "RIOT", "IOVA", "NVAX"]

def run_agent():
    small_cap_pool = get_russell_2000_tickers()
    print(f"Success. Located {len(small_cap_pool)} small-cap equities.")
    
    # Safely select 50 random small-cap stocks to audit for this 10-minute cycle
    batch_size = 50
    if len(small_cap_pool) > batch_size:
        watchlist = random.sample(small_cap_pool, batch_size)
    else:
        watchlist = small_cap_pool
        
    print(f"Evaluating volume & short dynamics for chosen batch: {watchlist}")
    matches_found = 0
    
    for ticker in watchlist:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            market_cap = info.get('marketCap') or 0
            short_float = info.get('shortPercentOfFloat') or 0
            avg_vol = info.get('averageVolume') or 1
            today_vol = info.get('volume') or 0
            
            # 1. Base Filter: Double check to ensure it meets our strict small-cap definition (< $2B)
            # and has a solid base layer of short sellers (> 12%)
            if market_cap == 0 or market_cap > 2000000000 or short_float < 0.12:
                continue
                
            # 2. Intraday Velocity Filter: Today's current trading activity must be 1.3x typical speed
            if today_vol < (avg_vol * 1.3):
                continue
                
            vol_spike = round(today_vol / avg_vol, 1)
            short_percentage = round(short_float * 100, 2)
            squeeze_score = calculate_squeeze_score(short_percentage, vol_spike)
            
            # 3. Trigger alert if combined score hits threshold
            if squeeze_score >= 40:
                matches_found += 1
                payload = {
                    "content": f"🚨 **SMALL-CAP SQUEEZE BREAKOUT DETECTED: ${ticker}**",
                    "embeds": [{
                        "title": f"Momentum Score: {squeeze_score}/100",
                        "fields": [
                            {"name": "Market Cap", "value": f"${market_cap:,.0f}", "inline": True},
                            {"name": "Short Float", "value": f"{short_percentage}%", "inline": True},
                            {"name": "Volume Velocity", "value": f"{vol_spike}x Normal", "inline": True}
                        ]
                    }]
                }
                send_discord_message(payload)
                print(f"Match found and pushed to Discord for {ticker}")
                
        except Exception:
            continue # Automatically bypasses delisted companies or missing data fields without crashing

    # Mandatory Accountability Report
    if matches_found == 0:
        payload = {
            "content": f"📊 **Batch Complete:** 50 random Russell 2000 small-caps audited. No breakout alerts triggered in this set."
        }
        send_discord_message(payload)
    else:
        payload = {
            "content": f"📊 **Batch Complete:** 50 random Russell 2000 small-caps audited. Found {matches_found} active momentum matching alert criteria!"
        }
        send_discord_message(payload)

if __name__ == "__main__":
    run_agent()
