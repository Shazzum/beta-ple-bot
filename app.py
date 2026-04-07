from flask import Flask, request
import requests
import uuid
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"

assignments = []
users = {}

# 🔥 PERSISTENT STORAGE FILE
DATA_FILE = "data.json"


# 🔄 LOAD DATA
def load_data():
    global leaderboard, pledge_counts

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            leaderboard = data.get("leaderboard", {})
            pledge_counts = data.get("pledge_counts", {})
    else:
        leaderboard = {}
        pledge_counts = {}


# 💾 SAVE DATA
def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            "leaderboard": leaderboard,
            "pledge_counts": pledge_counts
        }, f)


# Load on startup
load_data()


# Arkadelphia coordinates
LAT = 34.1209
LON = -93.0538


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


# 🌤 WEATHER FUNCTION
def get_weather():
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&temperature_unit=fahrenheit"
        f"&timezone=America/Chicago"
    )

    res = requests.get(url).json()
    daily = res.get("daily", {})

    if not daily:
        return "Weather unavailable ❌"

    max_temp = round(daily["temperature_2m_max"][0])
    min_temp = round(daily["temperature_2m_min"][0])
    rain = daily["precipitation_probability_max"][0]

    return (
        f"🌤 Arkadelphia Weather (Today)\n\n"
        f"High: {max_temp}°F\n"
        f"Low: {min_temp}°F\n"
        f"Rain Chance: {rain}%"
    )


# ⏰ DAILY WEATHER
def scheduled_weather():
    send_message(get_weather())


scheduler = BackgroundScheduler(timezone="America/Chicago")
scheduler.add_job(scheduled_weather, "cron", hour=8, minute=0)
scheduler.start()


@app.route("/", methods=["POST"])
def webhook():
    global assignments, users, leaderboard, pledge_counts

    data = request.json
    text = data.get("text", "").lower()
    name = data.get("name")
    user_id = data.get("user_id")

    users[user_id] = name

    # 🌤 WEATHER COMMAND
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # 📊 PLEDGE DUTY TRACKER
    if "pledgeduty" in text:
        pledge_counts[name] = pledge_counts.get(name, 0) + 1
        save_data()  # 🔥 save immediately
        send_message(f"📈 {name} has done pledgeduty {pledge_counts[name]} times")
        return "OK"

    # 🏆 PLEDGE DUTY LEADERBOARD
    if "pleaderboard" in text:
        if not pledge_counts:
            send_message("No pledgeduty counts yet")
            return "OK"

        sorted_lb = sorted(pledge_counts.items(), key=lambda x: x[1], reverse=True)

        msg = "📊 PledgeDuty Leaderboard:\n\n"
        for i, (user, count) in enumerate(sorted_lb, 1):
            msg += f"{i}. {user} — {count}\n"

        send_message(msg)
        return "OK"

    # 🏆 CLAIM LEADERBOARD
    if "!leaderboard" in text:
        if not leaderboard:
            send_message("No claims yet")
            return "OK"

        sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

        msg = "🏆 Leaderboard:\n\n"
        for i, (user, score) in enumerate(sorted_lb, 1):
            msg += f"{i}. {user} — {score}\n"

        send_message(msg)
        return "OK"

    # 🍞 PLEDGE SYSTEM
    if "pledge" in text:
        assignment_id = str(uuid.uuid4())

        assignments.append({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        })

        if len(assignments) > 5:
            assignments.pop(0)

        links = []
        for uid, uname in users.items():
            link = f"https://your-app.onrender.com/claim/{assignment_id}/{uid}"
            links.append(f"{uname}: {link}")

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap your name to claim:\n\n" +
            "\n".join(links)
        )

    return "OK"


@app.route("/claim/<assignment_id>/<user_id>")
def claim(assignment_id, user_id):
    global assignments, leaderboard

    for a in assignments:
        if a["id"] == assignment_id:

            if a["claimed_by"] is not None:
                return styled_page("Already claimed ❌")

            claimer = users.get(user_id, "Someone")
            a["claimed_by"] = claimer

            leaderboard[claimer] = leaderboard.get(claimer, 0) + 1
            save_data()  # 🔥 save immediately

            send_message(
                f"🔥 {claimer} has claimed {a['owner']}'s pledge duty"
            )

            return styled_page(f"{claimer}, you got it 👍")

    return styled_page("This assignment expired ❌")


def styled_page(message):
    return f"""
    <html>
    <head>
        <title>Pledge Claim</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: #0f172a;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #1e293b;
                padding: 30px;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            }}
            h1 {{
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{message}</h1>
        </div>
    </body>
    </html>
    """
