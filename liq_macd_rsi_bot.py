import time
from binance.client import Client
from telegram import Bot
import datetime
import pytz
import numpy as np

# API (сенинг маълумотинг билан)
api_key = 'rwgn9tWQhrPkeWYEUhmzWEVO0Yt1cMOnAOgGSFwc7y8RtyHlywbBCzMyoJJmgc6H'
api_secret = 'jnazgXkFe0nEHMZcHPyDJh2f2FMjni84nGX1wetO2ntoCGBIyBj83eGgTbUsizgN'
telegram_token = '7300093292:AAFn0XkEppHk9I__y5MN9Vvz4ZtBrPJbf9Y'
chat_id = -1007927873130

client = Client(api_key, api_secret)
bot = Bot(token=telegram_token)

leverage = 40
usdt = 35
interval = Client.KLINE_INTERVAL_5MINUTE

def rsi(close_prices, period=14):
    delta = np.diff(close_prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.convolve(gain, np.ones((period,))/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones((period,))/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def macd(close_prices, fast=12, slow=26, signal=9):
    exp1 = np.convolve(close_prices, np.ones(fast)/fast, mode='valid')
    exp2 = np.convolve(close_prices, np.ones(slow)/slow, mode='valid')
    macd_line = exp1[-len(exp2):] - exp2
    signal_line = np.convolve(macd_line, np.ones(signal)/signal, mode='valid')
    return macd_line[-1], signal_line[-1]

def get_symbols():
    info = client.futures_exchange_info()
    all_symbols = [s['symbol'] for s in info['symbols'] if 'USDT' in s['symbol'] and s['contractType'] == 'PERPETUAL']
    preferred = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
    return [s for s in all_symbols if s in preferred]

def get_signal(symbol):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=100)
        closes = np.array([float(k[4]) for k in klines])
        if len(closes) < 30:
            return None
        rsi_val = rsi(closes)[-1]
        macd_val, signal_val = macd(closes)
        if rsi_val > 50 and macd_val > signal_val:
            return "BUY"
        elif rsi_val < 50 and macd_val < signal_val:
            return "SELL"
    except:
        return None

def trade(symbol, signal):
    price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
    qty = round((usdt * leverage) / price, 3)
    sl = round(price * (0.98 if signal == "BUY" else 1.02), 2)
    tp = round(price * (1.02 if signal == "BUY" else 0.98), 2)

    try:
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        client.futures_create_order(symbol=symbol, side=Client.SIDE_BUY if signal == "BUY" else Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=qty)
        client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL if signal == "BUY" else Client.SIDE_BUY, type=Client.ORDER_TYPE_STOP_MARKET, stopPrice=str(sl), quantity=qty, reduceOnly=True)
        client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL if signal == "BUY" else Client.SIDE_BUY, type=Client.ORDER_TYPE_LIMIT, price=str(tp), quantity=qty, timeInForce='GTC', reduceOnly=True)
        bot.send_message(chat_id, f"{symbol} — Ордер очилди: {signal}\\nНарх: {price}, SL: {sl}, TP: {tp}")
    except Exception as e:
        bot.send_message(chat_id, f"{symbol} — Хато: {e}")

symbols = get_symbols()
while True:
    for symbol in symbols:
        signal = get_signal(symbol)
        if signal:
            trade(symbol, signal)
        time.sleep(5)
    time.sleep(60)
