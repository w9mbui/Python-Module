let currentData = null;
let isCelsius = true;

function convertTemp(temp) {
    return isCelsius ? temp : (temp * 9/5) + 32;
}

function updateTempDisplay() {
    if (currentData) {
        const tempUnit = isCelsius ? '°C' : '°F';
        document.getElementById('weather-result').innerHTML = `
            <p>Temperature: ${convertTemp(currentData.temp).toFixed(1)} ${tempUnit}</p>
            <p>Humidity: ${currentData.humidity}%</p>
            <p>AQI: ${currentData.aqi}</p>
            <p>UV Index: ${currentData.uv}</p>
            <p>Pollen: ${JSON.stringify(currentData.pollen)}</p>
            <p>Condition: ${currentData.condition}</p>
            <p>Outfit Suggestion: ${currentData.outfit}</p>
            <p>Activity Suggestion: ${currentData.activity}</p>
        `;
    }
}

document.getElementById('temp-unit').addEventListener('change', (e) => {
    isCelsius = e.target.checked;
    updateTempDisplay();
});

async function fetchWeather() {
    const location = document.getElementById('location').value;
    const date = document.getElementById('date').value;
    if (!location) {
        alert('Please enter a location');
        return;
    }
    const response = await fetch('/get_weather', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({location, date})
    });
    currentData = await response.json();
    if (currentData.error) {
        alert(currentData.error);
        return;
    }
    updateTempDisplay();
}

async function checkCalendar() {
    const location = document.getElementById('location').value;
    if (!location) {
        alert('Please enter a location');
        return;
    }
    const response = await fetch('/check_calendar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({location})
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    document.getElementById('calendar-alerts').innerHTML = data.alerts.join('<br>') || 'No rain alerts';
}

async function getCommuteAlert() {
    const time = document.getElementById('commute-time').value;
    const location = document.getElementById('location').value;
    if (!location || !time) {
        alert('Please enter location and time');
        return;
    }
    const response = await fetch('/commute_alert', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({time, location})
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    document.getElementById('commute-result').innerText = data.alert;
}

async function getBestTimes() {
    const activity = document.getElementById('activity').value;
    const date = document.getElementById('activity-date').value;
    const location = document.getElementById('location').value;
    if (!location || !date || !activity) {
        alert('Please enter activity, date, and location');
        return;
    }
    const response = await fetch('/best_times', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({activity, date, location})
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    document.getElementById('best-times').innerHTML = data.best_times.join('<br>') || 'No suitable times';
}

async function saveMood() {
    if (!currentData) {
        alert('Get weather first!');
        return;
    }
    const mood = document.getElementById('mood').value;
    if (!mood || isNaN(mood) || mood < 1 || mood > 10) {
        alert('Mood must be a number between 1 and 10');
        return;
    }
    const response = await fetch('/save_mood', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({mood, temp: currentData.temp, condition: currentData.condition})
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    alert('Mood saved!');
}

async function loadChart() {
    const response = await fetch('/get_moods');
    const data = await response.json();
    const moods = data.moods;
    const labels = moods.map(m => m[0]);
    const moodScores = moods.map(m => parseInt(m[1]));
    const temps = moods.map(m => parseFloat(m[2]));

    const ctx = document.getElementById('mood-chart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {label: 'Mood', data: moodScores, borderColor: 'blue', fill: false},
                {label: 'Temperature (°C)', data: temps, borderColor: 'red', fill: false}
            ]
        },
        options: {
            scales: {
                y: {beginAtZero: true},
                x: {ticks: {autoSkip: true, maxRotation: 45, minRotation: 45}}
            }
        }
    });
}

async function addFavorite() {
    const city = document.getElementById('favorite-city').value;
    if (!city) {
        alert('Please enter a city');
        return;
    }
    const response = await fetch('/add_favorite', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({city})
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    alert('Favorite added!');
}

async function loadFavorites() {
    const response = await fetch('/get_favorites');
    const data = await response.json();
    document.getElementById('favorites-list').innerHTML = data.favorites.join('<br>') || 'No favorites';
}