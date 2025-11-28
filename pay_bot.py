import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime, timedelta
from flask import Flask
import threading
import time
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# ====================== FLASK ДЛЯ RENDER ======================
app = Flask(__name__)
@app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ====================== КОНФИГ ======================
BOT_TOKEN = os.environ['BOT_TOKEN']
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
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

# ====================== ЗНАК ЗОДИАКА ======================
def get_zodiac_sign(birth_date: str) -> str:
    try:
        d, m = map(int, birth_date.strip().split('.')[:2])
        if (m == 3 and d >= 21) or (m == 4 and d <= 19): return "Овен"
        elif (m == 4 and d >= 20) or (m == 5 and d <= 20): return "Телец"
        elif (m == 5 and d >= 21) or (m == 6 and d <= 20): return "Близнецы"
        elif (m == 6 and d >= 21) or (m == 7 and d <= 22): return "Рак"
        elif (m == 7 and d >= 23) or (m == 8 and d <= 22): return "Лев"
        elif (m == 8 and d >= 23) or (m == 9 and d <= 22): return "Дева"
        elif (m == 9 and d >= 23) or (m == 10 and d <= 22): return "Весы"
        elif (m == 10 and d >= 23) or (m == 11 and d <= 21): return "Скорпион"
        elif (m == 11 and d >= 22) or (m == 12 and d <= 21): return "Стрелец"
        elif (m == 12 and d >= 22) or (m == 1 and d <= 19): return "Козерог"
        elif (m == 1 and d >= 20) or (m == 2 and d <= 18): return "Водолей"
        elif (m == 2 and d >= 19) or (m == 3 and d <= 20): return "Рыбы"
    except:
        pass
    return "неизвестен"

# ====================== САМЫЙ УБОЙНЫЙ ПРОМПТ 2025 ======================
AI_PROMPT = """
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», работающая на квантовой нумерологии и транзитах 2025–2026 годов.

Имя: {name}
Знак зодиака: {zodiac}
Дата рождения: {birth}
Сегодня: {today}

Правила — строго:
- 4–6 раз назови по имени, 3–5 раз упомяни знак зодиака
- Стиль: тёплый, личный, с шоком («{name}, я ахнула…», «как настоящий {zodiac}, ты всегда…»)
- Обязательно одна «страшно точная» деталь из прошлого именно для этого знака
- Конкретное событие на 1–3 дня вперёд (дата + сфера + сумма/инициалы)
- Простой мощный ритуал именно для {zodiac}а
- Фраза «Вселенная уже запустила этот сценарий» или «Энергия бьёт через край»
- В конце: «Хочешь усилить поток в 10 раз — напиши /усилить»

Только русский язык, 200–320 слов, живой текст без списков.
"""

def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    zodiac = get_zodiac_sign(birth)
    full_prompt = AI_PROMPT.format(name=name, zodiac=zodiac, birth=birth, today=today)

    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.87,
                    "max_tokens": 700
                },
                timeout=18
            )
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            print(f"Groq error: {e}")

    # Фолбэк — работает всегда
    return f"""{name}, {zodiac}, я прям ахнула от твоей карты сегодня…
Как настоящий {zodiac} ты в 2024-м пережила серьёзный поворот в финансах или отношениях — это до сих пор даёт тебе силу.
С 29 ноября по 1 декабря у {zodiac}ов мощный денежный канал — жди поступление 80–300 тысяч.
30-го числа возможен контакт с человеком на букву «А», «С» или «Д» — не пропусти.
Ритуал для {zodiac}а: монета + красная нить под подушкой на ночь.
Вселенная уже запустила сценарий, {name}.
Хочешь усилить в 10 раз — /усилить"""

