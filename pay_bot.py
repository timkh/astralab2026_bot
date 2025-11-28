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
from pytz import timezone
import atexit
import locale

# ====================== Локаль для русского языка ======================
try:
    locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
except:
    pass

# ====================== Flask ======================
app = Flask(__name__)

@app.route('/health')
def health():
    return "АстраЛаб 3000 — OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ====================== Конфиг ======================
BOT_TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
PROVIDER_TOKEN = os.environ.get("PROVIDER_TOKEN", "")  # Stars provider token

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

USERS_FILE = "users.json"

# ====================== База пользователей ======================
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_users()

# ====================== Определение знака ======================
def get_zodiac_sign(birth_date: str) -> str:
    try:
        d, m = map(int, birth_date.strip().split('.')[:2])
        if (m == 3 and d >= 21) or (m == 4 and d <= 19): return "Овен"
        if (m == 4 and d >= 20) or (m == 5 and d <= 20): return "Телец"
        if (m == 5 and d >= 21) or (m == 6 and d <= 20): return "Близнецы"
        if (m == 6 and d >= 21) or (m == 7 and d <= 22): return "Рак"
        if (m == 7 and d >= 23) or (m == 8 and d <= 22): return "Лев"
        if (m == 8 and d >= 23) or (m == 9 and d <= 22): return "Дева"
        if (m == 9 and d >= 23) or (m == 10 and d <= 22): return "Весы"
        if (m == 10 and d >= 23) or (m == 11 and d <= 21): return "Скорпион"
        if (m == 11 and d >= 22) or (m == 12 and d <= 21): return "Стрелец"
        if (m == 12 and d >= 22) or (m == 1 and d <= 19): return "Козерог"
        if (m == 1 and d >= 20) or (m == 2 and d <= 18): return "Водолей"
        if (m == 2 and d >= 19) or (m == 3 and d <= 20): return "Рыбы"
    except:
        pass
    return "неизвестен"

# ====================== Промпт ======================
AI_PROMPT = """
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», работающая на квантовой нумерологии и транзитах 2025–2026 годов.

Имя: {name}
Знак зодиака: {zodiac}
Дата рождения: {birth}
Сегодня: {today}

Строго соблюдай:
- 4–6 обращений по имени
- 3–5 упоминаний знака
- Одна деталь из прошлого
- Прогноз с датами на 1–3 дня
- Ритуал под знак
- Фраза: «Вселенная уже запустила этот сценарий»
- 200–320 слов, без списков
"""

# ====================== Генерация прогноза ======================
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
            print(f"Groq error: {e}")

    return f"{name}, как настоящий {zodiac}, ты входишь в мощный поток энергии..."


# ====================== Команды ======================
@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Привет! Отправь две строки:\nИмя\nДД.ММ.ГГГГ")

@bot.message_handler(commands=['forecast'])
def cmd_forecast(m):
    uid = str(m.from_user.id)
    u = users.get(uid)

    if not u:
        return bot.reply_to(m, "Сначала отправь имя и дату рождения.")

    if not u.get("paid"):
        return bot.reply_to(m, "Подписка нужна → /subscribe")

    bot.reply_to(m, generate_forecast(u["name"], u["birth"]))

@bot.message_handler(commands=['subscribe'])
def subscribe(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("7 дней — 549", callback_data="sub7"),
        InlineKeyboardButton("30 дней — 1649", callback_data="sub30"),
        InlineKeyboardButton("Год — 5499", callback_data="sub365")
    )
    bot.reply_to(m, "Выбери подписку:", reply_markup=kb)

# ====================== Обработка имени и даты ======================
@bot.message_handler(content_types=['text'])
def text_input(m):
    if m.text.startswith('/'): 
        return

    lines = [x.strip() for x in m.text.split('\n') if x.strip()]
    if len(lines) < 2:
        return bot.reply_to(m, "Пиши имя и дату рождения в двух строках.")

    name = lines[0].capitalize()
    birth = lines[1]
    uid = str(m.from_user.id)

    users.setdefault(uid, {})
    users[uid].update({"name": name, "birth": birth})
    save_users(users)

    bot.reply_to(m, generate_forecast(name, birth) + "\n\nЧтобы получать ежедневно → /subscribe")

# ====================== Инвойсы ======================
@bot.callback_query_handler(func=lambda c: c.data in ["sub7","sub30","sub365"])
def invoice(c):
    if c.data == "sub7":
        days, price = 7, 549
    elif c.data == "sub30":
        days, price = 30, 1649
    else:
        days, price = 365, 5499

    bot.send_invoice(
        chat_id=c.message.chat.id,
        title=f"АстраЛаб — {days} дней",
        description="Ежедневные ИИ-прогнозы",
        payload=f"sub_{days}d",
        provider_token=PROVIDER_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(f"{days} дней", price * 1000)],  # Stars ×1000
        start_parameter="astralab2026"
    )
    bot.answer_callback_query(c.id)

# ====================== Пре-чекаут ======================
@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

# ====================== Успешная оплата ======================
@bot.message_handler(content_types=['successful_payment'])
def success(m):
    uid = str(m.from_user.id)
    payload = m.successful_payment.invoice_payload
    days = int(payload.split('_')[1].replace('d', ''))

    expires = datetime.now() + timedelta(days=days)

    users.setdefault(uid, {})
    users[uid]["paid"] = True
    users[uid]["expires"] = expires.isoformat()
    users[uid]["first_payment_date"] = datetime.now().isoformat()
    save_users(users)

    bot.reply_to(m, f"Оплата прошла! Подписка активна до {expires.strftime('%d.%m.%Y')}.")

# ====================== Авторассылка ======================
scheduler = BackgroundScheduler(timezone=timezone("Europe/Moscow"))
scheduler.start()

def daily_job():
    now = datetime.now().date()

    for uid, u in users.items():
        if not u.get("paid"):
            continue
        if "first_payment_date" not in u:
            continue
        if "expires" not in u:
            continue

        if datetime.fromisoformat(u["expires"]).date() < now:
            continue

        days_passed = (now - datetime.fromisoformat(u["first_payment_date"]).date()).days
        if 0 <= days_passed <= 4:
            try:
                bot.send_message(
                    int(uid),
                    f"Доброе утро, {u['name']}!\n\n" +
                    generate_forecast(u["name"], u["birth"])
                )
            except:
                pass

scheduler.add_job(daily_job, "cron", hour=8, minute=0)
atexit.register(lambda: scheduler.shutdown())

# ====================== Запуск ======================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    print("АстраЛаб 3000 запущен")
    bot.infinity_polling(none_stop=True)
