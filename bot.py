import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

# ============ FLASK APP ============
app = Flask(__name__)

# ============ CONFIGURATION ============
BOT_TOKEN = "8958327625:AAE6B5kypZyXEFDaEx93FgT1nzyVR_6l_Fc"
SUPABASE_URL = "https://vqqkfongtzjjhiagmxcn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxcWtmb25ndHpqamhpYWdteGNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTg4NDAsImV4cCI6MjEwMDQ3NDg0MH0.44ZTRCPZdid_yccX2jlif6yDuntinIFi-e1psPgBdb8"

# ============ TELEGRAM FUNCTIONS ============
def send_telegram(chat_id, text, parse_mode='Markdown', reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Send error: {e}")
        return None

def send_menu(chat_id):
    """Send the main menu with buttons"""
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
    welcome = f"""💰 **Credit Tracker Bot**

Tap a button below to manage your clients.

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
    send_telegram(chat_id, welcome, reply_markup=json.dumps(keyboard))

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Edit error: {e}")

def answer_callback(callback_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id}, timeout=5)
    except:
        pass

# ============ SUPABASE FUNCTIONS ============
def supabase_request(method, table, params=None, data=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, params=params, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params, timeout=10)
        else:
            return None
        if response.status_code in [200, 201, 204]:
            return response.json() if response.text else []
        else:
            print(f"Supabase error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Supabase error: {e}")
        return None

def get_clients(user_id):
    """Get all clients for a user"""
    print(f"📊 Fetching clients for user_id: {user_id}")
    params = {"user_id": f"eq.{user_id}", "order": "name.asc"}
    result = supabase_request("GET", "clients", params=params)
    print(f"📊 Found {len(result) if result else 0} clients")
    return result if result else []

def add_client(user_id, name, amount):
    """Add or update a client"""
    print(f"➕ Adding client: user_id={user_id}, name={name}, amount={amount}")
    
    # Check if client exists
    existing = get_clients(user_id)
    for client in existing:
        if client.get("name").lower() == name.lower():
            new_amount = client.get("amount", 0) + amount
            params = {"id": f"eq.{client['id']}"}
            data = {"amount": new_amount, "updated_at": datetime.now().isoformat()}
            supabase_request("PATCH", "clients", params=params, data=data)
            return "updated", client.get("amount", 0), new_amount
    
    # Add new client
    data = {
        "user_id": user_id,
        "name": name,
        "amount": amount,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    result = supabase_request("POST", "clients", data=data)
    print(f"➕ Add result: {result}")
    return "added", 0, amount

def mark_paid(user_id, name):
    clients = get_clients(user_id)
    for client in clients:
        if client.get("name").lower() == name.lower():
            params = {"id": f"eq.{client['id']}"}
            data = {"amount": 0, "updated_at": datetime.now().isoformat()}
            supabase_request("PATCH", "clients", params=params, data=data)
            return True
    return False

def remove_client(user_id, name):
    params = {"user_id": f"eq.{user_id}", "name": f"eq.{name}"}
    supabase_request("DELETE", "clients", params=params)
    return True

def get_total_pending(user_id):
    clients = get_clients(user_id)
    return sum(c.get("amount", 0) for c in clients)

def delete_all_clients(user_id):
    params = {"user_id": f"eq.{user_id}"}
    supabase_request("DELETE", "clients", params=params)
    return True

# ============ CALLBACK HANDLERS ============
def handle_callback(callback_query):
    callback_id = callback_query.get("id")
    data = callback_query.get("data")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    user_id = callback_query.get("from", {}).get("id")
    
    answer_callback(callback_id)

    if data == "add_client":
        edit_message(chat_id, message_id, 
            "➕ **Add Client**\n\nSend the client name and amount like this:\n\n`John 5000`\n\n(Just type it as a message)")
        return

    elif data == "list_clients":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        if not active_clients:
            edit_message(chat_id, message_id, "📭 **No pending clients!**")
            return
        msg = "📋 **Pending Clients**\n\n"
        total = 0
        for i, client in enumerate(sorted(active_clients, key=lambda x: x.get("amount", 0), reverse=True), 1):
            msg += f"{i}. **{client.get('name')}**: ₹{client.get('amount')}\n"
            total += client.get("amount", 0)
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n💰 **Total:** ₹{total}\n👤 **Clients:** {len(active_clients)}"
        edit_message(chat_id, message_id, msg)
        return

    elif data == "mark_paid":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        if not active_clients:
            edit_message(chat_id, message_id, "📭 No pending clients to mark as paid.")
            return
        keyboard = {"inline_keyboard": []}
        for client in active_clients:
            keyboard["inline_keyboard"].append([
                {"text": f"✅ {client.get('name')} (₹{client.get('amount')})", 
                 "callback_data": f"paid_{client.get('name')}"}
            ])
        keyboard["inline_keyboard"].append([{"text": "🔙 Back to Menu", "callback_data": "menu"}])
        edit_message(chat_id, message_id, "✅ **Select a client to mark as paid:**", reply_markup=json.dumps(keyboard))
        return

    elif data == "send_reminder":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        if not active_clients:
            edit_message(chat_id, message_id, "📭 No clients to remind.")
            return
        keyboard = {"inline_keyboard": []}
        for client in active_clients:
            keyboard["inline_keyboard"].append([
                {"text": f"🔔 {client.get('name')} (₹{client.get('amount')})", 
                 "callback_data": f"remind_{client.get('name')}"}
            ])
        keyboard["inline_keyboard"].append([{"text": "🔙 Back to Menu", "callback_data": "menu"}])
        edit_message(chat_id, message_id, "🔔 **Select a client to remind:**", reply_markup=json.dumps(keyboard))
        return

    elif data == "status":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        total = sum(c.get("amount", 0) for c in active_clients)
        msg = f"💰 **Financial Status**\n\n"
        msg += f"📊 **Total Pending:** ₹{total}\n"
        msg += f"👤 **Active Clients:** {len(active_clients)}\n"
        msg += f"📋 **Total Clients:** {len(clients)}"
        if active_clients:
            highest = sorted(active_clients, key=lambda x: x.get("amount", 0), reverse=True)[0]
            msg += f"\n\n🏆 **Highest:** {highest.get('name')} (₹{highest.get('amount')})"
        else:
            msg += f"\n\n🎉 All clients paid up!"
        edit_message(chat_id, message_id, msg)
        return

    elif data == "reset_all":
        keyboard = {"inline_keyboard": [
            [{"text": "✅ Yes, Delete All", "callback_data": "confirm_reset"}],
            [{"text": "❌ Cancel", "callback_data": "menu"}]
        ]}
        edit_message(chat_id, message_id, "⚠️ **WARNING:** This will delete ALL clients.\n\nAre you sure?", reply_markup=json.dumps(keyboard))
        return

    elif data == "confirm_reset":
        delete_all_clients(user_id)
        edit_message(chat_id, message_id, "🗑️ **All clients deleted!**")
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

**OR use the menu buttons!**

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
        edit_message(chat_id, message_id, help_text)
        return

    elif data == "menu":
        send_menu(chat_id)
        return

    elif data.startswith("paid_"):
        name = data.replace("paid_", "")
        if mark_paid(user_id, name):
            clients = get_clients(user_id)
            client = next((c for c in clients if c.get("name").lower() == name.lower()), None)
            amount = client.get("amount", 0) if client else 0
            edit_message(chat_id, message_id, f"✅ **{name}** marked as paid!\n\n💳 ₹{amount} cleared.\n📊 **Remaining Total:** ₹{get_total_pending(user_id)}")
        else:
            edit_message(chat_id, message_id, f"❌ Client **{name}** not found or already paid.")
        return

    elif data.startswith("remind_"):
        name = data.replace("remind_", "")
        clients = get_clients(user_id)
        client = next((c for c in clients if c.get("name").lower() == name.lower()), None)
        if not client:
            edit_message(chat_id, message_id, f"❌ Client **{name}** not found.")
            return
        if client.get("amount", 0) == 0:
            edit_message(chat_id, message_id, f"✅ **{name}** has no pending amount.")
            return
        reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount')} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""
        edit_message(chat_id, message_id, f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount')}")
        send_telegram(chat_id, reminder_msg)
        return

# ============ FLASK WEBHOOK ============
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        
        # Handle button clicks
        if "callback_query" in data:
            handle_callback(data["callback_query"])
            return jsonify({"status": "ok"}), 200
        
        # Handle text messages
        message = data.get("message", {})
        if not message:
            return jsonify({"status": "ok"}), 200
        
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = message.get("from", {}).get("id")
        
        if not chat_id or not text:
            return jsonify({"status": "ok"}), 200
        
        print(f"📩 Message from user {user_id}: {text}")
        
        # Commands
        if text == "/start":
            send_menu(chat_id)
            return jsonify({"status": "ok"}), 200
        
        if text == "/help":
            send_telegram(chat_id, "💰 **Commands:**\n/add [name] [amount]\n/list\n/paid [name]\n/remind [name]\n/status\n/delete [name]\n/reset\n\nOr use the menu button!")
            return jsonify({"status": "ok"}), 200
        
        # /add command
        if text.startswith("/add "):
            parts = text.split(" ")
            if len(parts) < 3:
                send_telegram(chat_id, "❌ Usage: `/add [name] [amount]`")
                return jsonify({"status": "ok"}), 200
            try:
                amount = float(parts[-1])
                if amount <= 0:
                    send_telegram(chat_id, "❌ Amount must be > 0")
                    return jsonify({"status": "ok"}), 200
            except:
                send_telegram(chat_id, "❌ Invalid amount")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:-1])
            status, old, new = add_client(user_id, name, amount)
            if status == "added":
                send_telegram(chat_id, f"✅ **{name}** added with ₹{amount}\n\n💳 **Total:** ₹{new}")
            elif status == "updated":
                send_telegram(chat_id, f"✅ **{name}** updated\n\n📈 ₹{old} → ₹{new}")
            else:
                send_telegram(chat_id, "❌ Error adding client")
            # Show menu after adding
            send_menu(chat_id)
            return jsonify({"status": "ok"}), 200
        
        # /list command
        if text == "/list":
            clients = get_clients(user_id)
            active = [c for c in clients if c.get("amount", 0) > 0]
            if not active:
                send_telegram(chat_id, "📭 **No pending clients!**")
                return jsonify({"status": "ok"}), 200
            msg = "📋 **Pending Clients**\n\n"
            total = 0
            for i, c in enumerate(sorted(active, key=lambda x: x.get("amount", 0), reverse=True), 1):
                msg += f"{i}. **{c['name']}**: ₹{c['amount']}\n"
                total += c['amount']
            msg += f"\n💰 **Total:** ₹{total}"
            send_telegram(chat_id, msg)
            return jsonify({"status": "ok"}), 200
        
        # /status command
        if text == "/status":
            clients = get_clients(user_id)
            active = [c for c in clients if c.get("amount", 0) > 0]
            total = sum(c.get("amount", 0) for c in active)
            send_telegram(chat_id, f"💰 **Status:**\n📊 Pending: ₹{total}\n👤 Active: {len(active)}\n📋 Total: {len(clients)}")
            return jsonify({"status": "ok"}), 200
        
        # /paid command
        if text.startswith("/paid "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_telegram(chat_id, "❌ Usage: `/paid [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if mark_paid(user_id, name):
                send_telegram(chat_id, f"✅ **{name}** marked as paid!")
            else:
                send_telegram(chat_id, f"❌ **{name}** not found or already paid")
            return jsonify({"status": "ok"}), 200
        
        # /remind command
        if text.startswith("/remind "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_telegram(chat_id, "❌ Usage: `/remind [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            clients = get_clients(user_id)
            client = next((c for c in clients if c.get("name").lower() == name.lower()), None)
            if not client:
                send_telegram(chat_id, f"❌ **{name}** not found")
                return jsonify({"status": "ok"}), 200
            if client.get("amount", 0) == 0:
                send_telegram(chat_id, f"✅ **{name}** has no pending amount")
                return jsonify({"status": "ok"}), 200
            reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount')} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""
            send_telegram(chat_id, f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount')}")
            send_telegram(chat_id, reminder_msg)
            return jsonify({"status": "ok"}), 200
        
        # /delete command
        if text.startswith("/delete "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_telegram(chat_id, "❌ Usage: `/delete [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if remove_client(user_id, name):
                send_telegram(chat_id, f"🗑️ **{name}** removed")
            else:
                send_telegram(chat_id, f"❌ **{name}** not found")
            return jsonify({"status": "ok"}), 200
        
        # /reset command
        if text == "/reset":
            delete_all_clients(user_id)
            send_telegram(chat_id, "🗑️ **All clients deleted!**")
            return jsonify({"status": "ok"}), 200
        
        # If not a command, treat as "name amount" input
        parts = text.split(" ")
        if len(parts) >= 2:
            try:
                amount = float(parts[-1])
                if amount > 0:
                    name = " ".join(parts[:-1])
                    status, old, new = add_client(user_id, name, amount)
                    if status == "added":
                        send_telegram(chat_id, f"✅ **{name}** added with ₹{amount}\n\n💳 **Total:** ₹{new}")
                    elif status == "updated":
                        send_telegram(chat_id, f"✅ **{name}** updated\n\n📈 ₹{old} → ₹{new}")
                    # Show menu after adding
                    send_menu(chat_id)
                else:
                    send_telegram(chat_id, "❌ Amount must be > 0")
            except:
                send_telegram(chat_id, "❌ Enter: `[name] [amount]`")
        else:
            send_telegram(chat_id, "❌ Enter: `[name] [amount]`")
        
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

if __name__ == "__main__":
    app.run()
