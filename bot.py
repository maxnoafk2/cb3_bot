import os
import requests
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")


# ---------- ЦБ ----------
def get_key_rate():
    url = "https://www.cbr.ru/hd_base/KeyRate/"
    r = requests.get(url, timeout=10)
    html = r.text

    matches = re.findall(r"(\d{2}\.\d{2}\.\d{4}).*?(\d+,\d+)", html, re.DOTALL)
    date, rate = matches[-1]

    return float(rate.replace(",", ".")), date


# ---------- расчёты ----------
def calc(rate):
    return {
        "Совкомбанк": rate * 0.69,
        "ТКБ": rate - 4.5,
        "Альфа-Банк": rate - 3.05,
        "Синара": rate - 1.9,
        "Уралсиб": rate - 4.5,
    }


# ---------- таблица ----------
def build_table(rate, date):
    msg = f"📊 КЛЮЧЕВАЯ СТАВКА ЦБ РФ\n"
    msg += f"📅 {date}\n"
    msg += f"📈 {rate:.2f}%\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"

    for k, v in calc(rate).items():
        msg += f"{k:<15}{v:>10.2f}%\n"

    msg += "━━━━━━━━━━━━━━━━━━"
    return msg


# ---------- СОВКОМБАНК (ЧИСТЫЙ ТЕКСТ) ----------
SOVKOM_TEXT = """🏦 Совкомбанк — тарифы

💼 Ведение счета – Бесплатно  
💳 Открытие счета – 1000 ₽ (разово)  
🖥 Банк-клиент – 1700 ₽ (разово)  

📄 Платежи:  
• ЮЛ – 100 ₽  
• ФЛ – 100 ₽ + 0,5% (но не более 3100 ₽)  

📊 Дополнительно:  
• Доп. счета в день открытия – 1000 ₽ за каждый  
• Если позже — бесплатно  
• Возврат задатков – бесплатно  
• Справки и выписки – бесплатно  
"""


# ---------- ГЛАВНОЕ МЕНЮ ----------
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 КС ЦБ", callback_data="rate")],
        [InlineKeyboardButton("🏦 Ставки", callback_data="banks")],
        [InlineKeyboardButton("📊 Тарифы", callback_data="tariffs")]
    ])


# ---------- ТАРИФЫ ----------
def tariffs_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Совкомбанк", callback_data="bank_sovkom")],
        [InlineKeyboardButton("Уралсиб", callback_data="bank_uralsib")],
        [InlineKeyboardButton("ТКБ", callback_data="bank_tkb")],
        [InlineKeyboardButton("Альфа-Банк", callback_data="bank_alfa")],
        [InlineKeyboardButton("Синара", callback_data="bank_sinara")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Финтех-бот запущен",
        reply_markup=menu()
    )


# ---------- CALLBACK ----------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rate_value, date = get_key_rate()
    data = calc(rate_value)

    # --- главное меню ---
    if query.data == "rate":
        await query.message.reply_text(build_table(rate_value, date))

    elif query.data == "banks":
        await query.message.reply_text(build_table(rate_value, date))

    elif query.data == "tariffs":
        await query.message.reply_text("Выберите банк:", reply_markup=tariffs_menu())

    # --- тарифы ---
    elif query.data == "bank_sovkom":
        await query.message.reply_text(SOVKOM_TEXT)

    elif query.data == "bank_uralsib":
        await query.message.reply_text(f"🏦 Уралсиб: {data['Уралсиб']:.2f}%")

    elif query.data == "bank_tkb":
        await query.message.reply_text(f"🏦 ТКБ: {data['ТКБ']:.2f}%")

    elif query.data == "bank_alfa":
        await query.message.reply_text(f"🏦 Альфа-Банк: {data['Альфа-Банк']:.2f}%")

    elif query.data == "bank_sinara":
        await query.message.reply_text(f"🏦 Синара: {data['Синара']:.2f}%")

    elif query.data == "back":
        await query.message.reply_text("Главное меню", reply_markup=menu())


# ---------- MAIN ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handler))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
