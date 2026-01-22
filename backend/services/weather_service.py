import requests
import logging
from config import settings

logger = logging.getLogger(__name__)

OPENWEATHERMAP_API_KEY = getattr(settings, 'OPENWEATHERMAP_API_KEY', None)

def get_weather_forecast(city: str = "Berlin") -> dict:
    """
    Fetches current weather data from OpenWeatherMap API.
    Returns dict with temp, description, humidity, wind, etc.
    """
    if not OPENWEATHERMAP_API_KEY:
        logger.warning("OpenWeatherMap API key not configured")
        return None
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": OPENWEATHERMAP_API_KEY,
            "units": "metric",  # Celsius
            "lang": "de"  # German descriptions
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "city": data.get("name", city),
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"] * 3.6),  # m/s to km/h
            "rain": data.get("rain", {}).get("1h", 0),
        }
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return None


def get_clothing_recommendation(weather: dict) -> str:
    """
    Generates clothing recommendation based on weather data.
    """
    if not weather:
        return ""
    
    temp = weather["temp"]
    rain = weather.get("rain", 0)
    wind = weather.get("wind_speed", 0)
    
    recommendations = []
    
    # Temperature-based
    if temp < 0:
        recommendations.append("Winterjacke, Mütze und Handschuhe")
    elif temp < 10:
        recommendations.append("warme Jacke und eventuell Schal")
    elif temp < 18:
        recommendations.append("leichte Jacke oder Pullover")
    elif temp < 25:
        recommendations.append("T-Shirt und leichte Hose")
    else:
        recommendations.append("luftige Kleidung und Sonnenschutz")
    
    # Rain
    if rain > 0:
        recommendations.append("Regenschirm nicht vergessen")
    
    # Wind
    if wind > 30:
        recommendations.append("windfeste Kleidung empfohlen")
    
    return ", ".join(recommendations)


def get_weather_briefing(city: str = "Berlin") -> str:
    """
    Returns a formatted weather section for the briefing.
    """
    weather = get_weather_forecast(city)
    
    if not weather:
        return "Wetterdaten sind momentan nicht verfügbar."
    
    clothing = get_clothing_recommendation(weather)
    
    return (
        f"Das Wetter in {weather['city']}: "
        f"{weather['temp']} Grad, {weather['description']}. "
        f"Gefühlt wie {weather['feels_like']} Grad. "
        f"Meine Empfehlung für heute: {clothing}."
    )
