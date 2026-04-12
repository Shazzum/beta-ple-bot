from flask import Flask, request
import requests
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from supabase import create_client
import os

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"
BASE_URL = "https://beta-ple-bot.onrender.com"

LAT = 34.1209
LON = -93.0538

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
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

# =========================
# 💰 ECONOMY
# =========================
def get_balance(name):
    res = supabase.table("balances").select("*").eq("name", name).execute()
    if res.data:
        return res.data[0]["balance"]
    else:
        supabase.table("balances").insert({"name": name, "balance": 100}).execute()
        return 100

def add_balance(name, amount):
    bal = get_balance(name)
    supabase.table("balances").update({"balance": bal + amount}).eq("name", name).execute()

def subtract_balance(name, amount):
    bal = get_balance(name)
    if bal < amount:
        return False
    supabase.table("balances").update({"balance": bal - amount}).eq("name", name).execute()
    return True

# =========================
# 📤 SEND MESSAGE
# =========================
def send_message(text):
    requests.post(
        "https://api.groupme.com/v3/bots/post",
        json={"bot_id": BOT_ID, "text": text}
    )

# =========================
# 📊 LEADERBOARDS
# =========================
def add_score(table, name, amount):
    existing = supabase.table(table).select("*").eq("name", name).execute()
    if existing.data:
        supabase.table(table).update({"score": existing.data[0]["score"] + amount}).eq("name", name).execute()
    else:
        supabase.table(table).insert({"name": name, "score": amount}).execute()

def get_leaderboard(table):
    return supabase.table(table).select("*").order("score", desc=True).execute().data

# =========================
# 🌤 WEATHER
# =========================
def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=America/Chicago"
    res = requests.get(url).json()
    daily = res.get("daily", {})
    return f"🌤 Arkadelphia Weather\nHigh: {round(daily['temperature_2m_max'][0])}°F\nLow: {round(daily['temperature_2m_min'][0])}°F"

# =========================
# ⏰ DAILY JOB (SAFE)
# =========================
def daily_job():
    try:
        users = supabase.table("balances").select("*").execute().data
        for u in users:
            add_balance(u["name"], 100)

        send_message("💰 Everyone got +100 points!")
        send_message(get_weather())
    except Exception as e:
        print("Daily job error:", e)

scheduler = BackgroundScheduler(timezone="America/Chicago")

def start_scheduler():
    try:
        if not scheduler.running:
            scheduler.add_job(daily_job, "cron", hour=8, minute=0)
            scheduler.start()
            print("Scheduler started")
    except Exception as e:
        print("Scheduler failed:", e)

start_scheduler()

# =========================
# 🔧 HELPER
# =========================
def extract_parentheses(text):
    results = []
    current = ""
    inside = False

    for char in text:
        if char == "(":
            inside = True
            current = ""
        elif char == ")":
            inside = False
            results.append(current.strip())
        elif inside:
            current += char

    return results

# =========================
# 📊 LIVE ODDS
# =========================
def send_odds(bet):
    entries = supabase.table("bet_entries").select("*").eq("bet_id", bet["id"]).execute().data

    if not entries:
        return

    options = bet["options"].split(",")

    msg = "📊 Current Odds:\n\n"

    for opt in options:
        users = [e for e in entries if e["option"] == opt]
        total = sum(e["amount"] for e in users)

        msg += f"{opt} — {len(users)} players ({total})\n"

    send_message(msg)

# =========================
# 🚀 WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():
    global assignments

    data = request.json
    if not data:
        return "OK"

    if data.get("sender_type") == "bot":
        return "OK"

    raw_text = data.get("text")
    if not raw_text:
        return "OK"

    text = raw_text.lower().replace("\n", "").replace("\r", "").strip()
    name = data.get("name")

    print("Incoming:", repr(text))

    # 🍞 pledgeduty
    if "pledgeduty" in text:
        print("PLEDGEDUTY TRIGGERED")

        add_score("pledge_counts", name, 1)

        assignment_id = str(uuid.uuid4())

        assignments.append({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        })

        if len(assignments) > 5:
            assignments.pop(0)

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap to claim:\n{BASE_URL}/claim/{assignment_id}"
        )

        return "OK"

    # 💰 balance
    if text == "!balance":
        send_message(f"{name} has {get_balance(name)} points 💰")
        return "OK"

    # 💰 richlist (ALL)
    if text == "!richlist":
        data = supabase.table("balances").select("*").order("balance", desc=True).execute().data
        msg = "💰 Richlist:\n\n"
        for i, row in enumerate(data, 1):
            msg += f"{i}. {row['name']} — {row['balance']}\n"
        send_message(msg)
        return "OK"

    # 🌤 weather
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    return "OK"

# =========================
# 🟢 HEALTH CHECK ROUTE
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
