import os
import requests
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")


def get_key_rate():
    url = "https://www.cbr.ru/hd_base/KeyRate/"
    r = requests.get(url, timeout=10)
    html = r.text

    matches = re.findall(r"(\d{2}\.\d{2}\.\d{4}).*?(\d+,\d+)", html, re.DOTALL)

    date, rate = matches[-1]
    return float(rate.replace(",", ".")), date


def calc(rate):
    return {
        "Совкомбанк": round(rate * 0.69, 2),
        "ТКБ": round(rate - 4.5, 2),
        "Альфа-Банк": round(rate - 3.05, 2),
        "Синара": round(rate - 1.9, 2),
        "Уралсиб": round(rate - 4.5, 2),
    }


def build(rate, date):
    msg = f"📊 Ключевая ставка ЦБ РФ\n📅 {date}\n📈 {rate}%\n\n"
    for k, v in calc(rate).items():
        msg += f"{k}: {v}%\n"
    return msg


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот работает! /rate")


async def rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rate_value, date = get_key_rate()
        await update.message.reply_text(build(rate_value, date))
    except Exception as e:
        await update.message.reply_text(str(e))


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rate", rate))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
