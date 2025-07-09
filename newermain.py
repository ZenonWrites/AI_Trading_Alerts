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

# === CONFIGURATION === #
WATCHLIST = [
    'VBL.NS', 'PPLPHARMA.NS', 'SYNGENE.NS', 'COLPAL.NS', 'PATANJALI.NS',
    'EASEMYTRIP.NS', 'UNITDSPR.NS', 'IDEA.NS', 'CGCL.NS', 'ARE&M.NS',
    'TEJASNET.NS', 'GICRE.NS', 'PRAJIND.NS', 'JYOTHYLAB.NS', 'EMAMILTD.NS', 'CARBORUNIV.NS',
'SHIVALIK.NS', 'GICRE.NS'
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
def check_buy_signal(ticker: str) -> Dict:
    df = yf.download(ticker, period='2mo', interval='1d', auto_adjust=True)
    if df.empty or len(df) < 30:
        return {'ticker': ticker, 'status': 'insufficient_data'}

    strategy = SMCDiscountStrategy(lookback=30, min_volume=100000, tp_percent=5.0, sl_percent=2.0)

    high_data = df['High'].tolist()
    low_data = df['Low'].tolist()
    open_data = df['Open'].tolist()
    close_data = df['Close'].tolist()
    volume = df['Volume'].iloc[-1]

    buy = strategy.generate_buy_signal(high_data, low_data, open_data, close_data, volume, timestamp=datetime.now())

    if buy:
        price = close_data[-1]
        tp, sl = strategy.calculate_tp_sl(price)
        return {
            'ticker': ticker,
            'price': price,
            'take_profit': tp,
            'stop_loss': sl,
            'volume': int(volume),
            'signal': True
        }
    return {'ticker': ticker, 'price': close_data[-1], 'signal': False}

# === SCANNING === #
def scan_stocks():
    print(f"[SCAN] Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    no_signals = True

    for stock in WATCHLIST:
        try:
            res = check_buy_signal(stock)
            print(f"[CHECK] {stock} → Signal: {res.get('signal')} | Price: {res.get('price')}")

            if res.get('signal'):
                no_signals = False
                msg = (
                    f"BUY SIGNAL: {res['ticker']}\n"
                    f"Price: ₹{res['price']:.2f}\n"
                    f"TP: ₹{res['take_profit']:.2f}\n"
                    f"SL: ₹{res['stop_loss']:.2f}\n"
                    f"Volume: {res['volume']}"
                )

                alerts_log.append({
                    'time': str(datetime.now()),
                    'stock': stock,
                    'price': res['price']
                })
                if len(alerts_log) > MAX_LOG_LENGTH:
                    alerts_log.pop(0)

                send_telegram_alert(msg)
                send_email_alert(f"[BUY ALERT] {stock}", msg)
                log_to_gsheet(stock, res['price'], res['take_profit'], res['stop_loss'], res['volume'])

        except Exception as e:
            print(f"[ERROR] Scanning {stock}: {e}")

    if no_signals:
        print("[SCAN] No signals found this round.")

# === BACKGROUND SCANNER === #
def start_background_scanner():
    def job():
        while True:
            scan_stocks()
            time.sleep(SCAN_INTERVAL)
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
