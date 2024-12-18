from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import googlemaps
import logging
import asyncio
import aiohttp
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

# Асинхронные запросы с использованием aiohttp
async def fetch_weather(lat, lon):
    try:
        async with aiohttp.ClientSession() as session:
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            async with session.get(weather_url) as response:
                response_data = await response.json()
                return {
                    "description": response_data["weather"][0]["description"],
                    "temp": response_data["main"]["temp"]
                }
    except Exception as e:
        logging.error(f"Ошибка запроса к OpenWeather: {e}")
        return None
    
def create_navigation_buttons():
    # Определяем кнопки
    button_start = InlineKeyboardButton("Начать новый маршрут", callback_data="start_new_route")
    button_history = InlineKeyboardButton("История запросов", callback_data="show_history")
    button_cancel = InlineKeyboardButton("Отменить запрос", callback_data="cancel_request")
    
    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup([[button_start, button_history], [button_cancel]])
    
    return keyboard

# Сначала определяем функцию обработчика
async def handle_button_click(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id

    # Обработка нажатия кнопки "Начать новый маршрут"
    if query.data == "start_new_route":
        user_state[user_id] = {"step": "origin"}  # Сбрасываем состояние
        await query.answer()  # Ответ на запрос
        await query.edit_message_text("Отправьте мне пункт отправления для нового маршрута.")

    # Обработка нажатия кнопки "История запросов"
    elif query.data == "show_history":
        await history(update, context)  # Показать историю запросов

    # Обработка нажатия кнопки "Отменить запрос"
    elif query.data == "cancel_request":
        if user_id in user_state:
            del user_state[user_id]  # Отменяем запрос
            await query.answer()  # Ответ на запрос
            await query.edit_message_text("Ваш запрос был отменен.")

# Теперь добавляем обработчик в приложение
application.add_handler(CallbackQueryHandler(handle_button_click))  # Обработчик для нажатий на кнопки



async def start(update: Update, context):
    user_id = update.message.from_user.id
    user_state[user_id] = {"step": "origin"}  # Инициализируем состояние
    await update.message.reply_text(
        "Привет! Я помогу вам с маршрутом в Астане и предупрежу о погодных условиях.\n"
        "Для начала отправьте мне пункт отправления.",
        reply_markup=create_navigation_buttons()  # Отправляем клавиатуру с кнопками
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
        # Получение начальной и конечной точки
        origin_input = user_state[user_id]["origin"]
        destination_input = user_state[user_id]["destination"]

        origin = await normalize_address(origin_input)
        destination = await normalize_address(destination_input)

        if not origin or not destination:
            await update.message.reply_text(
                "Не удалось найти один из адресов. Убедитесь, что они находятся в Астане."
            )
            return

        # Запрос маршрутов для разных видов транспорта
        modes = ["driving", "walking", "transit"]
        routes = {}

        for mode in modes:
            directions_params = {
                "origin": origin["formatted_address"],
                "destination": destination["formatted_address"],
                "mode": mode,
                "departure_time": "now",
                "traffic_model": "best_guess",
            }

            result = gmaps.directions(**directions_params)
            if result:
                routes[mode] = result[0]['legs'][0]

        if not routes:
            await update.message.reply_text("Не удалось найти маршрут. Проверьте адреса.")
            return

        # Извлечение данных для каждого вида транспорта
        driving = routes.get("driving")
        walking = routes.get("walking")
        transit = routes.get("transit")

        # Получение погодных условий для начальной и конечной точки
        weather_conditions = await get_weather_conditions(driving or walking or transit)
        weather_warnings = generate_weather_warnings(weather_conditions)

        # Анализ дорожной обстановки
        traffic_recommendations = generate_traffic_recommendations(driving) if driving else "Дорожная обстановка не анализировалась."

        # Определение самого быстрого маршрута
        travel_times = {}
        if driving:
            travel_times["driving"] = driving['duration']['value']
        if walking:
            travel_times["walking"] = walking['duration']['value']
        if transit:
            travel_times["transit"] = transit['duration']['value']

        fastest_mode = min(travel_times, key=travel_times.get)
        fastest_time = travel_times[fastest_mode]

        # Сохранение в историю
        if user_id not in user_history:
            user_history[user_id] = []
        user_history[user_id].append({
            "origin": origin["formatted_address"],
            "destination": destination["formatted_address"],
            "distance": driving["distance"]["text"] if driving else "N/A",
            "duration": driving["duration"]["text"] if driving else "N/A",
            "traffic": driving.get("duration_in_traffic", {}).get("text", "N/A") if driving else "N/A",
            "weather": weather_conditions,
        })

        # Формирование ответа
        response = f"Оптимальные маршруты от {origin['formatted_address']} до {destination['formatted_address']}:\n\n"

        if driving:
            traffic = driving.get('duration_in_traffic', {}).get('text', 'неизвестно')
            driving_link = f"https://www.google.com/maps/dir/?api=1&origin={origin['formatted_address'].replace(' ', '+')}&destination={destination['formatted_address'].replace(' ', '+')}&travelmode=driving"
            response += (f"🚗 На автомобиле:\n"
                         f"- Расстояние: {driving['distance']['text']}\n"
                         f"- Время: {driving['duration']['text']}\n"
                         f"- С учетом пробок: {traffic}\n"
                         f"[Посмотреть маршрут в Google Maps]({driving_link})\n\n")

        if walking:
            walking_link = f"https://www.google.com/maps/dir/?api=1&origin={origin['formatted_address'].replace(' ', '+')}&destination={destination['formatted_address'].replace(' ', '+')}&travelmode=walking"
            response += (f"🚶 Пешком:\n"
                         f"- Расстояние: {walking['distance']['text']}\n"
                         f"- Время: {walking['duration']['text']}\n"
                         f"[Посмотреть маршрут в Google Maps]({walking_link})\n\n")

        if transit:
            transit_details = transit['steps'][0].get('transit_details', {})
            transit_link = f"https://www.google.com/maps/dir/?api=1&origin={origin['formatted_address'].replace(' ', '+')}&destination={destination['formatted_address'].replace(' ', '+')}&travelmode=transit"
            if transit_details:
                line_name = transit_details['line']['short_name']
                departure_stop = transit_details['departure_stop']['name']
                arrival_stop = transit_details['arrival_stop']['name']
                response += (f"🚌 На автобусе:\n"
                             f"- Маршрут: {line_name}\n"
                             f"- Остановка отправления: {departure_stop}\n"
                             f"- Остановка прибытия: {arrival_stop}\n"
                             f"- Время в пути: {transit['duration']['text']}\n"
                             f"[Посмотреть маршрут в Google Maps]({transit_link})\n\n")
            else:
                response += (f"🚌 На общественном транспорте:\n"
                             f"- Время в пути: {transit['duration']['text']}\n"
                             f"[Посмотреть маршрут в Google Maps]({transit_link})\n\n")

        # Указание самого быстрого способа
        mode_names = {
            "driving": "на автомобиле",
            "walking": "пешком",
            "transit": "на общественном транспорте"
        }
        response += f"✨ Самый быстрый способ добраться: {mode_names[fastest_mode]} ({fastest_time // 60} мин).\n\n"

        # Добавление погодных условий и рекомендаций
        response += f"🌤 Погодные условия:\n{weather_warnings}\n\n"
        response += f"🚦 Рекомендации по дорожной обстановке:\n{traffic_recommendations}\n"

        await update.message.reply_markdown(response)
    except Exception as e:
        logging.error(f"Ошибка при расчете маршрута: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса.")


# Команда для очистки истории
async def clear_history(update: Update, context):
    user_id = update.message.from_user.id
    if user_id in user_history:
        user_history[user_id] = []
        await update.message.reply_text("Ваша история запросов была очищена.")
    else:
        await update.message.reply_text("У вас нет сохраненной истории.")

# Регистрация новой команды
application.add_handler(CommandHandler("clearhistory", clear_history))

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
                         f"   - Время с учетом пробок: {entry['traffic']}\n")
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("У вас нет истории маршрутов.")

async def cancel(update: Update, context):
    user_id = update.message.from_user.id
    if user_id in user_state:
        del user_state[user_id]
        await update.message.reply_text("Ваш запрос был отменен.")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("history", history))
application.add_handler(CommandHandler("cancel", cancel))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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
