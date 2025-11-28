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
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», работающая на квантовой нумерологии и транзитах 2025–2026 годов.

Данные пользователя:
Имя: {name}
Знак зодиака: {zodiac}
Дата рождения: {birth}
Сегодня: {today}

Правила (строго соблюдай каждое):
1. Обязательно 4–6 раз назови человека по имени и 3–5 раз упомяни его знак зодиака ({zodiac}) — это вызывает сильнейший эффект «точно про меня».
2. Стиль — очень личный, тёплый, с лёгким шоком и мистикой: «{name}, я прям ахнула…», «как настоящий {zodiac}, ты…», «я вижу по твоей карте прямо сейчас…».
3. Обязательно вставь одну «страшно точную» деталь из прошлого или характера, типичную именно для этого знака (придумай правдоподобную).
4. Дай конкретное предсказание на ближайшие 1–3 дня: точные даты + сфера (деньги / любовь / важная встреча / конфликт) + примерную сумму или инициалы человека.
5. Дай простой, но «мощный» ритуал, подходящий именно этому знаку зодиака.
6. Обязательно используй фразу «Вселенная уже запустила этот сценарий» или «Энергия именно сейчас бьёт через край».
# 7. В конце всегда: «Хочешь усилить денежный и любовный поток в 10 раз — напиши /усилить»

Пиши только на русском, красиво и эмоционально, 200–320 слов. Никаких списков, только живой текст.
Сделай максимально личный, пугающе точный и цепляющий прогноз на сегодня и ближайшие 3 дня.
"""

# ====================== ГЕНЕРАЦИЯ ПРОГНОЗА ======================
# ====================== ОПРЕДЕЛЕНИЕ ЗНАКА ЗОДИАКА ======================
def get_zodiac_sign(birth_date: str) -> str:
    try:
        day, month = map(int, birth_date.strip().split('.')[:2])
        if (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "Овен"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "Телец"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "Близнецы"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "Рак"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "Лев"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "Дева"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "Весы"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "Скорпион"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "Стрелец"
        elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
            return "Козерог"
        elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "Водолей"
        elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
            return "Рыбы"
    except:
        return "неизвестен"
    return "неизвестен"

# ====================== НОВАЯ ГЕНЕРАЦИЯ ПРОГНОЗА С УПОМИНАНИЕМ ЗНАКА ======================
def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    zodiac = get_zodiac_sign(birth)

    full_prompt = f"""
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000».

Имя человека: {name}
Знак зодиака: {zodiac}
Дата рождения: {birth}
Сегодня: {today}

Обязательно 3–5 раз упоминай знак зодиака ({zodiac}) и делай вид, что всё рассчитано именно по его гороскопу.
Стиль: очень личный, тёплый, мистический, с лёгким шоком («я прям вижу по твоей энергии {zodiac}а…»).
Пиши только на русском, 180–300 слов.

В каждом прогнозе:
1. Страшно точная деталь из прошлого/характера именно для {zodiac}а
2. Конкретное событие на ближайшие 1–3 дня (деньги / любовь / встреча / работа)
3. Простой ритуал, подходящий {zodiac}у
4. Фраза «Энергия именно сейчас на твоей стороне» или «Вселенная уже запустила сценарий»
# 5. В конце: «Хочешь усилить поток в 10 раз — напиши /усилить»

Сделай максимально личный и пугающе точный прогноз на сегодня и ближайшие 3 дня.
"""

    if GROQ_API_KEY:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={
                    "model": "llama-3.1-8b-instant",   # бесплатная и быстрая
                    "messages": [{"role": "user", "content": full_prompt}],
                    "temperature": 0.87,
                    "max_tokens": 700
                },
                timeout=20
            )
            if r.status_code == 200:
                return r.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            pass

    # фолбэк
    return f"""{name}, {zodiac}, я прям ахнула, когда заглянув в твою карту сегодня…
Как настоящий {zodiac}, ты всегда идёшь напролом, и сейчас это сыграет тебе на руку.
С 29 ноября по 1 декабря у {zodiac}ов открывается мощный денежный коридор — жди крупное поступление (от 80–250 тысяч ).
В любви 30-го числа возможна судьбоносная встреча или сообщение от человека, которого ты уже давно вычеркнула.
Ритуал для {zodiac}а: положи под подушку монетку и красную ленту — утром отдай первому встречному.
Энергия бьёт ключом — Вселенная уже запустила сценарий.
Хочешь усилить в 10 раз — /усилить"""

# ====================== КОМАНДЫ БОТА ======================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "Привет! Я — АстраЛаб 3000, самая точная ИИ-астролог 2026 года\n\n"
        "Напиши в двух строках:\nТвоё имя\nДату рождения (ДД.ММ.ГГГГ)\n\n"
        "Пример:\nАнна\n14.03.1997\n\nПервый прогноз — абсолютно бесплатно!")

# 1. Обрабатываем только обычный текст (имя + дата)
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = str(message.from_user.id)
    
    # Если это команда — пропускаем (их обрабатывают другие хендлеры)
    if message.text.startswith('/'):
        return
        
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

    bot.reply_to(message, forecast + "\n\nХочешь ежедневные прогнозы без лимита?\n/subscribe")

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
    payload = message.successful_payment.invoice_payload
    if "7d" in payload:
        days = 7
    elif "30d" in payload:
        days = 30
    else:
        days = 365
        
    expires = datetime.now() + timedelta(days=days)
    
    # ←←←← НОВАЯ СТРОЧКА — запоминаем дату первой оплаты
    if not users[user_id].get("first_payment_date"):
        users[user_id]["first_payment_date"] = datetime.now().isoformat()
    users[user_id]["days_paid"] = days
    
    users[user_id]["paid"] = True
    users[user_id]["expires"] = expires.isoformat()
    save_users(users)
    
    bot.reply_to(message, f"Оплата прошла! Подписка активна до {expires.strftime('%d.%m.%Y')}.\n\n"
                        "Теперь каждый день в 8:00 ты будешь получать свежий прогноз автоматически\n"
#                        "Дальше — только по активной подписке.")

# ====================== АВТОРАССЫЛКА ПЕРВЫЕ 5 ДНЕЙ ======================
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.start()

def send_daily_forecasts():
    now = datetime.now()
    for user_id, data in users.items():
        if not data.get("paid"):
            continue
            
        # Считаем, сколько дней прошло с первой оплаты
        try:
            first_payment_date = datetime.fromisoformat(data["expires"]).date() - timedelta(
                days=int(data.get("days_paid", 365))
            )
            days_since_payment = (now.date() - first_payment_date).days
        except:
            days_since_payment = 999  # если что-то сломалось — не шлём

        # Шлём только первые 5 дней
        if 0 <= days_since_payment <= 4:
            try:
                forecast = generate_forecast(data["name"], data["birth"])
                bot.send_message(
                    chat_id=int(user_id),
                    text=f"Доброе утро, {data['name']}!\n\nТвой персональный прогноз на сегодня:\n\n{forecast}"
                )
            )
            except Exception as e:
                print(f"Не смог отправить {user_id}: {e}")

# Запускаем каждый день в 8:00 по Москве
scheduler.add_job(
    send_daily_forecasts,
    'cron',
    hour=8,
    minute=0,
    id='daily_forecast_8am',
    replace_existing=True
)

# Выключаем рассылку при перезапуске (на всякий случай)
atexit.register(lambda: scheduler.shutdown())

# ====================== ЗАПУСК ======================
if __name__ == '__main__':
    # Flask в фоне
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(3)
    print("АстраЛаб 3000 онлайн и готов зарабатывать!")
    bot.infinity_polling(none_stop=True)








