import os
import json
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

app = Flask(__name__)

# ============ CONFIGURATION ============
BOT_TOKEN = "8958327625:AAE6B5kypZyXEFDaEx93FgT1nzyVR_6l_Fc"
SUPABASE_URL = "https://vqqkfongtzjjhiagmxcn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZxcWtmb25ndHpqamhpYWdteGNuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTg4NDAsImV4cCI6MjEwMDQ3NDg0MH0.44ZTRCPZdid_yccX2jlif6yDuntinIFi-e1psPgBdb8"

# ============ SUPABASE HTTP FUNCTIONS ============
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
            print(f"Supabase HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Supabase request error: {e}")
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

# ============ TELEGRAM BOT SETUP ============
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ============ BOT COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def add_client_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ **Usage:** `/add [name] [amount]`\n\nExample: `/add John 5000`",
            parse_mode="Markdown"
        )
        return
    
    try:
        amount = float(parts[-1])
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be greater than 0.")
            return
    except:
        await update.message.reply_text("❌ Please enter a valid amount (e.g., 5000)")
        return
    
    name = " ".join(parts[1:-1])
    status, old_amount, new_amount = add_client(user_id, name, amount)
    
    if status == "added":
        await update.message.reply_text(
            f"✅ **{name}** added with ₹{amount}\n\n"
            f"💳 **Total:** ₹{new_amount}\n"
            f"📊 **Overall Pending:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    elif status == "updated":
        await update.message.reply_text(
            f"✅ **{name}** updated\n\n"
            f"📈 ₹{old_amount} → ₹{new_amount}\n"
            f"📊 **Overall Pending:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def list_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clients = get_clients(user_id)
    active_clients = [c for c in clients if c.get("amount", 0) > 0]
    
    if not active_clients:
        await update.message.reply_text(
            "📭 **No pending clients**\n\nAll clients are paid up! 🎉",
            parse_mode="Markdown"
        )
        return
    
    msg = "📋 **Pending Clients**\n\n"
    total = 0
    for i, client in enumerate(sorted(active_clients, key=lambda x: x.get("amount", 0), reverse=True), 1):
        msg += f"{i}. **{client.get('name', 'N/A')}**: ₹{client.get('amount', 0)}\n"
        total += client.get("amount", 0)
    
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n💰 **Total:** ₹{total}"
    msg += f"\n👤 **Clients:** {len(active_clients)}"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/paid [name]`\n\nExample: `/paid John`",
            parse_mode="Markdown"
        )
        return
    
    name = " ".join(parts[1:])
    clients = get_clients(user_id)
    client = next((c for c in clients if c.get("name") == name), None)
    
    if not client:
        await update.message.reply_text(
            f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.",
            parse_mode="Markdown"
        )
        return
    
    if client.get("amount", 0) == 0:
        await update.message.reply_text(
            f"✅ **{name}** is already paid up! 🎉",
            parse_mode="Markdown"
        )
        return
    
    if mark_paid(user_id, name):
        await update.message.reply_text(
            f"✅ **{name}** marked as paid!\n\n"
            f"💳 ₹{client.get('amount', 0)} cleared.\n"
            f"📊 **Remaining Total:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/remind [name]`\n\nExample: `/remind John`",
            parse_mode="Markdown"
        )
        return
    
    name = " ".join(parts[1:])
    clients = get_clients(user_id)
    client = next((c for c in clients if c.get("name") == name), None)
    
    if not client:
        await update.message.reply_text(
            f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.",
            parse_mode="Markdown"
        )
        return
    
    if client.get("amount", 0) == 0:
        await update.message.reply_text(f"✅ **{name}** doesn't have any pending amount.")
        return
    
    reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client.get('amount', 0)} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""

    await update.message.reply_text(
        f"📤 **Reminder sent for {name}**\n\n💳 Amount: ₹{client.get('amount', 0)}",
        parse_mode="Markdown"
    )
    await update.message.reply_text(reminder_msg, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def delete_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/delete [name]`\n\nExample: `/delete John`",
            parse_mode="Markdown"
        )
        return
    
    name = " ".join(parts[1:])
    clients = get_clients(user_id)
    client = next((c for c in clients if c.get("name") == name), None)
    
    if not client:
        await update.message.reply_text(f"❌ Client **{name}** not found.", parse_mode="Markdown")
        return
    
    amount = client.get("amount", 0)
    if remove_client(user_id, name):
        await update.message.reply_text(
            f"🗑️ **{name}** removed!\n\n"
            f"💳 ₹{amount} removed from pending.\n"
            f"📊 **Remaining Total:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clients = get_clients(user_id)
    
    if not clients:
        await update.message.reply_text("📭 No clients to delete.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete All", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ **WARNING:** This will delete ALL {len(clients)} clients.\n\n"
        f"Total pending: ₹{sum(c.get('amount', 0) for c in clients)}\n\n"
        f"Are you sure?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == "confirm_reset":
        delete_all_clients(user_id)
        await query.edit_message_text(
            "🗑️ **All clients deleted!**\n\nYour data has been cleared.",
            parse_mode="Markdown"
        )
    elif query.data == "cancel_reset":
        await query.edit_message_text(
            "✅ Reset cancelled. Your data is safe.",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    
    if text.startswith('/'):
        await update.message.reply_text(
            f"🤖 Unknown command: `{text}`\n\nType `/help` to see all available commands.",
            parse_mode="Markdown"
        )
        return
    
    await update.message.reply_text(
        "🤖 I'm a credit tracker bot. Please use the following commands:\n\n"
        "/add [name] [amount] - Add a client\n"
        "/list - Show all clients\n"
        "/paid [name] - Mark as paid\n"
        "/help - Show all commands",
        parse_mode="Markdown"
    )

# ============ CREATE APPLICATION ============
telegram_app = Application.builder().token(BOT_TOKEN).build()

# Register all handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("add", add_client_command))
telegram_app.add_handler(CommandHandler("list", list_clients))
telegram_app.add_handler(CommandHandler("paid", paid_command))
telegram_app.add_handler(CommandHandler("remind", remind_command))
telegram_app.add_handler(CommandHandler("status", status_command))
telegram_app.add_handler(CommandHandler("delete", delete_client))
telegram_app.add_handler(CommandHandler("reset", reset_command))
telegram_app.add_handler(CallbackQueryHandler(button_callback))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ============ FLASK WEBHOOK ROUTE ============
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, telegram_app.bot)
        # Use a synchronous process_update method
        telegram_app.process_update(update)
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

# ============ SETUP WEBHOOK ============
def set_webhook():
    vercel_url = os.environ.get("VERCEL_URL")
    if vercel_url:
        webhook_url = f"https://{vercel_url}/webhook/{BOT_TOKEN}"
        try:
            # Set webhook synchronously
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_app.bot.set_webhook(url=webhook_url))
            loop.close()
            print(f"✅ Webhook set to: {webhook_url}")
        except Exception as e:
            print(f"Webhook error: {e}")

if os.environ.get("VERCEL"):
    set_webhook()

if __name__ == "__main__":
    app.run()
