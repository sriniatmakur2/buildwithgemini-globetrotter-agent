import json
import urllib.request
import urllib.parse

def get_live_weather(location: str) -> str:
    """Fetch real-time current weather conditions for any travel destination worldwide.

    Args:
        location: City or destination name (e.g., 'Kyoto', 'Paris', 'San Francisco', 'Bali').

    Returns:
        A formatted summary string with real-time temperature in °C and °F, humidity, and wind speed.
    """
    try:
        encoded_location = urllib.parse.quote(location)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_location}&count=1"
        
        req = urllib.request.Request(geo_url, headers={"User-Agent": "GlobeTrotterAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            geo_data = json.loads(response.read().decode())
            
        results = geo_data.get("results")
        if not results:
            return f"Location '{location}' not found."
            
        loc_data = results[0]
        lat = loc_data["latitude"]
        lon = loc_data["longitude"]
        city_name = loc_data["name"]
        country = loc_data.get("country", "")
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        w_req = urllib.request.Request(weather_url, headers={"User-Agent": "GlobeTrotterAgent/1.0"})
        with urllib.request.urlopen(w_req, timeout=5) as response:
            weather_data = json.loads(response.read().decode())
            
        current = weather_data.get("current", {})
        temp_c = current.get("temperature_2m")
        temp_f = round(temp_c * 9/5 + 32, 1)
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        
        return (
            f"Current weather in {city_name}, {country}: "
            f"{temp_c}°C ({temp_f}°F), Humidity: {humidity}%, Wind: {wind} km/h."
        )
    except Exception as e:
        return f"Unable to fetch live weather for '{location}': {str(e)}"