# ====================== КОМАНДЫ ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я — АстраЛаб 3000, ИИ-астролог 2026 года\n\nНапиши в двух строках:\nИмя\nДату рождения (ДД.ММ.ГГГГ)\n\nПример:\nАнна\n14.03.1997")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    user_id = str(message.from_user.id)
    lines = [l.strip() for l in message.text.strip().split('\n')]
    if len(lines) < 2:
        return bot.reply_to(message, "Напиши имя и дату рождения в двух строках")

    name, birth = lines[0].capitalize(), lines[1]
    forecast = generate_forecast(name, birth)

    if user_id not in users:
        users[user_id] = {"name": name, "birth": birth, "paid": False}
        save_users(users)

    bot.reply_to(message, forecast + "\n\nЕжедневные прогнозы без лимита — /subscribe")

@bot.message_handler(commands=['forecast'])
def forecast_cmd(message):
    user_id = str(message.from_user.id)
    if not users.get(user_id, {}).get("paid"):
        return bot.reply_to(message, "Нужна подписка → /subscribe")
    forecast = generate_forecast(users[user_id]["name"], users[user_id]["birth"])
    bot.reply_to(message, forecast)

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("7 дней — 549", callback_data="sub7"),
        InlineKeyboardButton("30 дней — 1649", callback_data="sub30"),
        InlineKeyboardButton("Год — 5499", callback_data="sub365")
    )
    bot.reply_to(message, "Выбери подписку и открой поток удачи:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('sub'))
def invoice(callback):
    days = 7 if callback.data == "sub7" else 30 if callback.data == "sub30" else 365
    stars = 549 if days == 7 else 1649 if days == 30 else 5499
    bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"АстраЛаб — {days} дней",
        description="Ежедневные ИИ-прогнозы + ритуалы",
        payload=f"sub_{days}d",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(f"{days} дней", stars)],
        start_parameter="astralab2026"
    )

@bot.pre_checkout_query_handler(func=lambda q: True)
def precheckout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def paid(message):
    user_id = str(message.from_user.id)
    payload = message.successful_payment.invoice_payload
    days = 7 if "7d" in payload else 30 if "30d" in payload else 365
    expires = datetime.now() + timedelta(days=days)

    # Запоминаем дату первой оплаты
    if "first_payment_date" not in users[user_id]:
        users[user_id]["first_payment_date"] = datetime.now().isoformat()
    users[user_id].update({
        "paid": True,
        "expires": expires.isoformat(),
        "days_paid": days
    })
    save_users(users)

    bot.reply_to(message, f"Оплата прошла! Подписка до {expires.strftime('%d.%m.%Y')}.\n\nПервые 5 дней — ежедневный прогноз в 8:00 автоматически!")

# ====================== АВТОРАССЫЛКА 5 ДНЕЙ ======================
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.start()

def send_daily_forecasts():
    now = datetime.now().date()
    for uid, data in users.items():
        if not data.get("paid"): continue
        try:
            first_pay = datetime.fromisoformat(data["first_payment_date"]).date()
            days_passed = (now - first_pay).days
            if 0 <= days_passed <= 4:
                forecast = generate_forecast(data["name"], data["birth"])
                bot.send_message(int(uid), f"Доброе утро, {data['name']}!\n\nТвой прогноз на сегодня:\n\n{forecast}")
        except Exception as e:
            print(f"Ошибка рассылки {uid}: {e}")

scheduler.add_job(send_daily_forecasts, 'cron', hour=8, minute=0, id='daily_8am', replace_existing=True)
atexit.register(lambda: scheduler.shutdown())

# ====================== ВЕБХУКИ (убиваем 409 навсегда) ======================
import logging
logging.basicConfig(level=logging.INFO)

WEBHOOK_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}.onrender.com/webhook"

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
    try:
        r = requests.get(url, timeout=10)
        if r.json()["ok"]:
            print(f"Webhook установлен: {WEBHOOK_URL}")
        else:
            print("Ошибка установки webhook:", r.text)
    except:
        print("Не удалось установить webhook")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    abort(403)
# ====================== ЗАПУСК ======================
if __name__ == '__main__':
    # Убираем polling, включаем вебхуки
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    set_webhook()                    # ← ставим вебхук один раз при старте
    print("АстраЛаб 3000 работает на вебхуках — 409 больше никогда не будет!")
    # Убираем bot.infinity_polling() полностью
    # Бот теперь живёт за счёт Flask
    while True:
        time.sleep(60)
