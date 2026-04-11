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

SUPABASE_URL = "https://nanarwxrozdcajidmuba.supabase.co"
SUPABASE_KEY = "YOUR_KEY"
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
# 🚀 WEBHOOK
# =========================
@app.route("/", methods=["POST"])
def webhook():
    global assignments

    data = request.json
    text = (data.get("text") or "").lower()
    name = data.get("name")

    # 💰 BALANCE
    if text == "!balance":
        send_message(f"{name} has {get_balance(name)} points 💰")
        return "OK"

    # 💰 RICHLIST
    if text == "!richlist":
        data = supabase.table("balances").select("*").order("balance", desc=True).execute().data
        msg = "💰 Richlist:\n\n"
        for i, row in enumerate(data[:10], 1):
            msg += f"{i}. {row['name']} — {row['balance']}\n"
        send_message(msg)
        return "OK"

    # 👑 BLESS ALL
    if text.startswith("!blessall"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        try:
            amount = int(text.split()[1])
        except:
            send_message("Usage: !blessall [amount]")
            return "OK"

        users = supabase.table("balances").select("*").execute().data
        for u in users:
            add_balance(u["name"], amount)

        send_message(f"🙏 Mega blessed everyone with +{amount}")
        return "OK"

    # 🌤 WEATHER
    if "!weather" in text:
        send_message(get_weather())
        return "OK"

    # 🔥 GIVE (UNCHANGED)
    if text.startswith("!give"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        parts = text.split()
        pid = parts[1]
        amount = int(parts[2])

        add_score("leaderboard", pid, amount)
        send_message(f"⚡ {PLEDGES[pid]} received {amount}")
        return "OK"

    # =========================
    # 🎲 BET (FIXED)
    # =========================
    if text.startswith("!bet"):
        try:
            parts = text.split('"')
            if len(parts) < 3:
                send_message("Format: !bet \"question\" 1. option / 2. option")
                return "OK"

            question = parts[1]
            raw_options = parts[2]

            options = []
            for opt in raw_options.split("/"):
                if "." in opt:
                    options.append(opt.split(".", 1)[1].strip())

            if len(options) < 2:
                send_message("Need at least 2 options ❌")
                return "OK"

            options_str = ",".join(options)

        except:
            send_message("Invalid bet format ❌")
            return "OK"

        supabase.table("bets").insert({
            "id": str(uuid.uuid4()),
            "question": question,
            "options": options_str,
            "active": True,
            "resolved": False
        }).execute()

        send_message(f"🎲 Bet created: {question}")
        return "OK"

    # =========================
    # 🎲 JOIN
    # =========================
    if text.startswith("!join"):
        try:
            parts = text.split('"')
            bet_name = parts[1]
            choice = parts[3]
        except:
            send_message("Invalid format ❌")
            return "OK"

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
        return "OK"

    # =========================
    # 🎲 RESOLVE
    # =========================
    if text.startswith("!resolve"):
        if name != "Mega":
            send_message("Unauthorized ❌")
            return "OK"

        parts = text.split('"')
        bet_name = parts[1]
        winning = parts[3]

        bet = supabase.table("bets").select("*").eq("question", bet_name).eq("active", True).execute().data
        if not bet:
            send_message("Bet not found ❌")
            return "OK"

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

        send_message(f"🏆 Bet resolved: {winning}")
        return "OK"

    # =========================
    # 🍞 PLEDGE SYSTEM
    # =========================
    if text.strip() == "pledgeduty":
        add_score("pledge_counts", name, 1)

        assignment_id = str(uuid.uuid4())
        assignments.append({"id": assignment_id, "owner": name, "claimed_by": None})

        link = f"{BASE_URL}/claim/{assignment_id}"
        send_message(f"🍞 {name} posted a pledge duty\n\n{link}")
        return "OK"

    if "pleaderboard" in text:
        data = get_leaderboard("pledge_counts")
        msg = "📊 PledgeDuty Leaderboard:\n\n"
        for i, row in enumerate(data, 1):
            msg += f"{i}. {row['name']} — {row['score']}\n"
        send_message(msg)
        return "OK"

    if "!leaderboard" in text:
        data = get_leaderboard("leaderboard")
        msg = "🏆 Leaderboard:\n\n"
        for i, row in enumerate(data, 1):
            msg += f"{i}. {PLEDGES.get(row['name'],'Unknown')} — {row['score']}\n"
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
    return f"<html><body style='background:#0f172a;color:white;text-align:center;'><h1>Select your name</h1>{buttons}</body></html>"


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

            send_message(f"🔥 {claimer} has claimed {a['owner']}'s pledge duty")
            return html_page(f"{claimer}, you got it 👍")

    return html_page("This assignment expired ❌")


def html_page(message):
    return f"<html><body style='background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;'><h1>{message}</h1></body></html>"
