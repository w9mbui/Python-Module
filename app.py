from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='templates', static_folder='static')

PEXELS_API_KEY = "LX1WrezSMyT7DDUIOEOdV7baQXlbQYkSiKuGH5CoPrdvZMnNlJKpk7uC"

class WeatherCompanion:
    def __init__(self):
        self.forecast_api = "https://api.open-meteo.com/v1/forecast"
        self.geocode_api = "https://geocoding-api.open-meteo.com/v1/search"
        self.ip_api = "http://ip-api.com/json/"
        self.weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }

    def get_location_by_ip(self, ip=None):
        try:
            response = requests.get(self.ip_api + (ip if ip else ''), timeout=5)
            data = response.json()
            if data['status'] == 'success':
                return data['city'], data['lat'], data['lon'], data['timezone']
        except Exception:
            pass
        return None, None, None, None

    def search_city(self, city_name):
        try:
            params = {'name': city_name, 'count': 1, 'language': 'en', 'format': 'json'}
            response = requests.get(self.geocode_api, params=params, timeout=5)
            data = response.json()
            if data.get('results'):
                result = data['results'][0]
                return result['name'], result['latitude'], result['longitude'], result['timezone']
        except Exception:
            pass
        return None, None, None, None

    def get_weather(self, lat, lon, timezone='auto'):
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,apparent_temperature,precipitation,weather_code',
                'temperature_unit': 'celsius',
                'timezone': timezone
            }
            response = requests.get(self.forecast_api, params=params, timeout=5)
            return response.json()
        except Exception:
            return {'error': 'Failed to fetch weather data'}

    def get_trends(self, lat, lon, timezone='auto'):
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': 'temperature_2m_mean',
                'past_days': 7,
                'forecast_days': 0,
                'temperature_unit': 'celsius',
                'timezone': timezone
            }
            response = requests.get(self.forecast_api, params=params, timeout=5)
            return response.json()
        except Exception:
            return {'error': 'Failed to fetch trends data'}

    def get_daily_forecast(self, lat, lon, timezone='auto'):
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code',
                'forecast_days': 7,
                'temperature_unit': 'celsius',
                'timezone': timezone
            }
            response = requests.get(self.forecast_api, params=params, timeout=5)
            return response.json()
        except Exception:
            return {'error': 'Failed to fetch forecast data'}

    def get_suggestions(self, weather_data):
        if 'error' in weather_data:
            return ['Unable to generate suggestions due to data fetch error.']
        current = weather_data.get('current', {})
        temp = current.get('temperature_2m', 0)
        code = current.get('weather_code', 0)
        precip = current.get('precipitation', 0)
        condition = self.weather_codes.get(code, "Unknown")

        suggestions = []
        if 'rain' in condition.lower() or precip > 0:
            suggestions.append("It might rain — carry an umbrella!")
        if temp == 0 and temp > 20:
            suggestions.append("Perfect day for a walk!")
        if temp < 10:
            suggestions.append("It's chilly — bundle up!")
        return suggestions

    def get_city_image(self, city_name):
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": city_name, "per_page": 1, "orientation": "landscape"}
        try:
            response = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params, timeout=5)
            data = response.json()
            if "photos" in data and len(data["photos"]) > 0:
                return data["photos"][0]["src"]["large"]
        except Exception:
            pass
        return "https://via.placeholder.com/800x400?text=No+Image+Found"


companion = WeatherCompanion()


@app.route('/')
def index():
    ip = request.remote_addr
    city, lat, lon, timezone = companion.get_location_by_ip(ip)
    if not city:
        city, lat, lon, timezone = "Unknown", 0, 0, "auto"
    return render_template('index.html', city=city, lat=lat, lon=lon, timezone=timezone)


@app.route('/weather')
def weather():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    timezone = request.args.get('timezone', 'auto')
    data = companion.get_weather(lat, lon, timezone)
    suggestions = companion.get_suggestions(data)
    return jsonify({'weather': data, 'suggestions': suggestions})


@app.route('/trends')
def trends():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    timezone = request.args.get('timezone', 'auto')
    data = companion.get_trends(lat, lon, timezone)
    return jsonify(data)


@app.route('/forecast')
def forecast():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    timezone = request.args.get('timezone', 'auto')
    data = companion.get_daily_forecast(lat, lon, timezone)
    return jsonify(data)


@app.route('/search_city')
def search_city():
    city_name = request.args.get('city')
    if not city_name:
        return jsonify({'error': 'City name required'})
    city, lat, lon, timezone = companion.search_city(city_name)
    if not city:
        return jsonify({'error': 'City not found'})
    
    # Get city image from Pexels
    image_url = companion.get_city_image(city_name)
    
    return jsonify({'city': city, 'lat': lat, 'lon': lon, 'timezone': timezone, 'image_url': image_url})


if __name__ == '__main__':
    app.run(debug=True)
