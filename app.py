from flask import Flask, request
import requests
import uuid
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"
BASE_URL = "https://beta-ple-bot.onrender.com"

# 📍 Arkadelphia coords
LAT = 34.1209
LON = -93.0538

DATA_FILE = "data.json"

# ✅ PLEDGES
PLEDGES = {
    "simms": "pledge simms",
    "lane": "pledge lane",
    "allen": "pledge allen",
    "denton": "pledge denton",
    "anderson": "pledge anderson",
    "gillum": "pledge gillum",
    "collier": "pledge collier",
    "woodard": "pledge woodard",
    "ballard": "pledge ballard",
    "earls": "pledge earls",
    "woolbright": "pledge woolbright",
    "reddin": "pledge reddin",
    "sommers": "pledge sommers",
    "crum": "pledge crum",
    "bell": "pledge bell",
    "correll": "pledge correll",
    "smith": "pledge smith",
    "ellis": "pledge ellis",
    "vance": "pledge vance",
    "nelson": "pledge nelson"
}

assignments = []

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

load_data()


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


# 🌤 WEATHER FUNCTION (fixed Fahrenheit)
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


# ⏰ DAILY WEATHER (8AM CENTRAL)
def scheduled_weather():
    send_message(get_weather())


scheduler = BackgroundScheduler(timezone="America/Chicago")
scheduler.add_job(scheduled_weather, "cron", hour=8, minute=0)
scheduler.start()


@app.route("/", methods=["POST"])
def webhook():
    global assignments, leaderboard, pledge_counts

    data = request.json
    text = (data.get("text") or "").lower()
    name = data.get("name")

    # 🌤 WEATHER COMMAND
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # 📊 PLEDGE DUTY TRACKER
    if "pledgeduty" in text:
        pledge_counts[name] = pledge_counts.get(name, 0) + 1
        save_data()
        send_message(f"📈 {name} has posted {pledge_counts[name]} duties")
        return "OK"

    # 🏆 PLEDGE DUTY LEADERBOARD
    if "pleaderboard" in text:
        if not pledge_counts:
            send_message("No duty counts yet")
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
        for i, (pid, score) in enumerate(sorted_lb, 1):
            display_name = PLEDGES.get(pid, "Unknown")
            msg += f"{i}. {display_name} — {score}\n"

        send_message(msg)
        return "OK"

    # 🍞 TRIGGER DUTY
    if "pledgeduty" in text:
        assignment_id = str(uuid.uuid4())

        assignments.append({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        })

        if len(assignments) > 5:
            assignments.pop(0)

        link = f"{BASE_URL}/claim/{assignment_id}"

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap to claim:\n{link}"
        )

    return "OK"


# 🔘 CLAIM PAGE
@app.route("/claim/<assignment_id>")
def claim_page(assignment_id):

    buttons = ""

    for pid, pname in PLEDGES.items():
        buttons += f"""
        <form action="/submit/{assignment_id}/{pid}" method="post">
            <button>{pname}</button>
        </form>
        """

    return f"""
    <html>
    <body style="background:#0f172a;color:white;text-align:center;">
        <h1>Select your name</h1>
        {buttons}
    </body>
    </html>
    """


# ✅ HANDLE CLAIM
@app.route("/submit/<assignment_id>/<pid>", methods=["POST"])
def submit_claim(assignment_id, pid):
    global assignments, leaderboard

    for a in assignments:
        if a["id"] == assignment_id:

            if a["claimed_by"] is not None:
                return html_page("Already claimed ❌")

            claimer = PLEDGES.get(pid, "Someone")
            a["claimed_by"] = claimer

            leaderboard[pid] = leaderboard.get(pid, 0) + 1
            save_data()

            send_message(
                f"🔥 {claimer} has claimed {a['owner']}'s pledge duty"
            )

            return html_page(f"{claimer}, you got it 👍")

    return html_page("This assignment expired ❌")


def html_page(message):
    return f"""
    <html>
    <body style="background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;">
        <h1>{message}</h1>
    </body>
    </html>
    """
