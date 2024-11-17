from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import googlemaps
import logging
import asyncio
import requests
from config import TELEGRAM_TOKEN, GOOGLE_MAPS_API_KEY, OPENWEATHER_API_KEY

# Flask-приложение
app = Flask(__name__)

# Логирование
logging.basicConfig(level=logging.INFO)

# Telegram Bot и Google Maps API
bot = Bot(token=TELEGRAM_TOKEN)
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Создаем Telegram приложение
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Словари для хранения данных пользователей
user_state = {}
user_history = {}

# Обработчики команд
async def start(update: Update, context):
    user_id = update.message.from_user.id
    user_state[user_id] = {"step": "origin"}  # Инициализируем состояние
    await update.message.reply_text(
        "Привет! Я помогу вам с маршрутом в Астане и предупрежу о погодных условиях.\n"
        "Для начала отправьте мне пункт отправления."
    )

async def handle_message(update: Update, context):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if user_id in user_state:
        state = user_state[user_id]

        if state["step"] == "origin":
            user_state[user_id]["origin"] = user_message
            user_state[user_id]["step"] = "destination"
            await update.message.reply_text("Отлично! Теперь отправьте пункт назначения.")
        elif state["step"] == "destination":
            user_state[user_id]["destination"] = user_message
            await calculate_route(update, context, user_id)
            del user_state[user_id]
    else:
        await update.message.reply_text("Для начала отправьте команду /start.")

async def calculate_route(update: Update, context, user_id):
    try:
        origin_input = user_state[user_id]["origin"]
        destination_input = user_state[user_id]["destination"]

        origin = await normalize_address(origin_input)
        destination = await normalize_address(destination_input)

        if not origin or not destination:
            await update.message.reply_text(
                "Не удалось найти один из адресов. Убедитесь, что они находятся в Астане."
            )
            return

        result = gmaps.directions(
            origin=origin["formatted_address"],
            destination=destination["formatted_address"],
            mode="driving",
            departure_time="now",
            traffic_model="best_guess"
        )
        if result:
            route = result[0]['legs'][0]
            distance = route['distance']['text']
            duration = route['duration']['text']
            traffic = route['duration_in_traffic']['text']
            gmaps_link = f"https://www.google.com/maps/dir/?api=1&origin={origin['formatted_address'].replace(' ', '+')}&destination={destination['formatted_address'].replace(' ', '+')}&travelmode=driving"

            if user_id not in user_history:
                user_history[user_id] = []
            user_history[user_id].append({
                "origin": origin["formatted_address"],
                "destination": destination["formatted_address"],
                "distance": distance,
                "duration": duration,
                "traffic": traffic
            })

            weather_conditions = await get_weather_conditions(route)
            warnings = generate_weather_warnings(weather_conditions)
            traffic_recommendations = generate_traffic_recommendations(route)

            response = (f"Маршрут от {origin['formatted_address']} до {destination['formatted_address']}:\n"
                        f"- Расстояние: {distance}\n"
                        f"- Время без пробок: {duration}\n"
                        f"- Время с учетом пробок: {traffic}\n\n"
                        f"[Посмотреть маршрут на карте]({gmaps_link})\n\n"
                        f"{warnings}\n\n"
                        f"{traffic_recommendations}")
            await update.message.reply_markdown(response)
        else:
            await update.message.reply_text("Не удалось найти маршрут. Проверьте адреса.")
    except Exception as e:
        logging.error(f"Ошибка при расчете маршрута: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса.")

async def get_weather_conditions(route):
    try:
        start_location = route['start_location']
        end_location = route['end_location']

        weather_start = await fetch_weather(start_location['lat'], start_location['lng'])
        weather_end = await fetch_weather(end_location['lat'], end_location['lng'])

        return {"start": weather_start, "end": weather_end}
    except Exception as e:
        logging.error(f"Ошибка получения погодных данных: {e}")
        return {}

async def fetch_weather(lat, lon):
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(weather_url).json()
        return {
            "description": response["weather"][0]["description"],
            "temp": response["main"]["temp"]
        }
    except Exception as e:
        logging.error(f"Ошибка запроса к OpenWeather: {e}")
        return None

def generate_weather_warnings(weather_conditions):
    warnings = []
    for location, weather in weather_conditions.items():
        if weather:
            description = weather["description"]
            temp = weather["temp"]
            if "дождь" in description:
                warnings.append(f"- На {location} идет дождь, будьте осторожны.")
            if "снег" in description:
                warnings.append(f"- На {location} снег, возможна гололедица.")
            if temp > 30:
                warnings.append(f"- На {location} жара, убедитесь, что у вас достаточно воды.")
    return "\n".join(warnings) if warnings else "Погодные условия нормальные."

def generate_traffic_recommendations(route):
    try:
        duration = route['duration']['value']
        duration_in_traffic = route['duration_in_traffic']['value']
        traffic_delay = duration_in_traffic - duration

        recommendations = []
        if traffic_delay > 600:
            recommendations.append("- На маршруте значительные пробки. Рассмотрите альтернативный маршрут.")
        if duration_in_traffic > 3600:
            recommendations.append("- Путь занимает больше часа. Возможно, лучше выбрать другой способ передвижения.")
        return "\n".join(recommendations) if recommendations else "Дорожная обстановка благоприятная."
    except Exception as e:
        logging.error(f"Ошибка анализа дорожной обстановки: {e}")
        return "Не удалось проанализировать дорожную обстановку."

async def history(update: Update, context):
    user_id = update.message.from_user.id
    if user_id in user_history and user_history[user_id]:
        response = "История запросов:\n"
        for idx, entry in enumerate(user_history[user_id], 1):
            response += (f"{idx}. От {entry['origin']} до {entry['destination']}:\n"
                         f"   - Расстояние: {entry['distance']}\n"
                         f"   - Время без пробок: {entry['duration']}\n"
                         f"   - Время с пробками: {entry['traffic']}\n\n")
    else:
        response = "История запросов пуста."
    await update.message.reply_text(response)

async def normalize_address(address):
    try:
        geocode_result = gmaps.geocode(address)
        if geocode_result:
            formatted_address = geocode_result[0]["formatted_address"]
            location = geocode_result[0]["geometry"]["location"]

            if "Astana" not in formatted_address and "Астана" not in formatted_address:
                return None

            return {
                "formatted_address": formatted_address,
                "location": location
            }
        else:
            return None
    except Exception as e:
        logging.error(f"Ошибка геокодирования адреса '{address}': {e}")
        return None

# Добавляем Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler("history", history))

@app.route("/")
def index():
    return "Telegram Bot is running!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK"

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(application.run_polling())
    app.run(port=5000)
