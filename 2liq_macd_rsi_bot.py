import asyncio
import logging
from binance.client import Client
from binance.enums import *
from telegram import Bot
from telegram.ext import Application, CommandHandler
import ta
import pandas as pd

# API keys
BINANCE_API_KEY = 'rwgn9tWQhrPkeWYEUhmzWEVO0Yt1cMOnAOgGSFwc7y8RtyHlywbBCzMyoJJmgc6H'
BINANCE_API_SECRET = 'jnazgXkFe0nEHMZcHPyDJh2f2FMjni84nGX1wetO2ntoCGBIyBj83eGgTbUsizgN'
TELEGRAM_TOKEN = '7300093292:AAFn0XkEppHk9I__y5MN9Vvz4ZtBrPJbf9Y'
CHAT_ID = -1002627783040  # Telegram гуруҳ ID

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
bot = Bot(TELEGRAM_TOKEN)

# Асосий монеталар (ликвид ва комиссияси паст)
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
leverage = 40
usdt_amount = 35

async def send(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        print("Telegram error:", e)

def get_data(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close',
        'volume', 'close_time', 'quote_asset_volume',
        'number_of_trades', 'taker_buy_base_asset_volume',
        'taker_buy_quote_asset_volume', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['macd'] = ta.trend.MACD(df['close']).macd_diff()
    return df

def signal_generator(df):
    rsi = df['rsi'].iloc[-1]
    macd = df['macd'].iloc[-1]
    if rsi > 60 and macd > 0:
        return 'BUY'
    elif rsi < 40 and macd < 0:
        return 'SELL'
    else:
        return ''

async def order(symbol, side):
    try:
        client.futures_change_leverage(symbol=symbol, leverage=leverage)
        price = float(client.get_symbol_ticker(symbol=symbol)['price'])
        quantity = round((usdt_amount * leverage) / price, 3)
        sl = round(price * (0.98 if side == 'BUY' else 1.02), 2)
        tp = round(price * (1.02 if side == 'BUY' else 0.98), 2)
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side == 'BUY' else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            positionSide='BOTH'
        )
        await send(f"{symbol} {side} order opened at {price}\nSL: {sl} | TP: {tp}")
    except Exception as e:
        print(f"Order error: {e}")

async def monitor():
    while True:
        for symbol in symbols:
            df = get_data(symbol, '3m')
            df = calculate_indicators(df)
            signal = signal_generator(df)
            if signal:
                await order(symbol, signal)
        await asyncio.sleep(120)

# Telegram буйруқлар
async def start(update, context):
    await update.message.reply_text("Бот ишга тушди!")

async def status(update, context):
    await update.message.reply_text("Ҳолат: Бот фаол ва кузатувда!")

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    asyncio.create_task(monitor())
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
