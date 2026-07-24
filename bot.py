import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============ CONFIGURATION ============
BOT_TOKEN = "8958327625:AAE6B5kypZyXEFDaEx93FgT1nzyVR_6l_Fc"
SUPABASE_URL = "https://vqqkfongtzjjhiagmxcn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxcWtmb25ndHpqamhpYWdteGNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTg4NDAsImV4cCI6MjEwMDQ3NDg0MH0.44ZTRCPZdid_yccX2jlif6yDuntinIFi-e1psPgBdb8"

# ============ TELEGRAM SEND FUNCTION ============
def send_telegram(chat_id, text, parse_mode='Markdown'):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Send error: {e}")
        return None

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
            print(f"Supabase error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Supabase error: {e}")
        return None

def get_clients(user_id):
    params = {"user_id": f"eq.{user_id}", "order": "name.asc"}
    result = supabase_request("GET", "clients", params=params)
    return result if result else []

def add_client(user_id, name, amount):
    existing = get_clients(user_id)
    for client in existing:
        if client.get("name") == name:
            new_amount = client.get("amount", 0) + amount
            params = {"id": f"eq.{client['id']}"}
            data = {"amount": new_amount, "updated_at": datetime.now().isoformat()}
            supabase_request("PATCH", "clients", params=params, data=data)
            return "updated", client.get("amount", 0), new_amount
    
    data = {
        "user_id": user_id,
        "name": name,
        "amount": amount,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    supabase_request("POST", "clients", data=data)
    return "added", 0, amount

def remove_client(user_id, name):
    params = {"user_id": f"eq.{user_id}", "name": f"eq.{name}"}
    supabase_request("DELETE", "clients", params=params)
    return True

def mark_paid(user_id, name):
    existing = get_clients(user_id)
    for client in existing:
        if client.get("name") == name:
            params = {"id": f"eq.{client['id']}"}
            data = {"amount": 0, "updated_at": datetime.now().isoformat()}
            supabase_request("PATCH", "clients", params=params, data=data)
            return True
    return False

def get_total_pending(user_id):
    clients = get_clients(user_id)
    return sum(c.get("amount", 0) for c in clients)

def delete_all_clients(user_id):
    params = {"user_id": f"eq.{user_id}"}
    supabase_request("DELETE", "clients", params=params)
    return True

# ============ COMMAND HANDLERS ============
def handle_command(chat_id, text, user_id):
    parts = text.strip().split(" ")
    command = parts[0].lower()
    
    # /start
    if command == "/start":
        total = get_total_pending(user_id)
        clients = get_clients(user_id)
        welcome = f"""💰 **Credit Tracker Bot**

Welcome! I help you track client payments.

📊 **Current Status:**
• Total Pending: ₹{total}
• Active Clients: {len(clients)}

**Commands:**
/add [name] [amount] - Add client
/list - Show all clients
/paid [name] - Mark as paid
/remind [name] - Send reminder
/status - Show total
/delete [name] - Remove client
/reset - Delete ALL clients
/help - Show this menu

**Example:** `/add John 5000`

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
        send_telegram(chat_id, welcome)
        return
    
    # /help
    if command == "/help":
        help_text = """💰 **Credit Tracker Bot**

**Commands:**
/add [name] [amount] - Add client with pending payment
/list - Show all pending clients
/paid [name] - Mark client as paid
/remind [name] - Send payment reminder
/status - Show total pending
/delete [name] - Remove client
/reset - Delete ALL clients
/help - Show this menu

**Example:**
/add John 5000
/remind John

━━━━━━━━━━━━━━━━━━━━━
🤖 **Powered By @Introspection007**"""
        send_telegram(chat_id, help_text)
        return
    
    # /add
    if command == "/add":
        if len(parts) < 3:
            send_telegram(chat_id, "❌ **Usage:** `/add [name] [amount]`\n\nExample: `/add John 5000`")
            return
        
        try:
            amount = float(parts[-1])
            if amount <= 0:
                send_telegram(chat_id, "❌ Amount must be greater than 0.")
                return
        except:
            send_telegram(chat_id, "❌ Please enter a valid amount (e.g., 5000)")
            return
        
        name = " ".join(parts[1:-1])
        status, old_amount, new_amount = add_client(user_id, name, amount)
        
        if status == "added":
            send_telegram(chat_id, f"✅ **{name}** added with ₹{amount}\n\n💳 **Total:** ₹{new_amount}\n📊 **Overall Pending:** ₹{get_total_pending(user_id)}")
        elif status == "updated":
            send_telegram(chat_id, f"✅ **{name}** updated\n\n📈 ₹{old_amount} → ₹{new_amount}\n📊 **Overall Pending:** ₹{get_total_pending(user_id)}")
        else:
            send_telegram(chat_id, "❌ Something went wrong. Please try again.")
        return
    
    # /list
    if command == "/list":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        
        if not active_clients:
            send_telegram(chat_id, "📭 **No pending clients**\n\nAll clients are paid up! 🎉")
            return
        
        msg = "📋 **Pending Clients**\n\n"
        total = 0
        for i, client in enumerate(sorted(active_clients, key=lambda x: x.get("amount", 0), reverse=True), 1):
            msg += f"{i}. **{client.get('name', 'N/A')}**: ₹{client.get('amount', 0)}\n"
            total += client.get("amount", 0)
        
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n💰 **Total:** ₹{total}"
        msg += f"\n👤 **Clients:** {len(active_clients)}"
        send_telegram(chat_id, msg)
        return
    
    # /paid
    if command == "/paid":
        if len(parts) < 2:
            send_telegram(chat_id, "❌ **Usage:** `/paid [name]`\n\nExample: `/paid John`")
            return
        
        name = " ".join(parts[1:])
        clients = get_clients(user_id)
        client = next((c for c in clients if c.get("name") == name), None)
        
        if not client:
            send_telegram(chat_id, f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.")
            return
        
        if client.get("amount", 0) == 0:
            send_telegram(chat_id, f"✅ **{name}** is already paid up! 🎉")
            return
        
        if mark_paid(user_id, name):
            send_telegram(chat_id, f"✅ **{name}** marked as paid!\n\n💳 ₹{client.get('amount', 0)} cleared.\n📊 **Remaining Total:** ₹{get_total_pending(user_id)}")
        else:
            send_telegram(chat_id, "❌ Something went wrong. Please try again.")
        return
    
    # /remind
    if command == "/remind":
        if len(parts) < 2:
            send_telegram(chat_id, "❌ **Usage:** `/remind [name]`\n\nExample: `/remind John`")
            return
        
        name = " ".join(parts[1:])
        clients = get_clients(user_id)
        client = next((c for c in clients if c.get("name") == name), None)
        
        if not client:
            send_telegram(chat_id, f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.")
            return
        
        if client.get("amount", 0) == 0:
            send_telegram(chat_id, f"✅ **{name}** doesn't have any pending amount.")
            return
        
        reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount', 0)} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""
        
        send_telegram(chat_id, f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount', 0)}")
        send_telegram(chat_id, reminder_msg)
        return
    
    # /status
    if command == "/status":
        clients = get_clients(user_id)
        active_clients = [c for c in clients if c.get("amount", 0) > 0]
        total = sum(c.get("amount", 0) for c in active_clients)
        
        msg = f"💰 **Financial Status**\n\n"
        msg += f"📊 **Total Pending:** ₹{total}\n"
        msg += f"👤 **Active Clients:** {len(active_clients)}\n"
        msg += f"📋 **Total Clients:** {len(clients)}\n\n"
        
        if active_clients:
            highest = sorted(active_clients, key=lambda x: x.get("amount", 0), reverse=True)[0]
            msg += f"🏆 **Highest:** {highest.get('name', 'N/A')} (₹{highest.get('amount', 0)})"
        else:
            msg += f"🎉 **All clients paid up!**"
        
        send_telegram(chat_id, msg)
        return
    
    # /delete
    if command == "/delete":
        if len(parts) < 2:
            send_telegram(chat_id, "❌ **Usage:** `/delete [name]`\n\nExample: `/delete John`")
            return
        
        name = " ".join(parts[1:])
        clients = get_clients(user_id)
        client = next((c for c in clients if c.get("name") == name), None)
        
        if not client:
            send_telegram(chat_id, f"❌ Client **{name}** not found.")
            return
        
        amount = client.get("amount", 0)
        if remove_client(user_id, name):
            send_telegram(chat_id, f"🗑️ **{name}** removed!\n\n💳 ₹{amount} removed from pending.\n📊 **Remaining Total:** ₹{get_total_pending(user_id)}")
        else:
            send_telegram(chat_id, "❌ Something went wrong. Please try again.")
        return
    
    # /reset
    if command == "/reset":
        clients = get_clients(user_id)
        if not clients:
            send_telegram(chat_id, "📭 No clients to delete.")
            return
        
        delete_all_clients(user_id)
        send_telegram(chat_id, "🗑️ **All clients deleted!**\n\nYour data has been cleared.")
        return
    
    # Unknown command
    send_telegram(chat_id, f"🤖 Unknown command: `{text}`\n\nType `/help` to see all available commands.")

# ============ FLASK WEBHOOK ============
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        
        # Extract message
        message = data.get("message", {})
        if not message:
            return jsonify({"status": "ok"}), 200
        
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = message.get("from", {}).get("id")
        
        if not chat_id or not text:
            return jsonify({"status": "ok"}), 200
        
        # Handle the command
        handle_command(chat_id, text, user_id)
        
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
