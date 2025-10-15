from flask import Flask, render_template, request, jsonify
import requests
import os
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# API Keys (replace with your own or use env vars)
OPENWEATHER_API_KEY = 'your_openweather_api_key'
AMBEE_API_KEY = 'your_ambee_api_key'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class WeatherFetcher:
    def __init__(self):
        self.base_url = 'https://api.openweathermap.org/data/3.0/onecall'
        self.geo_url = 'https://api.openweathermap.org/geo/1.0/direct'

    def get_lat_lon(self, location):
        params = {'q': location, 'limit': 1, 'appid': OPENWEATHER_API_KEY}
        response = requests.get(self.geo_url, params=params)
        data = response.json()
        if data:
            return data[0]['lat'], data[0]['lon']
        return None, None

    def get_weather(self, location, date=None):
        lat, lon = self.get_lat_lon(location)
        if not lat:
            return None
        params = {'lat': lat, 'lon': lon, 'exclude': 'minutely', 'units': 'metric', 'appid': OPENWEATHER_API_KEY}
        response = requests.get(self.base_url, params=params)
        data = response.json()
        if date:
            try:
                target_date = datetime.datetime.strptime(date, '%Y-%m-%d')
                for daily in data.get('daily', []):
                    dt = datetime.datetime.fromtimestamp(daily['dt'])
                    if dt.date() == target_date.date():
                        return daily
                return None
            except ValueError:
                return None
        return data

    def get_forecast_hourly(self, location):
        data = self.get_weather(location)
        return data.get('hourly', []) if data else []

class PollenFetcher:
    def __init__(self):
        self.base_url = 'https://api.ambeedata.com/latest/pollen/by-place'

    def get_pollen(self, location):
        headers = {'x-api-key': AMBEE_API_KEY, 'Content-type': 'application/json'}
        params = {'place': location}
        response = requests.get(self.base_url, params=params, headers=headers)
        data = response.json()
        if data.get('message') == 'success' and data.get('data'):
            return data['data'][0]
        return None

