import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============ CONFIGURATION ============
BOT_TOKEN = "8958327625:AAE6B5kypZyXEFDaEx93FgT1nzyVR_6l_Fc"

# Supabase Configuration
SUPABASE_URL = "https://vqqkfongtzjjhiagmxcn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxcWtmb25ndHpqamhpYWdteGNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTg4NDAsImV4cCI6MjEwMDQ3NDg0MH0.44ZTRCPZdid_yccX2jlif6yDuntinIFi-e1psPgBdb8"

# ============ SUPABASE FUNCTIONS ============
def add_client_supabase(name, amount):
    """Add client directly to Supabase using REST API"""
    url = f"{SUPABASE_URL}/rest/v1/clients"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = {"name": name, "amount": int(amount)}
    
    try:
        print(f"📤 Sending to Supabase: {data}")
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"📥 Response: {response.status_code} - {response.text}")
        
        if response.status_code in [200, 201]:
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def get_clients_supabase():
    """Get all clients from Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/clients"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    params = {"order": "name.asc"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def delete_client_supabase(name):
    """Delete a client from Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/clients?name=eq.{name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        return response.status_code in [200, 204]
    except:
        return False

def update_client_amount_supabase(name, amount):
    """Update client amount"""
    url = f"{SUPABASE_URL}/rest/v1/clients?name=eq.{name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {"amount": int(amount)}
    try:
        response = requests.patch(url, json=data, headers=headers, timeout=10)
        return response.status_code in [200, 204]
    except:
        return False

def delete_all_clients_supabase():
    """Delete ALL clients from Supabase using condition"""
    # Method 1: Delete with condition (name is not null)
    url = f"{SUPABASE_URL}/rest/v1/clients?name=neq.null"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.delete(url, headers=headers, timeout=10)
        print(f"🗑️ Delete all response: {response.status_code} - {response.text}")
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"❌ Delete all error: {e}")
        return False

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
    
    answer_callback(callback_id)

    if data == "add_client":
        send_menu(chat_id, "➕ **Add Client**\n\nSend the client name and amount like this:\n\n`John 5000`\n\n(Just type it as a message)")
        return

    elif data == "list_clients":
        clients = get_clients_supabase()
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
        clients = get_clients_supabase()
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
        clients = get_clients_supabase()
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
        clients = get_clients_supabase()
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
        if delete_all_clients_supabase():
            send_menu(chat_id, "🗑️ **All clients deleted successfully!**")
        else:
            send_menu(chat_id, "❌ Failed to delete all clients. Please try again.")
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
        clients = get_clients_supabase()
        client = next((c for c in clients if c.get("name") == name), None)
        if not client:
            send_menu(chat_id, f"❌ **{name}** not found.")
            return
        if update_client_amount_supabase(name, 0):
            send_menu(chat_id, f"✅ **{name}** marked as paid!\n\n📊 **Remaining Total:** ₹{sum(c.get('amount', 0) for c in get_clients_supabase())}")
        else:
            send_menu(chat_id, f"❌ Failed to mark {name} as paid.")
        return

    elif data.startswith("remind_"):
        name = data.replace("remind_", "")
        clients = get_clients_supabase()
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
        
        if not chat_id or not text:
            return jsonify({"status": "ok"}), 200
        
        print(f"📩 Message: {text}")
        
        if text == "/start":
            send_menu(chat_id)
            return jsonify({"status": "ok"}), 200
        
        if text == "/help":
            send_menu(chat_id, "💰 **Commands:**\n/add [name] [amount]\n/list\n/paid [name]\n/remind [name]\n/status\n/delete [name]\n/reset\n\nOr use the menu button!")
            return jsonify({"status": "ok"}), 200
        
        # Handle /add command
        if text.startswith("/add "):
            parts = text.split(" ")
            if len(parts) < 3:
                send_menu(chat_id, "❌ Usage: `/add [name] [amount]`")
                return jsonify({"status": "ok"}), 200
            try:
                amount = int(parts[-1])
                if amount <= 0:
                    send_menu(chat_id, "❌ Amount must be > 0")
                    return jsonify({"status": "ok"}), 200
            except:
                send_menu(chat_id, "❌ Invalid amount. Please enter a whole number like 5000")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:-1])
            if add_client_supabase(name, amount):
                send_menu(chat_id, f"✅ **{name}** added with ₹{amount}")
            else:
                send_menu(chat_id, "❌ Error adding client. Please try again.")
            return jsonify({"status": "ok"}), 200
        
        # Handle /list command
        if text == "/list":
            clients = get_clients_supabase()
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
        
        # Handle /status command
        if text == "/status":
            clients = get_clients_supabase()
            active = [c for c in clients if c.get("amount", 0) > 0]
            total = sum(c.get("amount", 0) for c in active)
            send_menu(chat_id, f"💰 **Status:**\n📊 Pending: ₹{total}\n👤 Active: {len(active)}\n📋 Total: {len(clients)}")
            return jsonify({"status": "ok"}), 200
        
        # Handle /paid command
        if text.startswith("/paid "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/paid [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if update_client_amount_supabase(name, 0):
                send_menu(chat_id, f"✅ **{name}** marked as paid!")
            else:
                send_menu(chat_id, f"❌ **{name}** not found or already paid")
            return jsonify({"status": "ok"}), 200
        
        # Handle /remind command
        if text.startswith("/remind "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/remind [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            clients = get_clients_supabase()
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
        
        # Handle /delete command
        if text.startswith("/delete "):
            parts = text.split(" ")
            if len(parts) < 2:
                send_menu(chat_id, "❌ Usage: `/delete [name]`")
                return jsonify({"status": "ok"}), 200
            name = " ".join(parts[1:])
            if delete_client_supabase(name):
                send_menu(chat_id, f"🗑️ **{name}** removed")
            else:
                send_menu(chat_id, f"❌ **{name}** not found")
            return jsonify({"status": "ok"}), 200
        
        # Handle /reset command
        if text == "/reset":
            if delete_all_clients_supabase():
                send_menu(chat_id, "🗑️ **All clients deleted successfully!**")
            else:
                send_menu(chat_id, "❌ Failed to delete all clients. Please try again.")
            return jsonify({"status": "ok"}), 200
        
        # If not a command, treat as "name amount"
        parts = text.split(" ")
        if len(parts) >= 2:
            try:
                amount = int(parts[-1])
                if amount > 0:
                    name = " ".join(parts[:-1])
                    if add_client_supabase(name, amount):
                        send_menu(chat_id, f"✅ **{name}** added with ₹{amount}")
                    else:
                        send_menu(chat_id, "❌ Error adding client. Please try again.")
                else:
                    send_menu(chat_id, "❌ Amount must be > 0")
            except:
                send_menu(chat_id, "❌ Enter: `[name] [amount]` (e.g., `John 5000`)")
        else:
            send_menu(chat_id, "❌ Enter: `[name] [amount]` (e.g., `John 5000`)")
        
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
