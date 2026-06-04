import os
import yfinance as yf
import requests

def send_discord_alert(ticker, cap, short_percent, vol_spike):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Error: Discord Webhook URL secret is missing.")
        return
        
    message = {
        "content": f"🚀 **SHORT SQUEEZE RISK ALERT**\n\n"
                   f"**Ticker:** `${ticker}`\n"
                   f"• **Market Cap:** ${cap:,.0f}\n"
                   f"• **Short Float:** {short_percent}%\n"
                   f"• **Volume Momentum:** Trading at {vol_spike}x its normal average volume!\n"
                   f"• *Status: High retail interest detected via volume surge.*"
    }
    try:
        response = requests.post(webhook_url, json=message)
        if response.status_code == 204:
            print(f"Successfully sent Discord alert for {ticker}")
        else:
            print(f"Discord API returned status code {response.status_code}")
    except Exception as e:
        print(f"Failed to send alert to Discord: {e}")

def run_agent():
    # A combined master watchlist of WSB favorites, high-risk penny stocks, and volatile sectors
    wsb_favorites = ["GME", "AMC", "BB", "BYND", "SPCE", "CVNA", "UPST", "LCID", "PLUG"]
    crypto_ai_speculation = ["MARA", "RIOT", "SOUN", "BBAI", "LAZR"]
    pennystock_targets = ["KOSS", "HOLO", "NVAX", "OCGN", "WISH"]
    
    watchlist = list(set(wsb_favorites + crypto_ai_speculation + pennystock_targets))
    print(f"Evaluating {len(watchlist)} heavy retail/speculative tickers...")
    
    for ticker in watchlist:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Filter 1: Market Cap Check (Under $2 Billion)
            # Squeeze targets must be small enough for retail volume to move the price
            market_cap = info.get('marketCap') or 0
            if market_cap == 0 or market_cap > 2000000000:
                continue 
                
            # Filter 2: Short Interest Check (Over 15% of the float)
            short_float = info.get('shortPercentOfFloat') or 0
            if short_float < 0.15:
                continue
                
            # Filter 3: Retail Volume Surge Check
            avg_vol = info.get('averageVolume') or 1
            today_vol = info.get('volume') or 0
            
            # If today's volume is at least 1.5x the normal daily average, retail is swarming
            if today_vol < (avg_vol * 1.5):
                continue
                
            vol_spike = round(today_vol / avg_vol, 1)
            short_percentage = round(short_float * 100, 2)
            
            print(f"🎯 Match Found! Triggering alert for {ticker}")
            send_discord_alert(ticker, market_cap, short_percentage, vol_spike)
            
        except Exception as e:
            print(f"Could not process {ticker}: {e}")
            continue

if __name__ == "__main__":
    run_agent()
