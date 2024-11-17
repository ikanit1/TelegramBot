
# Telegram Bot with Flask

Этот проект представляет собой Telegram-бота, который работает на сервере Flask и принимает сообщения от пользователей. Для передачи данных используется вебхук, настроенный через ngrok.

## Требования

- Python 3.8+
- Flask
- python-telegram-bot
- ngrok

## Установка

1. Клонируйте этот репозиторий:

   ```bash
   git clone https://github.com/ikanit1/TelegramBot.git
   cd TelegramBot
   ```

2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Получите Telegram Bot Token от @BotFather.

4. Создайте файл `config.py` в корне проекта и добавьте токен:

   ```python
   TELEGRAM_TOKEN = "ВАШ_ТЕЛЕГРАМ_ТОКЕН"
   ```

## Запуск сервера

1. Создайте файл `app.py` со следующим содержимым:

   ```python
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
   ```

   Замените `'YOUR_TELEGRAM_BOT_TOKEN'` на ваш токен, который вы получили при регистрации бота через @BotFather.

2. Запустите Flask сервер:

   ```bash
   python app.py
   ```

3. В другом терминале запустите ngrok для проброса порта:

   ```bash
   ngrok http 5000
   ```

   Это создаст публичный HTTPS URL, например:

   ```
   https://abcd-1234-5678.ngrok-free.app
   ```

4. Настройте вебхук для Telegram, чтобы сообщения от пользователей направлялись на ваш сервер:

   ```bash
   curl -X POST "https://api.telegram.org/botВАШ_ТЕЛЕГРАМ_ТОКЕН/setWebhook?url=https://abcd-1234-5678.ngrok-free.app/ВАШ_ТЕЛЕГРАМ_ТОКЕН"
   ```

   Замените:
   - `ВАШ_ТЕЛЕГРАМ_ТОКЕН` на ваш токен.
   - `https://abcd-1234-5678.ngrok-free.app` на URL, который вам выдал ngrok.

## Примечания

- Убедитесь, что `ngrok` работает и создает доступный HTTPS URL для вашего локального сервера.
- Сервер будет работать до тех пор, пока вы не завершите его выполнение.

