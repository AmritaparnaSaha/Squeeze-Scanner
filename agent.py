import os
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
    short_component = min((short_pct / 40.0) * 50, 50)  
    volume_component = min((vol_spike / 5.0) * 50, 50)  
    return round(short_component + volume_component)

def get_all_us_tickers():
    """Fetches every active US stock ticker directly from the SEC public database."""
    print("Fetching master ticker list from the SEC...")
    headers = {'User-Agent': 'SqueezeScannerBot open-source-project@github.com'}
    try:
        response = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        data = response.json()
        # Extract just the ticker symbols from the JSON
        tickers = [company['ticker'] for company in data.values()]
        return tickers
    except Exception as e:
        print(f"Failed to fetch SEC list: {e}")
        # Fallback list just in case the SEC website is down
        return ["GME", "AMC", "KOSS", "HOLO", "MARA", "IOVA"]

def run_agent():
    all_tickers = get_all_us_tickers()
    
    # Shuffle the massive list and pick 50 random stocks for this 10-minute batch
    batch_size = 50
    if len(all_tickers) > batch_size:
        watchlist = random.sample(all_tickers, batch_size)
    else:
        watchlist = all_tickers
        
    print(f"Randomized Batch Selected. Evaluating {len(watchlist)} tickers...")
    
    matches_found = 0
    
    for ticker in watchlist:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # The agent will skip missing data without crashing
            market_cap = info.get('marketCap') or 0
            short_float = info.get('shortPercentOfFloat') or 0
            avg_vol = info.get('averageVolume') or 1
            today_vol = info.get('volume') or 0
            
            # 1. Size & Short Interest Filter (Under $2B Cap, >12% Short)
            if market_cap == 0 or market_cap > 2000000000 or short_float < 0.12:
                continue
                
            # 2. Intraday Momentum Filter (Volume > 1.3x)
            if today_vol < (avg_vol * 1.3):
                continue
                
            vol_spike = round(today_vol / avg_vol, 1)
            short_percentage = round(short_float * 100, 2)
            squeeze_score = calculate_squeeze_score(short_percentage, vol_spike)
            
            # 3. High Priority Trigger
            if squeeze_score >= 40:
                matches_found += 1
                payload = {
                    "content": f"🚨 **RANDOM SCANNER BREAKOUT: ${ticker}**",
                    "embeds": [{
                        "title": f"Momentum Score: {squeeze_score}/100",
                        "fields": [
                            {"name": "Market Cap", "value": f"${market_cap:,.0f}", "inline": True},
                            {"name": "Short Float", "value": f"{short_percentage}%", "inline": True},
                            {"name": "Volume Multiplier", "value": f"{vol_spike}x Normal", "inline": True}
                        ]
                    }]
                }
                send_discord_message(payload)
                print(f"Breakout alert sent for {ticker}")
                
        except Exception as e:
            continue # Silently skip errors (like mutual funds or delisted stocks)

    # Status Report
    if matches_found == 0:
        payload = {
            "content": f"✅ **Batch Complete:** Scanned 50 random US stocks. 0 breakouts detected in this batch."
        }
        send_discord_message(payload)
    else:
        payload = {
            "content": f"✅ **Batch Complete:** Scanned 50 random US stocks. Found {matches_found} active breakout(s)!"
        }
        send_discord_message(payload)

if __name__ == "__main__":
    run_agent()
