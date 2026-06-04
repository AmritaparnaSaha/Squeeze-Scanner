import os
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
    # Creates a weighted score out of 100 based on short interest and volume
    short_component = min((short_pct / 40.0) * 50, 50)  
    volume_component = min((vol_spike / 5.0) * 50, 50)  
    return round(short_component + volume_component)

def run_agent():
    watchlist = ["GME", "AMC", "BB", "BYND", "SPCE", "CVNA", "UPST", "LCID", "PLUG", "MARA", "RIOT", "SOUN", "BBAI", "KOSS", "HOLO", "NVAX"]
    matches_found = 0
    
    for ticker in watchlist:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            market_cap = info.get('marketCap') or 0
            short_float = info.get('shortPercentOfFloat') or 0
            avg_vol = info.get('averageVolume') or 1
            today_vol = info.get('volume') or 0
            
            # Base Rules: Must be Small Cap (< $2B) and have decent baseline short interest (> 12%)
            if market_cap == 0 or market_cap > 2000000000 or short_float < 0.12:
                continue
                
            # Intraday Volume Spike Check (Minimum 1.3x typical velocity)
            if today_vol < (avg_vol * 1.3):
                continue
                
            vol_spike = round(today_vol / avg_vol, 1)
            short_percentage = round(short_float * 100, 2)
            squeeze_score = calculate_squeeze_score(short_percentage, vol_spike)
            
            # High Priority Trigger: Alerts you immediately if a specific stock breaks out
            if squeeze_score >= 40:
                matches_found += 1
                payload = {
                    "content": f"🚨 **SQUEEZE BREAKOUT SCANNED: ${ticker}**",
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
            print(f"Skipping {ticker}: {e}")
            continue

    # THE MANDATORY REPORTING BLOCK
    # This guarantees a Discord notification every time GitHub runs the script
    if matches_found == 0:
        payload = {
            "content": "✅ **Scan Complete:** The agent checked all tickers. Market is calm; 0 squeeze breakouts detected right now."
        }
        send_discord_message(payload)
        print("Sent 0-matches confirmation to Discord.")
    else:
        payload = {
            "content": f"✅ **Scan Complete:** The agent found {matches_found} active breakout(s) during this check."
        }
        send_discord_message(payload)
        print("Sent multi-match confirmation to Discord.")

if __name__ == "__main__":
    run_agent()
