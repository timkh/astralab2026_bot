import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, Update
import json, os, threading, time, requests
from datetime import datetime, timedelta
from flask import Flask, request, abort
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
@app.route('/health')
def health(): return 'OK', 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

BOT_TOKEN = os.environ['BOT_TOKEN']
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
bot = telebot.TeleBot(BOT_TOKEN)
USERS_FILE = 'users.json'

def load_users():
    return json.load(open(USERS_FILE, encoding='utf-8')) if os.path.exists(USERS_FILE) else {}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

users = load_users()

def get_zodiac_sign(birth):
    try:
        d, m = map(int, birth.split('.')[:2])
        return ["Козерог","Водолей","Рыбы","Овен","Телец","Близнецы","Рак","Лев","Дева","Весы","Скорпион","Стрелец"][
            (m-1)*2 + (d > (19,18,20,19,20,20,22,22,22,22,21,21)[m-1])]
    except: return "неизвестен"

AI_PROMPT = """Ты — сверхточная нейросеть-астролог «АстраЛаб-3000»... (тот же убойный промпт, что я давал выше)"""

def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    zodiac = get_zodiac_sign(birth)
    prompt = AI_PROMPT.format(name=name, zodiac=zodiac, birth=birth, today=today)

    if GROQ_API_KEY:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}],
                      "temperature":0.87,"max_tokens":700}, timeout=18)
            if r.status_code == 200: return r.json()['choices'][0]['message']['content'].strip()
        except: pass
    return f"{name}, {zodiac}, я ахнула… Вселенная уже запустила денежный поток 29–30 ноября (80–350к). Ритуал: монета + красная нить. Хочешь усилить в 10 раз — /усилить"

# КОМАНДЫ
@bot.message_handler(commands=['start'])
def start(m): bot.reply_to(m, "Привет! Я — АстраЛаб 3000\n\nНапиши:\nИмя\nДД.ММ.ГГГГ")

@bot.message_handler(content_types=['text'])
def text(m):
    if m.text.startswith('/'): return
    lines = [x.strip() for x in m.text.split('\n') if x.strip()]
    if len(lines) < 2: return bot.reply_to(m, "Имя и дата в двух строках")
    name, birth = lines[0].capitalize(), lines[1]
    uid = str(m.from_user.id)
    users.setdefault(uid, {"name":name, "birth":birth, "paid":False})
    save_users(users)
    bot.reply_to(m, generate_forecast(name, birth) + "\n\nЕжедневно — /subscribe")

@bot.message_handler(commands=['forecast'])
def forecast(m):
    if not users.get(str(m.from_user.id), {}).get("paid"):
        return bot.reply_to(m, "Нужна подписка → /subscribe")
    bot.reply_to(m, generate_forecast(users[str(m.from_user.id)]["name"], users[str(m.from_user.id)]["birth"]))

@bot.message_handler(commands=['subscribe'])
def subscribe(m):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("7 дней — 549", callback_data="sub7"),
           InlineKeyboardButton("30 дней — 1649", callback_data="sub30"),
           InlineKeyboardButton("Год — 5499", callback_data="sub365"))
    bot.reply_to(m, "Выбери подписку и открой поток удачи:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ["sub7","sub30","sub365"])
def pay(c):
    days = 7 if c.data=="sub7" else 30 if c.data=="sub30" else 365
    stars = 549 if days==7 else 1649 if days==30 else 5499
    bot.send_invoice(c.message.chat.id, title=f"АстраЛаб — {days} дней",
        description="Ежедневные ИИ-прогнозы + ритуалы", payload=f"sub_{days}d",
        provider_token="", currency="XTR", prices=[LabeledPrice(f"{days} дней", stars)], start_parameter="astralab2026")
    bot.answer_callback_query(c.id)

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre(q): bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def paid(m):
    uid = str(m.from_user.id)
    days = 7 if "7d" in m.successful_payment.invoice_payload else 30 if "30d" in m.successful_payment.invoice_payload else 365
    expires = datetime.now() + timedelta(days=days)
    if "first_payment_date" not in users[uid]:
        users[uid]["first_payment_date"] = datetime.now().isoformat()
    users[uid].update({"paid":True, "expires":expires.isoformat(), "days_paid":days})
    save_users(users)
    bot.reply_to(m, f"Оплата прошла! Подписка до {expires.strftime('%d.%m.%Y')}.\nПервые 5 дней — прогноз в 8:00 автоматически!")

# РАССЫЛКА
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.start()
def daily():
    now = datetime.now().date()
    for uid, d in users.items():
        if d.get("paid") and "first_payment_date" in d:
            if 0 <= (now - datetime.fromisoformat(d["first_payment_date"]).date()).days <= 4:
                bot.send_message(int(uid), f"Доброе утро, {d['name']}!\n\n{generate_forecast(d['name'], d['birth'])}")
scheduler.add_job(daily, 'cron', hour=8, minute=0, replace_existing=True)
atexit.register(lambda: scheduler.shutdown())

# ВЕБХУКИ
WEBHOOK_HOST = os.environ['RENDER_EXTERNAL_HOSTNAME']
WEBHOOK_URL = f"https://{WEBHOOK_HOST}.onrender.com/webhook"

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}&drop_pending_updates=true"
    print("Webhook:", requests.get(url, timeout=15).json())

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return 'OK', 200
    return abort(403)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(5)
    set_webhook()
    print(f"АстраЛаб 3000 ЖИВ на {WEBHOOK_URL}")
    while True: time.sleep(3600)