class CalendarIntegrator:
    def get_credentials(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_events(self):
        try:
            service = build('calendar', 'v3', credentials=self.get_credentials())
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            events_result = service.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()
            return events_result.get('items', [])
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def check_rain_for_events(self, location):
        events = self.get_events()
        weather_fetcher = WeatherFetcher()
        alerts = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
            hourly = weather_fetcher.get_forecast_hourly(location)
            for hour in hourly:
                hour_dt = datetime.datetime.fromtimestamp(hour['dt'])
                if abs((hour_dt - dt).total_seconds()) < 3600:
                    if hour.get('rain', 0) > 0:
                        alerts.append(f"Rain expected during '{event['summary']}' at {dt}")
                    break
        return alerts

class MoodTracker:
    def save_mood(self, mood, temp, condition):
        with open('moods.txt', 'a') as f:
            f.write(f"{datetime.date.today()},{mood},{temp},{condition}\n")

    def get_moods(self):
        if not os.path.exists('moods.txt'):
            return []
        with open('moods.txt', 'r') as f:
            return [line.strip().split(',') for line in f]

class FavoriteManager:
    def add_favorite(self, city):
        with open('favorites.txt', 'a') as f:
            f.write(f"{city}\n")

    def get_favorites(self):
        if not os.path.exists('favorites.txt'):
            return []
        with open('favorites.txt', 'r') as f:
            return [line.strip() for line in f]

class Advisor:
    @staticmethod
    def suggest_outfit(temp, wind, rain):
        if rain > 0:
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
        if 'clear' in condition.lower():
            return "Perfect day for a walk!"
        if 'rain' in condition.lower():
            return "Stay indoors, maybe read a book."
        if temp > 20:
            return "Great for outdoor activities like hiking."
        return "Moderate weather, plan accordingly."

    @staticmethod
    def suggest_best_times(activity, date, location, hourly):
        good_hours = []
        try:
            target_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return []
        for hour in hourly:
            dt = datetime.datetime.fromtimestamp(hour['dt'])
            if dt.date() != target_date.date():
                continue
            temp = hour['temp']
            rain = hour.get('rain', {}).get('1h', 0)
            if activity == 'picnic' and temp > 15 and rain == 0:
                good_hours.append(dt.strftime('%H:%M'))
            elif activity == 'hike' and temp > 10 and rain == 0:
                good_hours.append(dt.strftime('%H:%M'))
            elif activity == 'wedding' and rain == 0:
                good_hours.append(dt.strftime('%H:%M'))
        return good_hours

    @staticmethod
    def commute_alert(commute_time, location):
        weather_fetcher = WeatherFetcher()
        hourly = weather_fetcher.get_forecast_hourly(location)
        try:
            target_dt = datetime.datetime.strptime(commute_time, '%H:%M')
        except ValueError:
            return "Invalid time format"
        today = datetime.date.today()
        target = datetime.datetime.combine(today, target_dt.time())
        for hour in hourly:
            hour_dt = datetime.datetime.fromtimestamp(hour['dt'])
            if abs((hour_dt - target).total_seconds()) < 3600:
                if hour.get('rain', {}).get('1h', 0) > 0:
                    return f"Rain expected on your route at {commute_time}"
                return "Clear commute!"
        return "No data for that time."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def get_weather():
    location = request.json.get('location')
    date = request.json.get('date')
    if not location:
        return jsonify({'error': 'Location is required'})
    weather_fetcher = WeatherFetcher()
    data = weather_fetcher.get_weather(location, date)
    if not data:
        return jsonify({'error': 'Location not found or invalid date'})
    
    if date:
        current = data
    else:
        current = data['current']
    
    pollen_fetcher = PollenFetcher()
    pollen = pollen_fetcher.get_pollen(location)
    
    advisor = Advisor()
    outfit = advisor.suggest_outfit(current['temp'], current.get('wind_speed', 0), current.get('rain', {}).get('1h', 0))
    activity = advisor.suggest_activity(current['weather'][0]['main'], current['temp'])
    
    response = {
        'temp': current['temp'],
        'humidity': current['humidity'],
        'aqi': 'N/A',  # OpenWeather One Call 3.0 needs separate AQI call
        'uv': current['uvi'],
        'pollen': pollen['Count'] if pollen else 'N/A',
        'condition': current['weather'][0]['main'],
        'outfit': outfit,
        'activity': activity
    }
    return jsonify(response)

@app.route('/check_calendar', methods=['POST'])
def check_calendar():
    location = request.json.get('location')
    if not location:
        return jsonify({'error': 'Location is required'})
    calendar = CalendarIntegrator()
    alerts = calendar.check_rain_for_events(location)
    return jsonify({'alerts': alerts})

@app.route('/commute_alert', methods=['POST'])
def commute_alert():
    commute_time = request.json.get('time')
    location = request.json.get('location')
    if not location or not commute_time:
        return jsonify({'error': 'Location and time are required'})
    alert = Advisor.commute_alert(commute_time, location)
    return jsonify({'alert': alert})

@app.route('/best_times', methods=['POST'])
def best_times():
    activity = request.json.get('activity')
    date = request.json.get('date')
    location = request.json.get('location')
    if not location or not date or not activity:
        return jsonify({'error': 'Activity, date, and location are required'})
    weather_fetcher = WeatherFetcher()
    hourly = weather_fetcher.get_forecast_hourly(location)
    best = Advisor.suggest_best_times(activity, date, location, hourly)
    return jsonify({'best_times': best})

@app.route('/save_mood', methods=['POST'])
def save_mood():
    mood = request.json.get('mood')
    temp = request.json.get('temp')
    condition = request.json.get('condition')
    if not mood or not temp or not condition:
        return jsonify({'error': 'Mood, temp, and condition are required'})
    try:
        mood = int(mood)
        if not 1 <= mood <= 10:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'Mood must be 1-10'})
    tracker = MoodTracker()
    tracker.save_mood(mood, temp, condition)
    return jsonify({'success': True})

@app.route('/get_moods', methods=['GET'])
def get_moods():
    tracker = MoodTracker()
    moods = tracker.get_moods()
    return jsonify({'moods': moods})

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    city = request.json.get('city')
    if not city:
        return jsonify({'error': 'City is required'})
    manager = FavoriteManager()
    manager.add_favorite(city)
    return jsonify({'success': True})

@app.route('/get_favorites', methods=['GET'])
def get_favorites():
    manager = FavoriteManager()
    favorites = manager.get_favorites()
    return jsonify({'favorites': favorites})

if __name__ == '__main__':
    app.run(debug=True)