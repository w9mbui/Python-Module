from flask import Flask, render_template, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

class WeatherCompanion:
    def __init__(self):
        self.forecast_api = "https://api.open-meteo.com/v1/forecast"
        self.geocode_api = "https://geocoding-api.open-meteo.com/v1/search"
        self.ip_api = "http://ip-api.com/json/"

    def get_lat_lon(self, location):
        params = {'name': location, 'count': 1}
        try:
            response = requests.get(self.geocode_api, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('results'):
                return data['results'][0]['latitude'], data['results'][0]['longitude']
            return None, None
        except requests.RequestException as e:
            print(f"Error fetching lat/lon: {e}")
            return None, None

    def get_weather(self, location, date=None):
        lat, lon = self.get_lat_lon(location)
        if not lat:
            return None
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,weather_code',
            'hourly': 'temperature_2m,precipitation',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
            'timezone': 'auto'
        }
        try:
            response = requests.get(self.forecast_api, params=params)
            response.raise_for_status()
            data = response.json()
            if date:
                try:
                    target_date = datetime.datetime.strptime(date, '%Y-%m-%d')
                    for i, daily_date in enumerate(data.get('daily', {}).get('time', [])):
                        dt = datetime.datetime.strptime(daily_date, '%Y-%m-%d')
                        if dt.date() == target_date.date():
                            return {
                                'temp': data['daily']['temperature_2m_max'][i],
                                'humidity': data['current']['relative_humidity_2m'],
                                'precipitation': data['daily']['precipitation_sum'][i],
                                'weather_code': data['current']['weather_code']
                            }
                    return None
                except ValueError:
                    return None
            return {
                'current': {
                    'temp': data['current']['temperature_2m'],
                    'humidity': data['current']['relative_humidity_2m'],
                    'precipitation': data['hourly']['precipitation'][0],
                    'weather_code': data['current']['weather_code']
                },
                'hourly': [
                    {'time': h, 'temp': t, 'precipitation': p}
                    for h, t, p in zip(data['hourly']['time'], data['hourly']['temperature_2m'], data['hourly']['precipitation'])
                ]
            }
        except requests.RequestException as e:
            print(f"Error fetching weather: {e}")
            return None

    def get_forecast_hourly(self, location):
        data = self.get_weather(location)
        return data.get('hourly', []) if data else []

    def get_location_by_ip(self):
        try:
            response = requests.get(self.ip_api)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'success':
                return data.get('city')
            return None
        except requests.RequestException as e:
            print(f"Error fetching IP location: {e}")
            return None

class MoodTracker:
    def save_mood(self, mood, temp, condition):
        try:
            with open('moods.txt', 'a') as f:
                f.write(f"{datetime.date.today()},{mood},{temp},{condition}\n")
        except IOError as e:
            print(f"Error saving mood: {e}")

    def get_moods(self):
        if not os.path.exists('moods.txt'):
            return []
        try:
            with open('moods.txt', 'r') as f:
                return [line.strip().split(',') for line in f]
        except IOError as e:
            print(f"Error reading moods: {e}")
            return []

class FavoriteManager:
    def add_favorite(self, city):
        try:
            with open('favorites.txt', 'a') as f:
                f.write(f"{city}\n")
        except IOError as e:
            print(f"Error saving favorite: {e}")

    def get_favorites(self):
        if not os.path.exists('favorites.txt'):
            return []
        try:
            with open('favorites.txt', 'r') as f:
                return [line.strip() for line in f]
        except IOError as e:
            print(f"Error reading favorites: {e}")
            return []

class Advisor:
    @staticmethod
    def suggest_outfit(temp, wind, precipitation):
        if precipitation > 0:
            return "Bring an umbrella or raincoat!"
        if temp < 10:
            return "It's chilly, grab a jacket!"
        if temp > 25:
            return "Light clothing, it's warm!"
        if wind > 20:  
            return "Windy, wear a windbreaker."
        return "Comfortable weather, casual outfit."

    @staticmethod
    def suggest_activity(condition, temp):
        if condition in [0, 1, 2]:  
            return "Perfect day for a walk!"
        if condition in [51, 53, 55, 61, 63, 65, 80, 81, 82]:  # Rain
            return "Stay indoors, maybe read a book."
        if temp > 20:
            return "Great for outdoor activities like hiking."
        return "Moderate weather, plan accordingly."

    