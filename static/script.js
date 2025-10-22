let currentUnits = 'celsius';
let lat, lon, city, timezone;
let chart;
let weatherData;

window.onload = () => {
    city = document.getElementById('currentCity').textContent;
    fetchInitialLocation();
    loadFavorites();
    loadAlerts();
};

function fetchInitialLocation() {
    fetch('/weather')  
        .then(res => res.json())
        .then(data => {
            if (data.weather && !data.weather.error) {
                updateDisplay(data);
                fetchCityImage(city);
            } else {
                document.getElementById('weatherInfo').innerHTML = '<p>Unable to fetch initial location-based weather.</p>';
            }
        });
}

function getWeather() {
    fetch(`/weather?lat=${lat}&lon=${lon}&timezone=${timezone}`)
        .then(res => res.json())
        .then(data => {
            updateDisplay(data);
            fetchCityImage(city);
        });
}

function updateDisplay(data) {
    weatherData = data.weather;
    if (weatherData.error) {
        document.getElementById('weatherInfo').innerHTML = `<p>Error: ${weatherData.error}</p>`;
        return;
    }
    const current = weatherData.current;
    const unit = '°C';
    let temp = current.temperature_2m;
    let feelsLike = current.apparent_temperature;
    if (currentUnits === 'fahrenheit') {
        temp = (temp * 9/5) + 32;
        feelsLike = (feelsLike * 9/5) + 32;
    }
    document.getElementById('weatherInfo').innerHTML = `
        <h2>Weather in ${city}</h2>
        <p>Temperature: ${temp.toFixed(1)}${currentUnits === 'celsius' ? '°C' : '°F'}</p>
        <p>Feels Like: ${feelsLike.toFixed(1)}${currentUnits === 'celsius' ? '°C' : '°F'}</p>
        <p>Precipitation: ${current.precipitation} mm</p>
        <p>Condition: ${getCondition(current.weather_code)}</p>
    `;
    document.getElementById('suggestions').innerHTML = `
        <h3>Friendly Suggestions:</h3>
        <ul>${data.suggestions.map(s => `<li>${s}</li>`).join('')}</ul>
    `;
    document.getElementById('currentCity').textContent = city;
    updateBackground(current.weather_code);
    checkAlerts(current.temperature_2m, current.precipitation);
    getTrends();
}

function fetchCityImage(cityName) {
    if (!cityName) return;
    fetch(`/city_image?city=${encodeURIComponent(cityName)}`)
        .then(res => res.json())
        .then(data => {
            if (data.image_url) {
                const imgElement = document.getElementById('cityImage');
                if (imgElement) {
                    imgElement.src = data.image_url;
                    imgElement.style.display = 'block';
                    imgElement.classList.add('fade-in');
                }
            }
        })
        .catch(err => console.error('Image fetch error:', err));
}

function getWeatherByCity() {
    const cityInput = document.getElementById('cityInput').value.trim();
    if (!cityInput) return;
    fetch(`/search_city?city=${encodeURIComponent(cityInput)}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            city = data.city;
            lat = data.lat;
            lon = data.lon;
            timezone = data.timezone;
            getWeather();
            fetchCityImage(city);
        });
}

function getTrends() {
    fetch(`/trends?lat=${lat}&lon=${lon}&timezone=${timezone}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error(data.error);
                return;
            }
            const daily = data.daily;
            const labels = daily.time;
            let temps = daily.temperature_2m_mean;
            if (currentUnits === 'fahrenheit') {
                temps = temps.map(t => (t * 9/5) + 32);
            }
            if (chart) chart.destroy();
            const ctx = document.getElementById('graph').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{ label: 'Mean Temperature', data: temps, borderColor: '#1E90FF', fill: false }]
                },
                options: { scales: { y: { beginAtZero: false } } }
            });
        });
}

function switchUnits() {
    currentUnits = currentUnits === 'celsius' ? 'fahrenheit' : 'celsius';
    getWeather();
}

