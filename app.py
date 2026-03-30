from flask import Flask, request
import requests
import uuid

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"
BASE_URL = "https://beta-ple-bot.onrender.com"  # 🔥 CHANGE THIS

assignments = []
users = {}
leaderboard = {}


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


@app.route("/", methods=["POST"])
def webhook():
    global assignments, users, leaderboard

    data = request.json

    # ✅ Safe text handling
    text = (data.get("text") or "").lower()
    name = data.get("name")
    user_id = data.get("user_id")

    # Track users (alias)
    users[user_id] = name

    # 🏆 Leaderboard command
    if "!leaderboard" in text:
        if not leaderboard:
            send_message("No claims yet")
            return "OK"

        sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)

        msg = "🏆 Leaderboard:\n\n"
        for i, (uid, score) in enumerate(sorted_lb, 1):
            display_name = users.get(uid, "Unknown")
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

        # 🔥 Personalized links
        links = []
        for uid, uname in users.items():
            link = f"{BASE_URL}/claim/{assignment_id}/{uid}"
            links.append(f"{uname}: {link}")

        send_message(
            f"🍞 {name} posted a pledge duty\n\nTap your name to claim:\n\n" +
            "\n".join(links)
        )

    return "OK"


@app.route("/claim/<assignment_id>/<user_id>")
def claim(assignment_id, user_id):
    global assignments, leaderboard, users

    print("CLAIM HIT:", assignment_id, user_id)  # 🔥 debug

    for a in assignments:
        if a["id"] == assignment_id:

            if a["claimed_by"] is not None:
                return html_page("Already claimed ❌")

            claimer = users.get(user_id, "Someone")
            a["claimed_by"] = claimer

            # ✅ Track by user_id (important)
            leaderboard[user_id] = leaderboard.get(user_id, 0) + 1

            send_message(
                f"🔥 {claimer} has claimed {a['owner']}'s pledge duty"
            )

            return html_page(f"{claimer}, you got it 👍")

    return html_page("This assignment expired ❌")


# 🎨 Clean UI
def html_page(message):
    return f"""
    <html>
    <head>
        <title>Pledge Duty</title>
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
                margin: 0;
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
