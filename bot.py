import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

# ============ FLASK APP ============
app = Flask(__name__)

# ============ CONFIGURATION ============
BOT_TOKEN = "8958327625:AAE6B5kypZyXEFDaEx93FgT1nzyVR_6l_Fc"

# SQLite Cloud Configuration
SQLITE_HOST = "ctv0adtedz.g6.sqlite.cloud"
SQLITE_PORT = "8860"
SQLITE_DB = "auth.sqlitecloud"
SQLITE_API_KEY = "LapaWymijCaGztdjyip2yyH62DgGHVWaj8mvQ1378WE"

# ============ SQLITE CLOUD HTTP API ============
def sqlitecloud_query(sql, params=None):
    """Execute a SQL query on SQLite Cloud via HTTP API"""
    url = f"https://{SQLITE_HOST}:{SQLITE_PORT}/api/v1/query"
    headers = {
        "Authorization": f"Bearer {SQLITE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "database": SQLITE_DB,
        "sql": sql,
        "params": params if params else []
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"SQLite Cloud error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"SQLite Cloud request error: {e}")
        return None

def init_database():
    """Create the clients table if it doesn't exist"""
    sql = """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """
    result = sqlitecloud_query(sql)
    if result is not None:
        print("✅ Database initialized!")
        return True
    print("❌ Database initialization failed!")
    return False

def get_clients(user_id):
    """Get all clients for a user"""
    sql = "SELECT * FROM clients WHERE user_id = ? ORDER BY name ASC"
    result = sqlitecloud_query(sql, [user_id])
    if result and "results" in result and len(result["results"]) > 0:
        rows = result["results"][0].get("rows", [])
        clients = []
        for row in rows:
            clients.append({
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "amount": row[3]
            })
        return clients
    return []

def add_client(user_id, name, amount):
    """Add or update a client"""
    # Check if client exists
    sql = "SELECT * FROM clients WHERE user_id = ? AND name = ?"
    result = sqlitecloud_query(sql, [user_id, name])
    if result and "results" in result and len(result["results"]) > 0:
        rows = result["results"][0].get("rows", [])
        if rows:
            old_amount = rows[0][3]
            new_amount = old_amount + amount
            sql = "UPDATE clients SET amount = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            sqlitecloud_query(sql, [new_amount, rows[0][0]])
            return "updated", old_amount, new_amount
    
    # Add new client
    sql = "INSERT INTO clients (user_id, name, amount) VALUES (?, ?, ?)"
    result = sqlitecloud_query(sql, [user_id, name, amount])
    if result is not None:
        return "added", 0, amount
    return "error", 0, 0

def mark_paid(user_id, name):
    """Mark a client as paid"""
    sql = "UPDATE clients SET amount = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ? AND name = ?"
    result = sqlitecloud_query(sql, [user_id, name])
    return result is not None

def remove_client(user_id, name):
    """Remove a client completely"""
    sql = "DELETE FROM clients WHERE user_id = ? AND name = ?"
    result = sqlitecloud_query(sql, [user_id, name])
    return result is not None

def get_total_pending(user_id):
    clients = get_clients(user_id)
    return sum(c.get("amount", 0) for c in clients)

def delete_all_clients(user_id):
    sql = "DELETE FROM clients WHERE user_id = ?"
    result = sqlitecloud_query(sql, [user_id])
    return result is not None

# ============ TELEGRAM FUNCTIONS ============
def send_telegram(chat_id, text, parse_mode='Markdown', reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def send_menu(chat_id, text=None):
    keyboard = {
        "inline_keyboard": [
            [{"text": "➕ Add Client", "callback_data": "add_client"}],
            [{"text": "📋 List Clients", "callback_data": "list_clients"}],
            [{"text": "✅ Mark Paid", "callback_data": "mark_paid"}],
            [{"text": "🔔 Send Reminder", "callback_data": "send_reminder"}],
            [{"text": "💰 Status", "callback_data": "status"}],
            [{"text": "🗑️ Reset All", "callback_data": "reset_all"}],
            [{"text": "❓ Help", "callback_data": "help"}]
        ]
    }
    if not text:
        text = f"""💰 **Credit Tracker Bot**

Tap a button below to manage your clients.

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
    send_telegram(chat_id, text, reply_markup=json.dumps(keyboard))

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id}, timeout=5)
    except:
        pass

# ============ CALLBACK HANDLERS ============
def handle_callback(callback_query):
    callback_id = callback_query.get("id")
    data = callback_query.get("data")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    user_id = callback_query.get("from", {}).get("id")
    
    answer_callback(callback_id)

    if data == "add_client":
        send_menu(chat_id, "➕ **Add Client**\n\nSend the client name and amount like this:\n\n`John 5000`\n\n(Just type it as a message)")
        return

    elif data == "list_clients":
        clients = get_clients(user_id)
        active = [c for c in clients if c.get("amount", 0) > 0]
        if not active:
            send_menu(chat_id, "📭 **No pending clients!**")
            return
        msg = "📋 **Pending Clients**\n\n"
        total = 0
        for i, c in enumerate(sorted(active, key=lambda x: x.get("amount", 0), reverse=True), 1):
            msg += f"{i}. **{c.get('name')}**: ₹{c.get('amount')}\n"
            total += c.get("amount", 0)
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n💰 **Total:** ₹{total}\n👤 **Clients:** {len(active)}"
        send_menu(chat_id, msg)
        return

    elif data == "mark_paid":
        clients = get_clients(user_id)
        active = [c for c in clients if c.get("amount", 0) > 0]
        if not active:
            send_menu(chat_id, "📭 No pending clients to mark as paid.")
            return
        keyboard = {"inline_keyboard": []}
        for c in active:
            keyboard["inline_keyboard"].append([
                {"text": f"✅ {c.get('name')} (₹{c.get('amount')})", 
                 "callback_data": f"paid_{c.get('name')}"}
            ])
        keyboard["inline_keyboard"].append([{"text": "🔙 Back to Menu", "callback_data": "menu"}])
        send_telegram(chat_id, "✅ **Select a client to mark as paid:**", reply_markup=json.dumps(keyboard))
        return

    elif data == "send_reminder":
        clients = get_clients(user_id)
        active = [c for c in clients if c.get("amount", 0) > 0]
        if not active:
            send_menu(chat_id, "📭 No clients to remind.")
            return
        keyboard = {"inline_keyboard": []}
        for c in active:
            keyboard["inline_keyboard"].append([
                {"text": f"🔔 {c.get('name')} (₹{c.get('amount')})", 
                 "callback_data": f"remind_{c.get('name')}"}
            ])
        keyboard["inline_keyboard"].append([{"text": "🔙 Back to Menu", "callback_data": "menu"}])
        send_telegram(chat_id, "🔔 **Select a client to remind:**", reply_markup=json.dumps(keyboard))
        return

    elif data == "status":
        clients = get_clients(user_id)
        active = [c for c in clients if c.get("amount", 0) > 0]
        total = sum(c.get("amount", 0) for c in active)
        msg = f"💰 **Financial Status**\n\n"
        msg += f"📊 **Total Pending:** ₹{total}\n"
        msg += f"👤 **Active Clients:** {len(active)}\n"
        msg += f"📋 **Total Clients:** {len(clients)}"
        if active:
            highest = sorted(active, key=lambda x: x.get("amount", 0), reverse=True)[0]
            msg += f"\n\n🏆 **Highest:** {highest.get('name')} (₹{highest.get('amount')})"
        else:
            msg += f"\n\n🎉 All clients paid up!"
        send_menu(chat_id, msg)
        return

    elif data == "reset_all":
        keyboard = {"inline_keyboard": [
            [{"text": "✅ Yes, Delete All", "callback_data": "confirm_reset"}],
            [{"text": "❌ Cancel", "callback_data": "menu"}]
        ]}
        send_telegram(chat_id, "⚠️ **WARNING:** This will delete ALL clients.\n\nAre you sure?", reply_markup=json.dumps(keyboard))
        return

    elif data == "confirm_reset":
        delete_all_clients(user_id)
        send_menu(chat_id, "🗑️ **All clients deleted!**")
        return

    elif data == "help":
        help_text = """💰 **Credit Tracker Bot**

**Commands:**
/add [name] [amount] - Add client
/list - Show all clients
/paid [name] - Mark as paid
/remind [name] - Send reminder
/status - Show total
/delete [name] - Remove client
/reset - Delete ALL clients

**OR use the menu buttons below!**

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
        send_menu(chat_id, help_text)
        return

    elif data == "menu":
        send_menu(chat_id)
        return

    elif data.startswith("paid_"):
        name = data.replace("paid_", "")
        if mark_paid(user_id, name):
            send_menu(chat_id, f"✅ **{name}** marked as paid!\n\n📊 **Remaining Total:** ₹{get_total_pending(user_id)}")
        else:
            send_menu(chat_id, f"❌ **{name}** not found or already paid.")
        return

    elif data.startswith("remind_"):
        name = data.replace("remind_", "")
        clients = get_clients(user_id)
        client = next((c for c in clients if c.get("name") == name), None)
        if not client:
            send_menu(chat_id, f"❌ **{name}** not found.")
            return
        if client.get("amount", 0) == 0:
            send_menu(chat_id, f"✅ **{name}** has no pending amount.")
            return
        reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount')} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""
        send_telegram(chat_id, reminder_msg)
        send_menu(chat_id, f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount')}")
        return

# ============ FLASK WEBHOOK ============
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        
        if "callback_query" in data:
            handle_callback(data["callback_query"])
            return jsonify({"status": "ok"}), 200
        
        message = data.get("message", {})
        if not message:
            return jsonify({"status": "ok"}), 200
        
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = message.get("from", {}).get("id")
        
        if not chat_id or not text:
            return jsonify({"status": "ok"}), 200
        
        if text == "/start":
            send_menu(chat_id)
            return jsonify({"status": "ok"}), 200
        
        if text == "/help":
            send_menu(chat_id, "💰 **Commands:**\n/add [name] [amount]\n/list\n/paid [name]\n/remind [name]\n/status\n/delete [name]\n/reset\n\nOr use the menu button!")
            return jsonify({"status": "ok"}), 200
        
        if text.startswith("/add "):
            parts = text.split(" ")
            if len(parts) < 3:
                send_menu(chat_id, "❌ Usage: `/add [name] [amount]`")
                return jsonify({"status": "ok"}), 200
            try:
                amount = float(parts[-1])
                if amount <= 0:
                    send_menu(chat_id, "❌ Amount must be > 0")
                    return jsonify({"status": "ok"}), 200
            except:
                send_menu(chat_id, "❌ Invalid amount")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:-1])
            status, old, new = add_client(user_id, name, amount)
            if status == "added":
                send_menu(chat_id, f"✅ **{name}** added with ₹{amount}")
            elif status == "updated":
                send_menu(chat_id, f"✅ **{name}** updated\n📈 ₹{old} → ₹{new}")
            else:
                send_menu(chat_id, "❌ Error adding client")
            return jsonify({"status": "ok"}), 200
        
        if text == "/list":
            clients = get_clients(user_id)
            active = [c for c in clients if c.get("amount", 0) > 0]
            if not active:
                send_menu(chat_id, "📭 **No pending clients!**")
                return jsonify({"status": "ok"}), 200
            msg = "📋 **Pending Clients**\n\n"
            total = 0
            for i, c in enumerate(sorted(active, key=lambda x: x.get("amount", 0), reverse=True), 1):
                msg += f"{i}. **{c['name']}**: ₹{c['amount']}\n"
                total += c['amount']
            msg += f"\n💰 **Total:** ₹{total}"
            send_menu(chat_id, msg)
            return jsonify({"status": "ok"}), 200
        
        if text == "/status":
            clients = get_clients(user_id)
            active = [c for c in clients if c.get("amount", 0) > 0]
            total = sum(c.get("amount", 0) for c in active)
            send_menu(chat_id, f"💰 **Status:**\n📊 Pending: ₹{total}\n👤 Active: {len(active)}\n📋 Total: {len(clients)}")
            return jsonify({"status": "ok"}), 200
        
        if text.startswith("/paid "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/paid [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if mark_paid(user_id, name):
                send_menu(chat_id, f"✅ **{name}** marked as paid!")
            else:
                send_menu(chat_id, f"❌ **{name}** not found or already paid")
            return jsonify({"status": "ok"}), 200
        
        if text.startswith("/remind "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/remind [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            clients = get_clients(user_id)
            client = next((c for c in clients if c.get("name") == name), None)
            if not client:
                send_menu(chat_id, f"❌ **{name}** not found")
                return jsonify({"status": "ok"}), 200
            if client.get("amount", 0) == 0:
                send_menu(chat_id, f"✅ **{name}** has no pending amount")
                return jsonify({"status": "ok"}), 200
            reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount')} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""
            send_telegram(chat_id, reminder_msg)
            send_menu(chat_id, f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount')}")
            return jsonify({"status": "ok"}), 200
        
        if text.startswith("/delete "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/delete [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if remove_client(user_id, name):
                send_menu(chat_id, f"🗑️ **{name}** removed")
            else:
                send_menu(chat_id, f"❌ **{name}** not found")
            return jsonify({"status": "ok"}), 200
        
        if text == "/reset":
            delete_all_clients(user_id)
            send_menu(chat_id, "🗑️ **All clients deleted!**")
            return jsonify({"status": "ok"}), 200
        
        # If not a command, treat as "name amount"
        parts = text.split(" ")
        if len(parts) >= 2:
            try:
                amount = float(parts[-1])
                if amount > 0:
                    name = " ".join(parts[:-1])
                    status, old, new = add_client(user_id, name, amount)
                    if status == "added":
                        send_menu(chat_id, f"✅ **{name}** added with ₹{amount}")
                    elif status == "updated":
                        send_menu(chat_id, f"✅ **{name}** updated\n📈 ₹{old} → ₹{new}")
                    else:
                        send_menu(chat_id, "❌ Error adding client")
                else:
                    send_menu(chat_id, "❌ Amount must be > 0")
            except:
                send_menu(chat_id, "❌ Enter: `[name] [amount]`")
        else:
            send_menu(chat_id, "❌ Enter: `[name] [amount]`")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error"}), 500

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "Credit Tracker Bot is running!",
        "creator": "@Introspection007"
    })

# ============ INITIALIZE DATABASE ============
init_database()

if __name__ == "__main__":
    app.run()
