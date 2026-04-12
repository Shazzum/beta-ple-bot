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
# 🏆 LEADERBOARD HELPERS
# =========================
def add_pledge_claim(pid):
    res = supabase.table("pledge_leaderboard").select("*").eq("name", pid).execute()
    if res.data:
        supabase.table("pledge_leaderboard").update({
            "score": res.data[0]["score"] + 1
        }).eq("name", pid).execute()
    else:
        supabase.table("pledge_leaderboard").insert({
            "name": pid,
            "score": 1
        }).execute()

def add_duty_post(user):
    res = supabase.table("duty_posts").select("*").eq("name", user).execute()
    if res.data:
        supabase.table("duty_posts").update({
            "count": res.data[0]["count"] + 1
        }).eq("name", user).execute()
    else:
        supabase.table("duty_posts").insert({
            "name": user,
            "count": 1
        }).execute()

# =========================
def send_message(text):
    requests.post("https://api.groupme.com/v3/bots/post", json={"bot_id": BOT_ID, "text": text})

# =========================
# 🌤 WEATHER
# =========================
def get_weather():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit&timezone=America/Chicago"
    res = requests.get(url).json()
    daily = res.get("daily", {})
    return f"🌤 Arkadelphia Weather\nHigh: {round(daily['temperature_2m_max'][0])}°F\nLow: {round(daily['temperature_2m_min'][0])}°F"

# =========================
# ⏰ DAILY REWARDS
# =========================
def daily_rewards():
    users = supabase.table("balances").select("*").execute().data
    for u in users:
        add_balance(u["name"], 100)
    send_message("💰 Everyone got +100 points!")

scheduler = BackgroundScheduler(timezone="America/Chicago")
scheduler.add_job(daily_rewards, "cron", hour=8, minute=0)
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
# 🚀 WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    text = (data.get("text") or "").lower()
    name = data.get("name")

    if text == "!balance":
        send_message(f"{name} has {get_balance(name)} points 💰")
        return "OK"

    if text == "!richlist":
        data = supabase.table("balances").select("*").order("balance", desc=True).execute().data
        msg = "💰 Richlist:\n\n"
        for i, row in enumerate(data[:10], 1):
            msg += f"{i}. {row['name']} — {row['balance']}\n"
        send_message(msg)
        return "OK"

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

    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # 🎲 CREATE BET (FIXED)
    if text.startswith("!bet"):
        parts = extract_parentheses(text)
        if len(parts) < 2:
            send_message("Format: !bet (question) (option1) (option2) (option3...)")
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
            msg += f"• {o}\n"

        send_message(msg)
        return "OK"

    # 🎲 JOIN (FIXED)
    if text.startswith("!join"):
        parts = extract_parentheses(text)
        if len(parts) < 2:
            send_message("Format: !join (bet name) (option)")
            return "OK"

        bet_name = parts[0]
        choice = parts[1]

        bet = supabase.table("bets").select("*").eq("question", bet_name).eq("active", True).execute().data
        if not bet:
            send_message("Bet not found ❌")
            return "OK"

        bet = bet[0]
        options = [o.strip() for o in bet["options"].split(",")]

        matched = None
        for o in options:
            if o.lower() == choice.lower():
                matched = o
                break

        if not matched:
            send_message(f"Invalid option ❌ Options: {', '.join(options)}")
            return "OK"

        if not subtract_balance(name, 100):
            send_message("Not enough money ❌")
            return "OK"

        supabase.table("bet_entries").insert({
            "bet_id": bet["id"],
            "user": name,
            "option": matched,
            "amount": 100
        }).execute()

        send_message(f"{name} joined {bet_name} → {matched}")
        return "OK"

    # 🎲 RESOLVE (UNCHANGED)
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

    # 🍞 DUTY
    if text.strip() == "pledgeduty":
        add_duty_post(name)

        assignment_id = str(uuid.uuid4())

        supabase.table("assignments").insert({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        }).execute()

        send_message(f"🍞 {name} posted a pledge duty\n{BASE_URL}/claim/{assignment_id}")
        return "OK"

    # 🏆 LEADERBOARDS
    # 🏆 LEADERBOARDS
if text == "!leaderboard":
    data = supabase.table("pledge_leaderboard").select("*").order("score", desc=True).execute().data

    if not data:
        send_message("No claims yet ❌")
        return "OK"

    msg = "🏆 Pledge Leaderboard:\n\n"
    for i, row in enumerate(data, 1):
        msg += f"{i}. {PLEDGES.get(row['name'], row['name'])} — {row['score']}\n"

    send_message(msg)
    return "OK"

if text == "!pleaderboard":
    data = supabase.table("duty_posts").select("*").order("count", desc=True).execute().data

    if not data:
        send_message("No duties posted yet ❌")
        return "OK"

    msg = "📊 Duty Post Leaderboard:\n\n"
    for i, row in enumerate(data, 1):
        msg += f"{i}. {row['name']} — {row['count']}\n"

    send_message(msg)
    return "OK"


    return "OK"

# =========================
# CLAIM PAGE
# =========================
@app.route("/claim/<assignment_id>")
def claim_page(assignment_id):
    res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
    if not res.data:
        return "Expired ❌"

    assignment = res.data[0]

    if assignment["claimed_by"]:
        return f"Already claimed by {assignment['claimed_by']} ❌"

    buttons = ""
    for pid, pname in PLEDGES.items():
        buttons += f"""
        <form action="/submit/{assignment_id}/{pid}" method="post">
            <button>{pname}</button>
        </form>
        """

    return f"<h1>Select your name</h1>{buttons}"

# =========================
# CLAIM SUBMIT
# =========================
@app.route("/submit/<assignment_id>/<pid>", methods=["POST"])
def submit_claim(assignment_id, pid):
    res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
    assignment = res.data[0]

    if assignment["claimed_by"]:
        return "Already claimed ❌"

    add_pledge_claim(pid)

    supabase.table("assignments").update({
        "claimed_by": PLEDGES.get(pid)
    }).eq("id", assignment_id).execute()

    send_message(f"🔥 {PLEDGES.get(pid)} claimed {assignment['owner']}'s duty")

    return f"{PLEDGES.get(pid)} claimed it 👍"

@app.route("/", methods=["GET"])
def home():
    return "Bot running ✅"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
