import re
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import logging
from fastapi.responses import PlainTextResponse
from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import SessionLocal, engine
from models import Base, SearchHistory as SearchHistoryModel
from schemas import SearchHistoryCreate, SearchHistory, CityCount
from typing import List

# Инициализация базы данных
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Зависимости
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Получение статистики по городам
@app.get("/searches/stats/", response_model=List[CityCount])
def get_search_stats(db: Session = Depends(get_db)):
    stats = db.query(
        SearchHistoryModel.city,
        func.count(SearchHistoryModel.city).label("count")
    ).group_by(SearchHistoryModel.city).all()

    return [CityCount(city=city, count=count) for city, count in stats]


def get_weather_data(city_input):
    try:
        # Геокодирование
        pattern = r'^([\w\s-]+),\s*([\w\s-]+)$'
        match = re.match(pattern, city_input)

        if match:
            city, country = match.groups()
            # Формируем запрос с учетом города и страны
            geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&country={country}&count=1&language=ru&format=json"
        else:
            # Формируем запрос с учетом города
            geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_input}&count=1&language=ru&format=json"

        geo_response = requests.get(geocoding_url)
        geo_data = geo_response.json()

        logger.info(f"Geocoding response: {geo_data}")

        if not geo_data.get("results"):
            return None, f"Город '{city_input}' не найден"

        location = geo_data["results"][0]
        lat, lon = location["latitude"], location["longitude"]

        # Получение погоды
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,precipitation_probability,weathercode&forecast_days=1&timezone=auto"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        return weather_data, None

    except Exception as e:
        logger.error(f"Error in get_weather_data: {str(e)}")
        return None, "Произошла ошибка при получении данных о погоде"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("weather.html", {"request": request})


# Формируем словарь с основными показателями и сохраняем информацию о поиске в базе данных
@app.post("/", response_class=HTMLResponse)
async def get_weather(request: Request, city: str = Form(...), db: Session = Depends(get_db)):

    ip_address = request.client.host
    db_search = SearchHistoryModel(ip_address=ip_address, city=city)
    db.add(db_search)
    db.commit()
    db.refresh(db_search)
    logger.info(f"Added search: IP={ip_address}, City={city}")
    weather_data, error = get_weather_data(city)

    if error:
        return PlainTextResponse(error)

    if not weather_data or 'hourly' not in weather_data:
        return PlainTextResponse("Не удалось получить данные о погоде")

    hourly_data = list(zip(
        weather_data['hourly']['time'],
        weather_data['hourly']['temperature_2m'],
        weather_data['hourly']['precipitation_probability'],
        weather_data['hourly']['weathercode']
    ))

    return templates.TemplateResponse("weather_results.html", {
        "request": request,
        "city": city,
        "hourly_data": hourly_data
    })


# Собираем названия городов, на используемом API при вводе 1 или 2 букв выводится только 1 результат
@app.get("/autocomplete")
async def autocomplete(name: str):

    if len(name) < 3:
        return JSONResponse([])

    url = f"https://geocoding-api.open-meteo.com/v1/search?name={name}&count=100&language=ru&format=json"
    logger.info(f"Sending request to geocoding API: {url}")

    try:
        geo_response = requests.get(url)
        data = geo_response.json()

        cities = []
        if "results" in data:
            for result in data["results"]:
                country = result.get("country")
                if country:
                    cities.append(f'{result["name"]},{country}')

        logger.info(f"Returning {len(cities)} cities for name '{name}'")
        return JSONResponse(cities)
    except requests.RequestException as e:
        logger.error(f"Error fetching cities: {str(e)}")
        return JSONResponse({"error": "Failed to fetch cities"}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
