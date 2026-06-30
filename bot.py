import os
import re
import time
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ---------- конфиг ----------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не задан — установите переменную окружения TOKEN")

CACHE_TTL = 3600
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- тарифы ----------
BANKS = {
    "Совкомбанк": {
        "formula": lambda r: r * 0.69,
        "tariff": (
            "Ведение счёта — бесплатно\n"
            "Открытие счёта — 1000 руб. (разово)\n"
            "Банк-клиент — 1700 руб. (разово)\n"
            "Платежи юр. лицам — 100 руб.\n"
            "Платежи физ. лицам — 100 руб. + 0,5% (макс. 3100 руб.)\n"
            "Доп. счета в день открытия — 1000 руб./шт, позже — бесплатно\n"
            "Возврат задатков, справки, выписки — бесплатно"
        ),
    },
    "ТКБ":        {"formula": lambda r: r - 4.5,  "tariff": "Тарифы уточняются."},
    "Альфа-Банк": {"formula": lambda r: r - 3.05, "tariff": "Тарифы уточняются."},
    "Синара":     {"formula": lambda r: r - 1.9,  "tariff": "Тарифы уточняются."},
    "Уралсиб":    {"formula": lambda r: r - 4.5,  "tariff": "Тарифы уточняются."},
}

CALLBACK_TO_BANK = {
    f"bank_{k.lower().replace('-', '').replace(' ', '')}": k for k in BANKS
}

# ---------- кеш ставки ----------
_cache: dict = {"rate": None, "date": None, "ts": 0}


def get_key_rate() -> tuple[float, str]:
    if _cache["rate"] and time.time() - _cache["ts"] < CACHE_TTL:
        return _cache["rate"], _cache["date"]
    try:
        r = requests.get("https://www.cbr.ru/hd_base/KeyRate/", timeout=10)
        r.raise_for_status()
        matches = re.findall(r"(\d{2}\.\d{2}\.\d{4}).*?(\d+,\d+)", r.text, re.DOTALL)
        if not matches:
            raise ValueError("Ставка не найдена в HTML")
        date, rate_str = matches[-1]
        rate = float(rate_str.replace(",", "."))
        _cache.update({"rate": rate, "date": date, "ts": time.time()})
        return rate, date
    except Exception as e:
        logger.error(f"Ошибка ЦБ: {e}")
        if _cache["rate"]:
            logger.warning("Используем кешированную ставку")
            return _cache["rate"], _cache["date"]
        raise RuntimeError("Не удалось получить ключевую ставку. Попробуйте позже.")


# ---------- экраны ----------
def screen_main() -> tuple[str, InlineKeyboardMarkup]:
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Ставки", callback_data="rates")],
        [InlineKeyboardButton("Тарифы", callback_data="tariffs")],
    ])
    return "Выберите раздел:", markup


def screen_rates() -> tuple[str, InlineKeyboardMarkup]:
    rate, date = get_key_rate()
    lines = [
        f"<b>Дата:</b> {date}",
        f"<b>Ключевая ставка:</b> {rate:.2f}%",
        "",
    ]
    for bank, info in BANKS.items():
        value = info["formula"](rate)
        lines.append(f"<b>{bank}</b> — {value:.2f}%")

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="main")]])
    return "\n".join(lines), markup


def screen_tariffs() -> tuple[str, InlineKeyboardMarkup]:
    buttons = [
        [InlineKeyboardButton(name, callback_data=cb)]
        for cb, name in CALLBACK_TO_BANK.items()
    ]
    buttons.append([InlineKeyboardButton("Назад", callback_data="main")])
    return "Выберите банк:", InlineKeyboardMarkup(buttons)


def screen_bank(bank_name: str) -> tuple[str, InlineKeyboardMarkup]:
    rate, _ = get_key_rate()
    info = BANKS[bank_name]
    value = info["formula"](rate)
    text = (
        f"<b>{bank_name}</b>\n"
        f"{'─' * 32}\n"
        f"{info['tariff']}\n"
        f"{'─' * 32}\n"
        f"Актуальная ставка: <b>{value:.2f}%</b>"
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="tariffs")]])
    return text, markup


# ---------- роутер ----------
SCREENS = {
    "main":    screen_main,
    "rates":   screen_rates,
    "tariffs": screen_tariffs,
    **{cb: (lambda b: lambda: screen_bank(b))(bank) for cb, bank in CALLBACK_TO_BANK.items()},
}


# ---------- утилита: отправить или отредактировать ----------
async def render(update: Update, text: str, markup: InlineKeyboardMarkup, parse_mode: str = "HTML"):
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, reply_markup=markup, parse_mode=parse_mode
        )
    else:
        await update.message.reply_text(
            text, reply_markup=markup, parse_mode=parse_mode
        )


# ---------- хендлеры ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, markup = screen_main()
    await render(update, text, markup)


async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    screen_fn = SCREENS.get(query.data)
    if not screen_fn:
        return

    try:
        text, markup = screen_fn()
    except RuntimeError as e:
        await query.message.edit_text(f"Ошибка: {e}")
        return

    await render(update, text, markup)


# ---------- запуск ----------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handler))
    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
