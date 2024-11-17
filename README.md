# Telegram Bot with Flask

Этот проект представляет собой Telegram-бота, который работает на сервере Flask и принимает сообщения от пользователей. Для передачи данных используется вебхук, настроенный через ngrok.

## Требования

1. Python 3.8+
2. Flask
3. python-telegram-bot
4. ngrok

## Установка

1. Клонируйте этот репозиторий:
   ```bash
   git clone https://github.com/ikanit1/TelegramBot.git
   cd TelegramBot
Установите зависимости:

bash
Копировать код
pip install -r requirements.txt
Получите Telegram Bot Token от @BotFather.

Создайте файл config.py в корне проекта и добавьте токен:

python
Копировать код
TELEGRAM_TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"
Запуск сервера
Создайте файл app.py со следующим содержимым:

python
Копировать код
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging

# Инициализация Flask
app = Flask(__name__)

# Инициализация Telegram Bot
TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Замените на ваш Telegram токен
bot = Bot(token=TELEGRAM_TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO)

# Настроим Application для обработки запросов от Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Определим команды и обработчики для сообщений
async def start(update: Update, context):
    await update.message.reply_text("Привет! Я ваш Telegram-бот!")

async def echo(update: Update, context):
    await update.message.reply_text(f"Вы сказали: {update.message.text}")

# Добавим обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# Flask маршруты
@app.route('/')
def index():
    return "Flask сервер работает!"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK"

# Запуск Flask сервера
if __name__ == "__main__":
    app.run(port=5000)
Замените 'YOUR_TELEGRAM_BOT_TOKEN' на ваш токен, который вы получили при регистрации бота через @BotFather.

Запустите Flask сервер:

bash
Копировать код
python app.py
В другом терминале запустите ngrok для проброса порта:

bash
Копировать код
ngrok http 5000
Это создаст публичный HTTPS URL, например:

arduino
Копировать код
https://abcd-1234-5678.ngrok-free.app
Настройте вебхук для Telegram, чтобы сообщения от пользователей направлялись на ваш сервер:

bash
Копировать код
curl -X POST "https://api.telegram.org/botВАШ_ТЕЛЕГРАМ_ТОКЕН/setWebhook?url=https://abcd-1234-5678.ngrok-free.app/ВАШ_ТЕЛЕГРАМ_ТОКЕН"
Замените:

ВАШ_ТЕЛЕГРАМ_ТОКЕН на ваш токен.
https://abcd-1234-5678.ngrok-free.app на URL, который вам выдал ngrok.
Теперь ваш сервер готов к работе, и бот будет принимать сообщения через вебхук.

Примечания
Убедитесь, что ngrok работает и создает доступный HTTPS URL для вашего локального сервера.
Сервер будет работать до тех пор, пока не завершите его выполнение.
go
Копировать код

Теперь вы можете вставить этот текст в `README.md` в вашем репозитории, чтобы описать процесс установки и настройки проекта.
