from flask import Flask, request
import requests
import uuid

app = Flask(__name__)

BOT_ID = "68219e78f1b2110053f1b4e4ed"

assignments = []
users = {}
leaderboard = {}  # 🔥 new


def send_message(text):
    url = "https://api.groupme.com/v3/bots/post"
    requests.post(url, json={"bot_id": BOT_ID, "text": text})


@app.route("/", methods=["POST"])
def webhook():
    global assignments, users, leaderboard

    data = request.json
    text = data.get("text", "").lower()
    name = data.get("name")
    user_id = data.get("user_id")

    # Track users
    users[user_id] = name

    # 🔥 Leaderboard command
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

    # Baker trigger
    if "pledge" in text:
        assignment_id = str(uuid.uuid4())

        assignments.append({
            "id": assignment_id,
            "owner": name,
            "claimed_by": None
        })

        if len(assignments) > 5:
            assignments.pop(0)

        # Personalized links
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

            # 🔥 Update leaderboard
            leaderboard[claimer] = leaderboard.get(claimer, 0) + 1

            send_message(
                f"🔥 {claimer} has claimed {a['owner']}'s pledge duty"
            )

            return styled_page(f"{claimer}, you got it 👍")

    return styled_page("This assignment expired ❌")


# 🎨 PROFESSIONAL UI
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
            button {{
                background: #22c55e;
                border: none;
                padding: 15px 25px;
                font-size: 18px;
                border-radius: 10px;
                color: white;
                cursor: pointer;
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
