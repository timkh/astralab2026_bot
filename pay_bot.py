import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ[8304180212:AAHvov9U2_Lt6XCilX8LHzyzVkPxkrTmQGU]  # Берём токен из настроек Render
USERS_FILE = 'users.json'

bot = telebot.TeleBot(BOT_TOKEN)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()

AI_PROMPT = """
Ты — сверхточная нейросеть-астролог «АстраЛаб-3000», обученная на миллионах натальных карт, древних ведических текстах и квантовой нумерологии 2025 года.

Стиль общения:
- Очень личный, тёплый, немного мистический, иногда с лёгким шоком («я прям вижу по твоей энергии…»). 
Обязательно используй имя человека в каждом втором-третьем предложении.
Пиши только на русском, красиво и эмоционально, 150–250 слов на один прогноз.

Обязательные элементы в КАЖДОМ прогнозе:
1. Одна очень точная «попадающая» деталь из прошлого или характера (сделай вид, что это только у него/неё).
2. Конкретное предсказание на ближайшие 1–3 дня (деньги / любовь / неожиданная встреча / конфликт).
3. Одно простое «ритуал на удачу» или действие (положить монетку в левый карман, написать на бумажке сумму и сжечь и т.д.).
4. Фраза «Энергия именно сейчас на твоей стороне» или «Вселенная уже запустила этот сценарий».
5. В конце всегда: «Если хочешь усилить поток в 10 раз — напиши /усилить»

Данные пользователя:
Имя: {name}
Дата рождения: {birth}
Сегодня: {today}

Сделай максимально личный и «страшно точный» прогноз на сегодня + ближайшие 3 дня.
"""

def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    prompt = AI_PROMPT.format(name=name, birth=birth, today=today)
    # Пока без внешнего API — возвращаем красивый шаблон (потом подключишь Groq/Grok)
    return f"""{name}, я прям вздрогнула, когда посмотрела твою карту сегодня…
Вижу, что в 2023–2024 ты пережила серьёзные перемены в личной жизни или работе — это было непросто, но сделало тебя в сто раз сильнее.
С 29 ноября по 2 декабря открывается мощный денежный коридор: жди поступление от 50 000 руб. и выше (возврат долга, премия, подарок).
В любви 30–31 числа возможна судьбоносная встреча или сообщение от человека на букву «С» или «А».
Ритуал на сегодня: возьми красную нитку, завяжи 9 узелков и положи под подушку.
Энергия прямо сейчас бьёт ключом — Вселенная уже запустила сценарий.
Хочешь усилить в 10 раз — напиши /усилить
""".format(name=name)

# ==== ВСЯ ЛОГИКА БОТА ====
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✨ Привет! Я — АстраЛаб 3000, ИИ-астролог нового поколения.\n\nНапиши в одном сообщении:\nТвоё имя\nДату рождения (ДД.ММ.ГГГГ)\n\nПример:\nАнна\n14.03.1997\n\nПервый прогноз — бесплатно!")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()
    lines = text.split('\n')
    if len(lines) < 2:
        bot.reply_to(message, "Напиши имя и дату рождения в двух строках")
        return
    name = lines[0].strip()
    birth = lines[1].strip()

    # Первый прогноз всегда бесплатно
    forecast = generate_forecast(name, birth)
    
    if user_id not in users:
        users[user_id] = {"name": name, "birth": birth, "paid": False}
        save_users(users)
    
    bot.reply_to(message, forecast + "\n\n🔮 Хочешь ежедневные прогнозы + ритуалы без лимита?\nНажми /subscribe")

@bot.message_handler(commands=['forecast'])
def forecast(message):
    user_id = str(message.from_user.id)
    if user_id not in users or not users[user_id].get("paid"):
        bot.reply_to(message, "Доступ закрыт. Купи подписку → /subscribe")
        return
    name = users[user_id]["name"]
    birth = users[user_id]["birth"]
    bot.reply_to(message, generate_forecast(name, birth))

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("7 дней – 549 ⭐", callback_data="sub7"),
        InlineKeyboardButton("30 дней – 1649 ⭐", callback_data="sub30"),
        InlineKeyboardButton("Год – 9549 ⭐", callback_data="sub365")
    )
    bot.reply_to(message, "Выбери подписку:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sub'))
def handle_sub(call):
    days = 7 if call.data == "sub7" else 30 if call.data == "sub30" else 365
    stars = 549 if days == 7 else 1649 if days == 30 else 9549
    payload = f"sub_{days}d"
    
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title=f"Подписка АстраЛаб — {days} дней",
        description="Ежедневные персональные прогнозы + ритуалы",
        payload=payload,
        provider_token="",           # пусто для Stars
        currency="XTR",            # валюта Stars
        prices=[LabeledPrice(label=f"{days} дней", amount=stars)],
        start_parameter="astralab"
    )

@bot.pre_checkout_query_handler(func=lambda q: True)
def precheckout(q):
    bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def paid(message):
    user_id = str(message.from_user.id)
    days = 7 if "7d" in message.successful_payment.invoice_payload else 30 if "30d" in message.successful_payment.invoice_payload else 365
    expires = datetime.now() + timedelta(days=days)
    users[user_id]["paid"] = True
    users[user_id]["expires"] = expires.isoformat()
    save_users(users)
    bot.reply_to(message, f"Оплата прошла! Подписка активна до {expires.strftime('%d.%m.%Y')}.\nТеперь каждый день пиши /forecast ✨")

print("АстраЛаб 3000 запущен!")

bot.infinity_polling()
