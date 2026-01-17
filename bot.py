import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3, time
from flask import Flask
from threading import Thread

# ================= CONFIG =================
API_ID = 33979655
API_HASH = "1486d052e4d73fe026b2d7d5bd667c47"
BOT_TOKEN = "8573641271:AAHuF0ehiyW33MJlMl9K_YueFKMEsdR8hnk"
ADMIN_ID = 7114473830
BOT_USERNAME = "Earnwithtasks2026_bot"  # Bot username

# ================= INIT BOT =================
app = Client("earn_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ================= DATABASE =================
db = sqlite3.connect("data.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    ref_by INTEGER,
    joined INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    link TEXT,
    min_duration INTEGER,
    reward_points INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_tasks (
    user_id INTEGER,
    task_id INTEGER,
    last_done INTEGER,
    PRIMARY KEY(user_id, task_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS withdraw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    method TEXT,
    number TEXT,
    amount INTEGER,
    status TEXT
)
""")
db.commit()

# ================= HELPERS =================
def add_user(uid, ref=None):
    if not cursor.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone():
        cursor.execute("INSERT INTO users (id, points, ref_by, joined) VALUES (?, ?, ?, ?)",
                       (uid, 0, ref, int(time.time())))
        db.commit()

def get_user(uid):
    return cursor.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 My Account", callback_data="account")],
        [InlineKeyboardButton("🔗 Refer & Earn", callback_data="refer")],
        [InlineKeyboardButton("🧠 Tasks", callback_data="task_list")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🛠 Support", url="https://t.me/neoEarner2026")]
    ])

def safe_edit(msg, text, markup=None):
    try:
        msg.edit_text(text, reply_markup=markup)
    except:
        pass

# ================= START =================
@app.on_message(filters.command("start"))
def start(_, msg):
    uid = msg.from_user.id
    ref = None
    if len(msg.command) > 1:
        try:
            ref = int(msg.command[1])
        except:
            ref = None

    add_user(uid, ref)
    if ref and cursor.execute("SELECT * FROM users WHERE id=?", (ref,)).fetchone():
        cursor.execute("UPDATE users SET points = points + 20 WHERE id=?", (ref,))
        db.commit()

    msg.reply("স্বাগতম! নিচের মেনু থেকে বেছে নাও 👇", reply_markup=main_menu())

# ================= CALLBACK =================
@app.on_callback_query()
def callback_handler(_, q):
    uid = q.from_user.id

    # -------- My Account --------
    if q.data == "account":
        user = get_user(uid)
        total_ref = cursor.execute("SELECT COUNT(*) FROM users WHERE ref_by=?", (uid,)).fetchone()[0]
        safe_edit(q.message, f"👤 My Account\n\n💰 Points: {user[1]}\n👥 Total Refer: {total_ref}", main_menu())

    # -------- Refer --------
    elif q.data == "refer":
        text = f"🔗 তোমার রেফার লিংক:\nhttps://t.me/{BOT_USERNAME}?start={uid}"
        safe_edit(q.message, text, main_menu())

    # -------- Tasks List --------
    elif q.data == "task_list":
        tasks = cursor.execute("SELECT task_id, title FROM tasks").fetchall()
        if not tasks:
            safe_edit(q.message, "🧠 বর্তমানে কোন টাস্ক নেই।\nAdmin দুঃখিত!", main_menu())
            return
        buttons = [[InlineKeyboardButton(t[1], callback_data=f"task_{t[0]}")] for t in tasks]
        safe_edit(q.message, "🧠 Available Tasks:", InlineKeyboardMarkup(buttons))

    # -------- Task Details --------
    elif q.data.startswith("task_"):
        task_id = int(q.data.split("_")[1])
        task = cursor.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        txt = f"🧠 {task[1]}\n\n{task[2]}"
        if task[3]:
            txt += "\n\n👇 Link Task:\n"
            buttons = [
                [InlineKeyboardButton("🔗 Open Link", url=task[3])],
                [InlineKeyboardButton("✅ Done", callback_data=f"done_{task_id}")]
            ]
        else:
            buttons = [[InlineKeyboardButton("✅ Done", callback_data=f"done_{task_id}")]]
        safe_edit(q.message, txt, InlineKeyboardMarkup(buttons))

    # -------- Task Done --------
    elif q.data.startswith("done_"):
        task_id = int(q.data.split("_")[1])
        now = int(time.time())
        record = cursor.execute("SELECT last_done FROM user_tasks WHERE user_id=? AND task_id=?",
                                (uid, task_id)).fetchone()
        if record and now - record[0] < 2700:  # 45 min cooldown
            q.answer("⏱️ Cooldown active! পরের জন্য অপেক্ষা করো.", show_alert=True)
            return
        task = cursor.execute("SELECT reward_points FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        points = task[0]
        if record:
            cursor.execute("UPDATE user_tasks SET last_done=? WHERE user_id=? AND task_id=?", (now, uid, task_id))
        else:
            cursor.execute("INSERT INTO user_tasks VALUES (?, ?, ?)", (uid, task_id, now))
        cursor.execute("UPDATE users SET points = points + ? WHERE id=?", (points, uid))
        db.commit()
        q.answer(f"✔️ {points} পয়েন্ট অ্যাড হয়েছে!", show_alert=True)
        safe_edit(q.message, "✔️ Task completed!\n\nমেনুতে ফিরে যাও 👇", main_menu())

    # -------- Withdraw --------
    elif q.data == "withdraw":
        safe_edit(q.message, "💸 Withdraw আবেদন পাঠান:\n\n/withdraw", main_menu())

# ================= WITHDRAW COMMAND =================
@app.on_message(filters.command("withdraw"))
def withdraw(_, msg):
    uid = msg.from_user.id
    user = get_user(uid)
    if not user:
        msg.reply("❌ প্রথমে /start লিখো!")
        return
    msg.reply("💸 Withdraw আবেদন:\nFormat:\n\n/req bkash 017XXXXXXXX 100")

@app.on_message(filters.command("req"))
def req_handler(_, msg):
    uid = msg.from_user.id
    args = msg.text.split()
    if len(args) != 4:
        msg.reply("❌ Format ভুল!\n\n/req bkash 017XXXXXXXX 100")
        return

    method, number, amount = args[1], args[2], args[3]
    try:
        amount = int(amount)
    except:
        msg.reply("❌ Amount টা নম্বর হতে হবে!")
        return

    if amount < 50:
        msg.reply("❌ Minimum withdraw 50 points")
        return

    cursor.execute("INSERT INTO withdraw(user_id, method, number, amount, status) VALUES(?,?,?,?,?)",
                   (uid, method, number, amount, "pending"))
    db.commit()
    msg.reply("✔️ Withdraw আবেদন পাঠানো হয়েছে। Admin অনুমোদন করবে।")

    # Admin notification with user points
    user = get_user(uid)
    app.send_message(ADMIN_ID,
                     f"💸 New Withdraw Request\n\n"
                     f"👤 User ID: {uid}\n"
                     f"💰 Current Points: {user[1]}\n"
                     f"💳 Method: {method}\n"
                     f"📱 Number: {number}\n"
                     f"💰 Amount: {amount}")

# ================= ADMIN PANEL =================
@app.on_message(filters.user(ADMIN_ID) & filters.command("tasks"))
def admin_task_list(_, msg):
    tasks = cursor.execute("SELECT * FROM tasks").fetchall()
    text = "📋 All Tasks:\n"
    for t in tasks:
        text += f"{t[0]}. {t[1]} — {t[5]} pts\n"
    msg.reply(text)

@app.on_message(filters.user(ADMIN_ID) & filters.command("addtask"))
def admin_add_task(_, msg):
    parts = msg.text.split("|")
    if len(parts) != 6:
        msg.reply("❌ Format:\n/addtask|title|desc|link(or None)|minsec|points")
        return
    _, title, desc, link, minsec, pts = parts
    try:
        minsec = int(minsec)
        pts = int(pts)
    except:
        msg.reply("❌ minsec ও points টা নম্বর দিতে হবে!")
        return
    if link.lower() == "none":
        link = ""
    cursor.execute("INSERT INTO tasks(title,description,link,min_duration,reward_points) VALUES(?,?,?,?,?)",
                   (title, desc, link, minsec, pts))
    db.commit()
    msg.reply("✔️ Task added!")

@app.on_message(filters.user(ADMIN_ID) & filters.command("deltask"))
def admin_delete_task(_, msg):
    try:
        tid = int(msg.text.split()[1])
        cursor.execute("DELETE FROM tasks WHERE task_id=?", (tid,))
        db.commit()
        msg.reply("✔️ Task deleted!")
    except:
        msg.reply("❌ Format:\n/deltask <task_id>")

@app.on_message(filters.user(ADMIN_ID) & filters.command("broadcast"))
def admin_broadcast(_, msg):
    text = msg.text.split(None, 1)[1]
    users = cursor.execute("SELECT id FROM users").fetchall()
    for u in users:
        try:
            app.send_message(u[0], text)
        except:
            pass
    msg.reply("✔️ Broadcast sent!")

# ================= FLASK SERVER FOR 24/7 =================
flask_app = Flask("")

@flask_app.route("/")
def home():
    return "Bot is alive!"

def run():
    flask_app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()

# ================= RUN BOT =================
print("🐍 Bot started!")
app.run()
