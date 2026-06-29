import os
import requests
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")


# ---------- ЦБ РФ ----------
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
    data = calc(rate)

    msg = "ФИНТЕХ ПАНЕЛЬ ЦБ РФ\n"
    msg += f"Дата: {date}\n"
    msg += f"Ключевая ставка: {rate:.2f}%\n"
    msg += "--------------------------------\n\n"

    msg += f"{'Совкомбанк':<15} {data['Совкомбанк']:>7.2f}%\n"
    msg += f"{'ТКБ':<15} {data['ТКБ']:>7.2f}%\n"
    msg += f"{'Альфа-Банк':<15} {data['Альфа-Банк']:>7.2f}%\n"
    msg += f"{'Синара':<15} {data['Синара']:>7.2f}%\n"
    msg += f"{'Уралсиб':<15} {data['Уралсиб']:>7.2f}%\n"

    msg += "\n--------------------------------"
    return msg


# ---------- Совкомбанк (полный текст) ----------
SOVKOM_TEXT = """Совкомбанк — тарифы

Ведение счета – Бесплатно
Открытие счета – 1000 руб. (разово)
Банк-клиент – 1700 руб. (разово)

Платежи юридическим лицам – 100 руб.
Платежи физическим лицам – 100 руб. + 0,5% (но не более 3100 руб.)

Дополнительные счета в день открытия – 1000 руб. за каждый
Если открытие позже – бесплатно

Возврат задатков – бесплатно
Справки и выписки – бесплатно
"""


# ---------- меню ----------
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ставки", callback_data="banks")],
        [InlineKeyboardButton("Тарифы", callback_data="tariffs")]
    ])


def tariffs_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Совкомбанк", callback_data="bank_sovkom")],
        [InlineKeyboardButton("Уралсиб", callback_data="bank_uralsib")],
        [InlineKeyboardButton("ТКБ", callback_data="bank_tkb")],
        [InlineKeyboardButton("Альфа-Банк", callback_data="bank_alfa")],
        [InlineKeyboardButton("Синара", callback_data="bank_sinara")],
        [InlineKeyboardButton("Назад", callback_data="back")]
    ])


# ---------- start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Меню",
        reply_markup=menu()
    )


# ---------- обработка кнопок ----------
async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rate_value, date = get_key_rate()
    data = calc(rate_value)

    if query.data == "banks":
        await query.message.reply_text(build_table(rate_value, date))

    elif query.data == "tariffs":
        await query.message.reply_text("Выберите банк", reply_markup=tariffs_menu())

    elif query.data == "bank_sovkom":
        await query.message.reply_text(SOVKOM_TEXT)

    elif query.data == "bank_uralsib":
        await query.message.reply_text(f"Уралсиб {data['Уралсиб']:.2f}%")

    elif query.data == "bank_tkb":
        await query.message.reply_text(f"ТКБ {data['ТКБ']:.2f}%")

    elif query.data == "bank_alfa":
        await query.message.reply_text(f"Альфа-Банк {data['Альфа-Банк']:.2f}%")

    elif query.data == "bank_sinara":
        await query.message.reply_text(f"Синара {data['Синара']:.2f}%")

    elif query.data == "back":
        await query.message.reply_text("Меню", reply_markup=menu())


# ---------- запуск ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handler))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
