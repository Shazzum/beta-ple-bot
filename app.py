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

import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🔥 PLEDGES
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
# ⏰ DAILY JOB
# =========================
def daily_job():
    users = supabase.table("balances").select("*").execute().data
    for u in users:
        add_balance(u["name"], 100)

    send_message("💰 Everyone got +100 points!")
    send_message(get_weather())

scheduler = BackgroundScheduler(timezone="America/Chicago")
scheduler.add_job(daily_job, "cron", hour=8, minute=0)
scheduler.start()

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
# 🚀 WEBHOOK (FIXED)
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

    text = raw_text.lower().strip()
    name = data.get("name")

    print("Incoming:", repr(text))

    # =========================
    # 🍞 PLEDGEDUTY (FIXED)
    # =========================
    if text.startswith("pledgeduty"):
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

    # =========================
    # 💰 BALANCE
    # =========================
    if text == "!balance":
        send_message(f"{name} has {get_balance(name)} points 💰")
        return "OK"

    # =========================
    # 💰 RICHLIST (ALL USERS)
    # =========================
    if text == "!richlist":
        data = supabase.table("balances").select("*").order("balance", desc=True).execute().data

        msg = "💰 Richlist:\n\n"
        for i, row in enumerate(data, 1):
            msg += f"{i}. {row['name']} — {row['balance']}\n"

        send_message(msg)
        return "OK"

    # =========================
    # 👑 BLESSALL
    # =========================
    if text.startswith("!blessall"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        amount = int(text.split()[1])

        users = supabase.table("balances").select("*").execute().data
        for u in users:
            add_balance(u["name"], amount)

        send_message(f"🙏 Mega blessed everyone with +{amount}")
        return "OK"

    # =========================
    # 🌤 WEATHER
    # =========================
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # =========================
    # 🎲 BET
    # =========================
    if text.startswith("!bet"):
        parts = extract_parentheses(text)

        if len(parts) < 3:
            send_message("Format: !bet (name) (option1) (option2)")
            return "OK"

        bet_name = parts[0]
        options = parts[1:]

        supabase.table("bets").insert({
            "id": str(uuid.uuid4()),
            "question": bet_name,
            "options": ",".join(options),
            "active": True,
            "resolved": False
        }).execute()

        msg = f"🎲 NEW BET:\n\n{bet_name}\n\n"
        for o in options:
            msg += f"- {o}\n"

        send_message(msg)
        return "OK"

    # =========================
    # 🎲 JOIN
    # =========================
    if text.startswith("!join"):
        parts = extract_parentheses(text)

        bet_name = parts[0]
        choice = parts[1]

        bet = supabase.table("bets").select("*").eq("question", bet_name).eq("active", True).execute().data
        if not bet:
            send_message("Bet not found ❌")
            return "OK"

        bet = bet[0]
        options = bet["options"].split(",")

        if choice not in options:
            send_message("Invalid option ❌")
            return "OK"

        existing = supabase.table("bet_entries").select("*").eq("bet_id", bet["id"]).eq("user", name).execute().data
        if existing:
            send_message("Already joined ❌")
            return "OK"

        if not subtract_balance(name, 100):
            send_message("Not enough money ❌")
            return "OK"

        supabase.table("bet_entries").insert({
            "bet_id": bet["id"],
            "user": name,
            "option": choice,
            "amount": 100
        }).execute()

        send_message(f"{name} joined {bet_name} → {choice}")
        send_odds(bet)
        return "OK"

    # =========================
    # 🎲 RESOLVE
    # =========================
    if text.startswith("!resolve"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        parts = extract_parentheses(text)
        bet_name = parts[0]
        winning = parts[1]

        bet = supabase.table("bets").select("*").eq("question", bet_name).eq("active", True).execute().data
        bet = bet[0]

        entries = supabase.table("bet_entries").select("*").eq("bet_id", bet["id"]).execute().data

        if len(entries) < 5:
            for e in entries:
                add_balance(e["user"], e["amount"])
            send_message("Bet cancelled (not enough players)")
            return "OK"

        winners = [e for e in entries if e["option"] == winning]
        losers = [e for e in entries if e["option"] != winning]

        total_losers = sum(l["amount"] for l in losers)
        total_winners = sum(w["amount"] for w in winners)

        for w in winners:
            payout = int(w["amount"] + (w["amount"] / total_winners) * total_losers)
            add_balance(w["user"], payout)

        supabase.table("bets").update({
            "active": False,
            "resolved": True,
            "winning_option": winning
        }).eq("id", bet["id"]).execute()

        send_message(f"🏆 BET RESOLVED!\nWinner: {winning}")
        return "OK"

    return "OK"
