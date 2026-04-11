from flask import Flask, request
import requests
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"
BASE_URL = "https://beta-ple-bot.onrender.com"

LAT = 34.1209
LON = -93.0538

# 🔥 SUPABASE SETUP
SUPABASE_URL = "https://nanarwxrozdcajidmuba.supabase.co"
SUPABASE_KEY = "sb_publishable_oBvZVUIfXr3haQ38sfPHRw_83C6Svzw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


# 🔥 DATABASE HELPERS
def add_score(table, name, amount):
    existing = supabase.table(table).select("*").eq("name", name).execute()

    if existing.data:
        new_score = existing.data[0]["score"] + amount
        supabase.table(table).update({"score": new_score}).eq("name", name).execute()
    else:
        supabase.table(table).insert({"name": name, "score": amount}).execute()


def get_leaderboard(table):
    res = supabase.table(table).select("*").order("score", desc=True).execute()
    return res.data


# 🌤 WEATHER
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
    global assignments

    data = request.json
    text = (data.get("text") or "").lower()
    name = data.get("name")

    # 🌤 WEATHER
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # 🔥 ADMIN (!give)
    if text.startswith("!give"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        parts = text.split()

        if len(parts) != 3:
            send_message("Usage: !give [pledge] [amount]")
            return "OK"

        pid = parts[1]

        try:
            amount = int(parts[2])
        except:
            send_message("Amount must be a number")
            return "OK"

        if pid not in PLEDGES:
            send_message("Invalid pledge name")
            return "OK"

        add_score("leaderboard", pid, amount)

        send_message(
            f"⚡ {PLEDGES[pid]} received {amount} duties"
        )
        return "OK"

    # 📊 PLEDGEDUTY
    if text.strip() == "pledgeduty":
        add_score("pledge_counts", name, 1)

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
            f"🍞 {name} posted a pledge duty\n\n"
            f"Tap to claim:\n{link}"
        )

        return "OK"

    # 🏆 PLEDGEDUTY LEADERBOARD
    if "pleaderboard" in text:
        data = get_leaderboard("pledge_counts")

        msg = "📊 PledgeDuty Leaderboard:\n\n"
        for i, row in enumerate(data, 1):
            msg += f"{i}. {row['name']} — {row['score']}\n"

        send_message(msg)
        return "OK"

    # 🏆 CLAIM LEADERBOARD
    if "!leaderboard" in text:
        data = get_leaderboard("leaderboard")

        msg = "🏆 Leaderboard:\n\n"
        for i, row in enumerate(data, 1):
            display_name = PLEDGES.get(row["name"], "Unknown")
            msg += f"{i}. {display_name} — {row['score']}\n"

        send_message(msg)
        return "OK"

    return "OK"


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


@app.route("/submit/<assignment_id>/<pid>", methods=["POST"])
def submit_claim(assignment_id, pid):
    global assignments

    for a in assignments:
        if a["id"] == assignment_id:

            if a["claimed_by"] is not None:
                return html_page("Already claimed ❌")

            claimer = PLEDGES.get(pid, "Someone")
            a["claimed_by"] = claimer

            add_score("leaderboard", pid, 1)

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
