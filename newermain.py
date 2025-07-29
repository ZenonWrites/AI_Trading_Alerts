import yfinance as yf
import pandas as pd
import time
import threading
import requests
import smtplib
from email.mime.text import MIMEText
from flask import Flask, jsonify
from datetime import datetime
from typing import List, Dict
from smc import SMCDiscountStrategy
import gspread
import json
import os
from oauth2client.service_account import ServiceAccountCredentials
from indicators.smc_smart_money import check_buy_signal as smc_check_signal


# === CONFIGURATION === #
WATCHLIST = [
    'VBL.NS', 'PPLPHARMA.NS', 'SYNGENE.NS', 'COLPAL.NS', 'PATANJALI.NS',
    'EASEMYTRIP.NS', 'UNITDSPR.NS', 'IDEA.NS', 'CGCL.NS', 'ARE&M.NS',
    'TEJASNET.NS', 'GICRE.NS', 'PRAJIND.NS', 'JYOTHYLAB.NS', 'EMAMILTD.NS', 'CARBORUNIV.NS',
'SHIVALIK.NS', 'GICRE.NS',
 # Newly added stocks
'FIVESTAR.NS', 'SCPL.NS', 'SUPERSPIN.NS', 'TCS.NS', 'HIKAL.NS', 'SADBHAV.NS',
    'EQUITASBNK.NS', 'ELDEHSG.NS', 'ADL.NS', 'SALASAR.NS', 'HFCL.NS',
    'JUSTDIAL.NS', 'OLAELEC.NS', 'GLOBALVECT.NS', 'VIVIDM.NS', 'SRSOLTD.NS',
    'PPL.NS', 'POLYPLEX.NS', 'SHIVALIK.NS', 'TPLPLASTEH.NS', 'SMFIL.NS', 'MHLXMIRU.NS'
]

QUANTITY = 1
SCAN_INTERVAL = 300  # 5 minutes

# Environment variables for secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SHEET_NAME = os.getenv("SHEET_NAME", "AI_Trading_Alerts")

# Google Sheets credentials
creds_dict = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gclient = gspread.authorize(creds)
sheet = gclient.open(SHEET_NAME).sheet1

# Global log
alerts_log = []
MAX_LOG_LENGTH = 100

app = Flask(__name__)

# === ALERT FUNCTIONS === #
def send_telegram_alert(message):
    print("[TELEGRAM] Sending message...")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=data)
        print("[TELEGRAM] Response:", response.status_code, response.text)
    except Exception as e:
        print("[TELEGRAM] Error:", e)

def send_email_alert(subject, body):
    print("[EMAIL] Sending alert...")
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print("[EMAIL] Sent!")
    except Exception as e:
        print("[EMAIL] Error:", e)

def log_to_gsheet(ticker, price, tp, sl, volume):
    print("[GSHEET] Logging to sheet...")
    try:
        sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, price, tp, sl, volume])
        print("[GSHEET] Logged.")
    except Exception as e:
        print("[GSHEET] Error:", e)

# === STRATEGY === #
def check_buy_signal(ticker):
    df = yf.download(ticker, period="6mo", interval="1d")
    
    if smc_check_signal(df):
        price = df["Close"].iloc[-1]
        return {
            'ticker': ticker,
            'price': price,
            'take_profit': round(price * 1.05, 2),
            'stop_loss': round(price * 0.98, 2),
            'volume': 100,  # or fetch real volume
            'signal': True
        }
    
    return {'signal': False}

# === SCANNING === #
def scan_stocks():
    print(f"[SCAN] Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    no_signals = True

    for stock in WATCHLIST:
        try:
            # TEMP: Force dummy dataframe
            df = yf.download(stock, period="6mo", interval="1d")
            signal = check_buy_signal(df)

            print(f"[CHECK] {stock} → Signal: {signal}")
            
            if signal:
                no_signals = False
                msg = f"🚨 BUY SIGNAL for {stock}\n📈 Check it now!"
                alerts_log.append({'time': str(datetime.now()), 'stock': stock})
                send_telegram_alert(msg)
                send_email_alert(f"[ALERT] {stock}", msg)
                log_to_gsheet(stock, df['Close'].iloc[-1], "-", "-", df['Volume'].iloc[-1])

        except Exception as e:
            print(f"[ERROR] {stock}: {e}")

    if no_signals:
        print("[SCAN] No signals found.")

def start_background_scanner():
    import threading
    import time

    def job():
        while True:
            scan_stocks()
            time.sleep(SCAN_INTERVAL)  # Make sure SCAN_INTERVAL is defined (e.g., 300 seconds)

    threading.Thread(target=job, daemon=True).start()

# === FLASK ROUTES === #
@app.route('/')
def home():
    return "AI Trading Bot is live. Use /scan to scan manually or /alerts to view recent alerts."

@app.route('/scan')
def scan_now():
    scan_stocks()
    return jsonify({"status": "Scan triggered."})

@app.route('/alerts')
def get_alerts():
    return jsonify(alerts_log)

# === MAIN === #
if __name__ == '__main__':
    start_background_scanner()
    app.run(host='0.0.0.0', port=5000)