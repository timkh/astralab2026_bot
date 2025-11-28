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

# ====================== Flask (чтобы Render не ругался на порты) ======================
app = Flask(__name__)

@app.route('/')
def index():
    return "АстраЛаб 3000 работает → @Astralab2026_bot", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ====================== Конфиг ======================
BOT_TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
bot = telebot.TeleBot(BOT_TOKEN)
USERS_FILE = "users.json"

# ====================== База пользователей ======================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_users()

# ====================== Знак зодиака ======================
def get_zodiac_sign(birth):
    try:
        d, m = map(int, birth.split('.')[:2])
        return ("Козерог","Водолей","Рыбы","Овен","Телец","Близнецы",
                "Рак","Лев","Дева","Весы","Скорпион","Стрелец")[
            (d > (19,18,20,19,20,20,22,22,22,22,21,21)[m-1])
        ]
    except:
        return "неизвестен"

# ====================== Самый убойный промпт 2025 ======================
AI_PROMPT = """
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», работающая на квантовой нумерологии и транзитах 2025–2026 годов.

Имя: {name}
Знак зодиака: {zodiac}
Дата рождения: {birth}
Сегодня: {today}

Строго соблюдай:
- 4–6 раз обратись по имени, 3–5 раз упомяни знак зодиака
- Стиль тёплый, личный, с лёгким шоком («{name}, я ахнула…», «как настоящий {zodiac}, ты…»)
- Одна «страшно точная» деталь из прошлого именно для этого знака
- Конкретное событие на ближайшие 1–3 дня (точные даты + сфера + сумма или инициалы)
- Простой мощный ритуал под знак
- Фраза «Вселенная уже запустила этот сценарий» или «Энергия бьёт через край»
- В конце всегда: «Хочешь усилить поток в 10 раз — напиши /усилить»

Только русский, 200–320 слов, живой текст без списков.
"""

def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    zodiac = get_zodiac_sign(birth)
    prompt = AI_PROMPT.format(name=name, zodiac=zodiac, birth=birth, today=today)

    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.87,
                    "max_tokens": 700
                },
                timeout=18
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("Groq error: {e}")

    # Фолбэк
    return f"""{name}, {zodiac}, я ахнула от твоей карты сегодня…
Как настоящий {zodiac} ты в 2024-м пережила серьёзный поворот — это до сих пор даёт тебе силу.
С 29 ноября по 1 декабря у {zodiac}ов мощный денежный канал — поступление 80–350 тысяч.
30-го жди важный контакт (буквы «А», «С» или «Д»).
Ритуал: монета + красная нить под подушкой на ночь.
Вселенная уже запустила сценарий, {name}.
Хочешь усилить в 10 раз — /усилить"""

# ====================== Команды бота ======================
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Привет! Я — АстраЛаб 3000, ИИ-астролог 2026 года\n\nНапиши в двух строках:\nИмя\nДД.ММ.ГГГГ\n\nПример:\nАнна\n14.03.1997")

@bot.message_handler(content_types=['text'])
def handle_text(m):
    if m.text.startswith('/'): return
    lines = [x.strip() for x in m.text.split('\n') if x.strip()]
    if len(lines) < 2:
        return bot.reply_to(m, "Имя и дата рождения — в двух строках")
    name, birth = lines[0].capitalize(), lines[1]
    uid = str(m.from_user.id)
    users.setdefault(uid, {"name": name, "birth": birth, "paid": False})
    save_users(users)
    bot.reply_to(m, generate_forecast(name, birth) + "\n\nЕжедневные прогнозы — /subscribe")

@bot.message_handler(commands=['forecast'])
def forecast(m):
    uid = str(m.from_user.id)
    if not users.get(uid, {}).get("paid"):
        return bot.reply_to(m, "Нужна подписка → /subscribe")
    bot.reply_to(m, generate_forecast(users[uid]["name"], users[uid]["birth"]))

@bot.message_handler(commands=['subscribe'])
def subscribe(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("7 дней — 549", callback_data="sub7"),
        InlineKeyboardButton("30 дней — 1649", callback_data="sub30"),
        InlineKeyboardButton("Год — 5499", callback_data="sub365")
    )
    bot.reply_to(m, "Выбери подписку и открой поток удачи:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["sub7","sub30","sub365"])
def invoice(c):
    days = 7 if c.data=="sub7" else 30 if c.data=="sub30" else 365
    stars = 549 if days==7 else 1649 if days==30 else 5499
    bot.send_invoice(
        c.message.chat.id,
        title=f"АстраЛаб — {days} дней",
        description="Ежедневные ИИ-прогнозы + ритуалы",
        payload=f"sub_{days}d",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(f"{days} дней", stars)],
        start_parameter="astralab2026"
    )
    bot.answer_callback_query(c.id)

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def paid(m):
    uid = str(m.from_user.id)
    days = 7 if "7d" in m.successful_payment.invoice_payload else 30 if "30d" in m.successful_payment.invoice_payload else 365
    expires = datetime.now() + timedelta(days=days)
    if "first_payment_date" not in users[uid]:
        users[uid]["first_payment_date"] = datetime.now().isoformat()
    users[uid].update({"paid": True, "expires": expires.isoformat(), "days_paid": days})
    save_users(users)
    bot.reply_to(m, f"Оплата прошла! Подписка до {expires.strftime('%d.%m.%Y')}.\nПервые 5 дней — прогноз в 8:00 автоматически!")

# ====================== Авторассылка первые 5 дней ======================
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.start()

def daily_forecasts():
    now = datetime.now().date()
    for uid, d in users.items():
        if d.get("paid") and "first_payment_date" in d:
            days_passed = (now - datetime.fromisoformat(d["first_payment_date"]).date()).days
            if 0 <= days_passed <= 4:
                bot.send_message(int(uid), f"Доброе утро, {d['name']}!\n\n{generate_forecast(d['name'], d['birth'])}")

scheduler.add_job(daily_forecasts, 'cron', hour=8, minute=0, replace_existing=True)
atexit.register(lambda: scheduler.shutdown())

# ====================== Запуск (Web Service + polling) ======================
if __name__ == '__main__':
    # Запускаем Flask в фоне — Render видит порт
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    
    # Принудительно убиваем любой старый вебхук
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
    
    print("АстраЛаб 3000 запущен — порт открыт, 409 убит, всё работает!")
    bot.infinity_polling(none_stop=True, interval=0)
