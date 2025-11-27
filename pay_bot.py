import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
from datetime import datetime, timedelta
import requests  # Для API ИИ, если нужно

BOT_TOKEN = '8304180212:AAHvov9U2_Lt6XCilX8LHzyzVkPxkrTmQGU'  # Вставь токен от BotFather
USERS_FILE = 'users.json'

bot = telebot.TeleBot(BOT_TOKEN)

# Загрузка/сохранение пользователей (кто заплатил)
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

users = load_users()

# Промпт для ИИ (вставь тот, что я дал раньше)
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

# Функция генерации прогноза (используем бесплатный API, например, Grok или OpenAI mini — вставь свой ключ, если есть; иначе шаблон)
def generate_forecast(name, birth):
    today = datetime.now().strftime("%d %B %Y")
    prompt = AI_PROMPT.format(name=name, birth=birth, today=today)
    
    # Здесь вызов API (пример с requests к бесплатному эндпоинту; замени на свой Grok API если есть ключ)
    # Для теста используем простой шаблон, потом подключишь реальный ИИ
    # response = requests.post('https://api.groq.com/openai/v1/chat/completions', json={'model': 'llama3-8b-8192', 'messages': [{'role': 'system', 'content': prompt}]}, headers={'Authorization': 'Bearer ТВОЙ_GROQ_KEY'})
    # return response.json()['choices'][0]['message']['content']
    
    # Временный шаблон для теста (потом заменишь на реальный API)
    return f"{name}, я прям вздрогнула, когда посмотрела твою карту сегодня… Вижу, что в прошлом году ты пережила перемены в работе, которые сделали тебя сильнее. С завтрашнего дня идёт коридор удачи в деньгах — жди сумму от 50к. Ритуал: положи монетку в кошелёк с шепотом 'приходи'. Энергия на твоей стороне! Хочешь усилить — /усилить"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Получить бесплатный прогноз", callback_data="free_forecast"))
    bot.reply_to(message, "Привет! Я — АстраЛаб 3000, ИИ-астролог ✨\nВведи имя и дату рождения (ДД.ММ.ГГГГ):\nПример: Анна 14.03.1997", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "free_forecast")
def free_forecast(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Введи данные для прогноза!")

@bot.message_handler(func=lambda message: True)
def handle_input(message):
    user_id = message.from_user.id
    text = message.text.strip()
    if '\n' in text:
        lines = text.split('\n')
        name = lines[0].strip()
        birth = lines[1].strip() if len(lines) > 1 else ''
    else:
        name, birth = text.split(' ', 1) if ' ' in text else (text, '')
    
    if not birth:
        bot.reply_to(message, "Уточни дату: ДД.ММ.ГГГГ")
        return
    
    # Первый прогноз бесплатно
    forecast = generate_forecast(name, birth)
    users[user_id] = {'name': name, 'birth': birth, 'paid': False, 'expires': None}
    save_users(users)
    bot.reply_to(message, forecast)

@bot.message_handler(commands=['forecast'])
def forecast(message):
    user_id = message.from_user.id
    if user_id not in users:
        bot.reply_to(message, "Сначала /start!")
        return
    
    user = users[user_id]
    if user['paid'] and (not user['expires'] or datetime.now() < user['expires']):
        forecast_text = generate_forecast(user['name'], user['birth'])
        bot.reply_to(message, forecast_text)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Купить подписку", callback_data="subscribe"))
        bot.reply_to(message, "Доступ заблокирован. Купи подписку для полных прогнозов!", reply_markup=markup)

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("7 дней - 549 Stars", callback_data="sub7"),
        InlineKeyboardButton("30 дней - 1649 Stars", callback_data="sub30")
    )
    markup.add(InlineKeyboardButton("Год - 5499 Stars", callback_data="sub365"))
    bot.reply_to(message, "Выбери подписку:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('sub'))
def send_invoice(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    if call.data == 'sub7':
        prices = [LabeledPrice('7 дней', 549)]
        payload = 'week_sub'
        expires = datetime.now() + timedelta(days=7)
    elif call.data == 'sub30':
        prices = [LabeledPrice('30 дней', 1649)]
        payload = 'month_sub'
        expires = datetime.now() + timedelta(days=30)
    else:
        prices = [LabeledPrice('365 дней', 5499)]
        payload = 'year_sub'
        expires = datetime.now() + timedelta(days=365)
    
    bot.send_invoice(
        chat_id=chat_id,
        title='АстраЛаб Подписка',
        description='Ежедневные ИИ-прогнозы + ритуалы',
        payload=payload,
        provider_token='',  # Пусто для Stars!
        currency='XTR',  # Код для Stars
        prices=prices,
        start_parameter='stars-test'
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_query(pre_checkout_q):
    bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload == 'week_sub':
        expires = datetime.now() + timedelta(days=7)
    elif payload == 'month_sub':
        expires = datetime.now() + timedelta(days=30)
    else:
        expires = datetime.now() + timedelta(days=365)
    
    users[user_id]['paid'] = True
    users[user_id]['expires'] = expires
    save_users(users)
    
    bot.reply_to(message, f"Спасибо! Подписка активирована до {expires.strftime('%d.%m.%Y')}. Теперь /forecast работает без лимитов! ✨")

# Запуск
if __name__ == '__main__':
    print("Бот запущен!")
    bot.polling(none_stop=True)
