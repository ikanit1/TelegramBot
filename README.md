
# Telegram Bot with Flask

Этот проект представляет собой Telegram-бота, который работает на сервере Flask и принимает сообщения от пользователей. Для передачи данных используется вебхук, настроенный через ngrok.

## Требования

- Python 3.8+
- Flask
- python-telegram-bot
- ngrok

## Запуск сервера

1. Запустите Flask сервер:

   ```bash
   python app.py
   ```

2. В другом терминале запустите ngrok для проброса порта:

   ```bash
   ngrok http 5000
   ```

   Это создаст публичный HTTPS URL, например:

   ```
   https://abcd-1234-5678.ngrok-free.app
   ```

3. Настройте вебхук для Telegram, чтобы сообщения от пользователей направлялись на ваш сервер:

   ```bash
   curl -X POST "https://api.telegram.org/botВАШ_ТЕЛЕГРАМ_ТОКЕН/setWebhook?url=https://abcd-1234-5678.ngrok-free.app/ВАШ_ТЕЛЕГРАМ_ТОКЕН"
   ```

   Замените:
   - `ВАШ_ТЕЛЕГРАМ_ТОКЕН` на ваш токен.
   - `https://abcd-1234-5678.ngrok-free.app` на URL, который вам выдал ngrok.

## Примечания

- Убедитесь, что `ngrok` работает и создает доступный HTTPS URL для вашего локального сервера.
- Сервер будет работать до тех пор, пока вы не завершите его выполнение.

