from flask import Flask, request
import requests
import uuid

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"
BASE_URL = "https://beta-ple-bot.onrender.com"  # 🔥 CHANGE THIS

# ✅ Fixed pledge list
PLEDGES = {
    "simms": "pledge simms",
    "lane": "pledge lane",
    "allen": "pledge allen",
    "denton": "pledge denton",
    "anderson": "pledge anderson",
    "gillum": "pledge gillum",
    "davis": "pledge davis",
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
leaderboard = {}


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


@app.route("/", methods=["POST"])
def webhook():
    global assignments, leaderboard

    data = request.json

    text = (data.get("text") or "").lower()
    name = data.get("name")

    # 🏆 Leaderboard command
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

    # 🍞 Trigger
    if "pledgeduty" in text:
        assignment_id = str(uuid.uuid4())

        assignments.append({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        })

        # Keep only last 5
        if len(assignments) > 5:
            assignments.pop(0)

        link = f"{BASE_URL}/claim/{assignment_id}"

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap to claim:\n{link}"
        )

    return "OK"


# 🔥 Claim page (buttons for pledges only)
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
    <head>
        <title>Claim Duty</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: #0f172a;
                color: white;
                text-align: center;
                padding: 20px;
            }}
            h1 {{
                margin-bottom: 20px;
            }}
            button {{
                width: 90%;
                margin: 10px;
                padding: 15px;
                font-size: 18px;
                border-radius: 12px;
                border: none;
                background: #22c55e;
                color: white;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <h1>Select your name</h1>
        {buttons}
    </body>
    </html>
    """


# 🔥 Handle claim
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

            send_message(
                f"🔥 {claimer} has claimed {a['owner']}'s pledge duty"
            )

            return html_page(f"{claimer}, you got it 👍")

    return html_page("This assignment expired ❌")


# 🎨 Confirmation page
def html_page(message):
    return f"""
    <html>
    <head>
        <title>Success</title>
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
        </style>
    </head>
    <body>
        <div class="card">
            <h1>{message}</h1>
        </div>
    </body>
    </html>
    """