function speakWeather() {
    if (!weatherData || weatherData.error) {
        alert('No weather data to speak.');
        return;
    }
    if ('speechSynthesis' in window) {
        const current = weatherData.current;
        let temp = current.temperature_2m;
        if (currentUnits === 'fahrenheit') temp = (temp * 9/5) + 32;
        const text = `Current temperature in ${city} is ${temp.toFixed(1)}${currentUnits === 'celsius' ? '°C' : '°F'}. Condition: ${getCondition(current.weather_code)}. ${document.getElementById('suggestions').innerText}`;
        const utterance = new SpeechSynthesisUtterance(text);
        speechSynthesis.speak(utterance);
    } else {
        alert('Voice feedback not supported.');
    }
}

function downloadForecast() {
    fetch(`/forecast?lat=${lat}&lon=${lon}&timezone=${timezone}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const daily = data.daily;
            let txt = `Daily Forecast for ${city}\n`;
            daily.time.forEach((time, i) => {
                let maxTemp = daily.temperature_2m_max[i];
                let minTemp = daily.temperature_2m_min[i];
                if (currentUnits === 'fahrenheit') {
                    maxTemp = (maxTemp * 9/5) + 32;
                    minTemp = (minTemp * 9/5) + 32;
                }
                txt += `${time}: Max ${maxTemp.toFixed(1)}${currentUnits === 'celsius' ? '°C' : '°F'}, Min ${minTemp.toFixed(1)}${currentUnits === 'celsius' ? '°C' : '°F'}, Precip ${daily.precipitation_sum[i]} mm, Condition: ${getCondition(daily.weather_code[i])}\n`;
            });
            const blob = new Blob([txt], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'forecast.txt';
            a.click();
        });
}

function addFavorite() {
    if (!city) return;
    let favorites = JSON.parse(localStorage.getItem('favorites')) || [];
    if (!favorites.some(f => f.city === city)) {
        favorites.push({ city, lat, lon, timezone });
        localStorage.setItem('favorites', JSON.stringify(favorites));
        loadFavorites();
    }
}

function loadFavorites() {
    let favorites = JSON.parse(localStorage.getItem('favorites')) || [];
    const ul = document.getElementById('favorites');
    ul.innerHTML = '';
    favorites.forEach(f => {
        const li = document.createElement('li');
        li.textContent = f.city;
        li.onclick = () => {
            city = f.city;
            lat = f.lat;
            lon = f.lon;
            timezone = f.timezone;
            getWeather();
            fetchCityImage(city);
        };
        ul.appendChild(li);
    });
}

function setAlerts() {
    const maxTemp = parseFloat(document.getElementById('maxTemp').value);
    const maxRain = parseFloat(document.getElementById('maxRain').value);
    localStorage.setItem('alerts', JSON.stringify({ maxTemp, maxRain, units: currentUnits }));
}

function loadAlerts() {
    const alerts = JSON.parse(localStorage.getItem('alerts'));
    if (alerts) {
        document.getElementById('maxTemp').value = alerts.maxTemp;
        document.getElementById('maxRain').value = alerts.maxRain;
    }
}

function checkAlerts(tempC, precip) {
    const alerts = JSON.parse(localStorage.getItem('alerts'));
    if (!alerts) return;
    let temp = tempC;
    if (alerts.units === 'fahrenheit') temp = (temp * 9/5) + 32;
    else if (currentUnits === 'fahrenheit') temp = (temp * 9/5) + 32;
    if (temp > alerts.maxTemp) {
        alert(`Temperature alert: Current temp ${temp.toFixed(1)} exceeds limit ${alerts.maxTemp}!`);
    }
    if (precip > alerts.maxRain) {
        alert(`Rain alert: Precipitation ${precip} mm exceeds limit ${alerts.maxRain}!`);
    }
}

function getCondition(code) {
    const codes = {
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
    };
    return codes[code] || 'Unknown';
}

function updateBackground(code) {
    const body = document.body;
    body.classList.remove('sunny', 'rainy', 'cloudy');
    if (code === 0 || code === 1 || code === 2) body.classList.add('sunny');
    else if (code >= 51 && code <= 99 && code !== 71 && code !== 73 && code !== 75 && code !== 77 && code !== 85 && code !== 86) body.classList.add('rainy');
    else body.classList.add('cloudy');
}
