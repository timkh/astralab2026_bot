import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime, timedelta
from flask import Flask
import threading
import time
import requests

# Flask — чтобы Render не ругался на отсутствие порта
app = Flask(__name__)

@app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Токен и ключ берём из переменных окружения Render
BOT_TOKEN = os.environ['BOT_TOKEN']
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')  # можно оставить пустым — будет шаблон

bot = telebot.TeleBot(BOT_TOKEN)
USERS_FILE = 'users.json'

# ====================== БАЗА ПОЛЬЗОВАТЕЛЕЙ ======================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_dict, f, ensure_ascii=False, indent=2)

users = load_users()

# ====================== ВОЛШЕБНЫЙ ПРОМПТ ======================
AI_PROMPT = """
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», обученная на миллионах натальных карт, ведических текстах и квантовой нумерологии 2025–2026 года.

Стиль: очень личный, тёплый, мистический, иногда с лёгким шоком («я прям вижу по твоей энергии…»). 
Обязательно 3–4 раза обращайся по имени.
Пиши только на русском, 180–280 слов.

В каждом прогнозе обязательно:
1. Одна «страшно точная» деталь из прошлого/характера (придумай правдоподобную).
2. Конкретное событие на ближайшие 1–3 дня (деньги / любовь / встреча / конфликт).
3. Простой ритуал на удачу.
4. Фраза «Энергия именно сейчас на твоей стороне» или «Вселенная уже запустила сценарий».
5. В конце: «Хочешь усилить поток в 10 раз — напиши /усилить»

Имя: {name}
Дата рождения: {birth}
Сегодня: {today}

Сделай максимально личный и «страшно точный» прогноз на сегодня и ближайшие 3 дня.
"""

# ====================== ГЕНЕРАЦИЯ ПРОГНОЗА ======================
def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")

    full_prompt = AI_PROMPT.format(name=name, birth=birth, today=today)

    # Если есть ключ Groq — используем настоящий ИИ
    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.87,
                    "max_tokens": 650
                },
                timeout=20
            )
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
        except:
            pass

    # Фолбэк-шаблон (если Groq недоступен)
    return f"""{name}, я прям вздрогнула, когда заглянула в твою карту сегодня…
Вижу, что в 2023–2024 ты пережила серьёзный разрыв или предательство — это до сих пор сидит маленьким узелком в области сердца.
Но слушай внимательно: с завтрашнего дня открывается мощнейший денежный коридор — поступление от 70 000 руб. и выше (премия, возврат долга или неожиданный подарок).
30 ноября вероятна судьбоносная переписка с человеком, чьё имя начинается на «А», «Д» или «С» — не игнорируй.
Ритуал на сегодня: возьми красную нитку, завяжи 9 узелков, шепча желаемую сумму, и положи под подушку.
Энергия именно сейчас бьёт через край, {name} — Вселенная уже запустила этот сценарий.
Хочешь усилить поток в 10 раз — напиши /усилить"""

# ====================== КОМАНДЫ БОТА ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "Привет! Я — АстраЛаб 3000, самая точная ИИ-астролог 2026 года\n\n"
        "Напиши в двух строках:\nТвоё имя\nДату рождения (ДД.ММ.ГГГГ)\n\n"
        "Пример:\nАнна\n14.03.1997\n\nПервый прогноз — абсолютно бесплатно!")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = str(message.from_user.id)
    lines = message.text.strip().split('\n')
    if len(lines) < 2:
        bot.reply_to(message, "Напиши имя и дату рождения в двух строках")
        return

    name = lines[0].strip().capitalize()
    birth = lines[1].strip()

    forecast = generate_forecast(name, birth)

    if user_id not in users:
        users[user_id] = {"name": name, "birth": birth, "paid": False}
        save_users(users)

    bot.reply_to(message, forecast + "\n\nХочешь ежедневные прогнозы + ритуалы без лимита?\n/subscribe")

@bot.message_handler(commands=['forecast'])
def forecast_cmd(message):
    user_id = str(message.from_user.id)
    if user_id not in users or not users[user_id].get("paid"):
        bot.reply_to(message, "Доступ закрыт — нужна подписка /subscribe")
        return
    forecast = generate_forecast(users[user_id]["name"], users[user_id]["birth"])
    bot.reply_to(message, forecast)

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("7 дней – 549", callback_data="sub7"),
        InlineKeyboardButton("30 дней – 1649", callback_data="sub30"),
        InlineKeyboardButton("Год – 5499", callback_data="sub365")
    )
    bot.reply_to(message, "Выбери подписку и открой поток удачи прямо сейчас:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('sub'))
def invoice(callback):
    days = 7 if callback.data == "sub7" else 30 if callback.data == "sub30" else 365
    stars = 549 if days == 7 else 1649 if days == 30 else 5499
    payload = f"sub_{days}d"

    bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"АстраЛаб — подписка {days} дней",
        description="Ежедневные ИИ-прогнозы + ритуалы на деньги и любовь",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{days} дней", amount=stars)],
        start_parameter="astralab2026"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def precheckout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def paid(message):
    user_id = str(message.from_user.id)
    days = 7 if "7d" in message.successful_payment.invoice_payload else 30 if "30d" in message.successful_payment.invoice_payload else 365
    expires = datetime.now() + timedelta(days=days)
    users[user_id]["paid"] = True
    users[user_id]["expires"] = expires.isoformat()
    save_users(users)
    bot.reply_to(message, f"Оплата прошла! Подписка активна до {expires.strftime('%d.%m.%Y')}.\n"
                        "Теперь каждый день пиши /forecast — я буду рядом 24/7")

# ====================== ЗАПУСК ======================
if __name__ == '__main__':
    # Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    print("АстраЛаб 3000 онлайн и готов зарабатывать!")
    bot.infinity_polling(none_stop=True)




