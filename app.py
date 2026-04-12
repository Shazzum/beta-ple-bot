from flask import Flask, request, render_template_string
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

# =========================
# 📛 PLEDGES
# =========================
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
        supabase.table(table).update(
            {"score": existing.data[0]["score"] + amount}
        ).eq("name", name).execute()
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
# ⏰ DAILY JOB
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
# 🚀 WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():
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
        assignment_id = str(uuid.uuid4())

        supabase.table("assignments").insert({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        }).execute()

        add_score("pledge_counts", name, 1)

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap to claim:\n{BASE_URL}/claim/{assignment_id}"
        )

        return "OK"

    # 💰 balance
    if text == "!balance":
        send_message(f"{name} has {get_balance(name)} points 💰")
        return "OK"

    # 💰 richlist
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
# 🌐 CLAIM PAGE (BUTTON UI)
# =========================
@app.route("/claim/<assignment_id>", methods=["GET"])
def claim_page(assignment_id):
    res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()

    if not res.data:
        return "❌ Duty not found."

    assignment = res.data[0]

    if assignment["claimed_by"]:
        return f"❌ Already claimed by {assignment['claimed_by']}."

    buttons_html = ""
    for pledge in PLEDGES.keys():
        buttons_html += f"""
        <form method="POST" action="/claim/{assignment_id}">
            <input type="hidden" name="name" value="{pledge}">
            <button type="submit" style="margin:5px;padding:10px 20px;font-size:16px;">
                {pledge.capitalize()}
            </button>
        </form>
        """

    return render_template_string(f"""
        <h2>🍞 Claim Duty</h2>
        <p>Select your name:</p>
        {buttons_html}
    """)

# =========================
# ✅ CLAIM SUBMIT
# =========================
@app.route("/claim/<assignment_id>", methods=["POST"])
def claim_submit(assignment_id):
    user = request.form.get("name")

    if not user:
        return "❌ No name selected."

    res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()

    if not res.data:
        return "❌ Duty not found."

    assignment = res.data[0]

    if assignment["claimed_by"]:
        return f"❌ Already claimed by {assignment['claimed_by']}."

    supabase.table("assignments").update({
        "claimed_by": user
    }).eq("id", assignment_id).execute()

    send_message(f"✅ {user.capitalize()} claimed the duty!")

    return f"""
    <h2>✅ Claimed!</h2>
    <p>{user.capitalize()} has claimed this duty.</p>
    """

# =========================
# 🟢 HEALTH CHECK
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running ✅"

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
