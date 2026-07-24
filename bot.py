import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from supabase import create_client, Client

# ============ CONFIGURATION ============
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============ DATABASE FUNCTIONS ============
def get_clients(user_id):
    """Get all clients for a user"""
    try:
        result = supabase.table("clients")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("name")\
            .execute()
        return result.data if result.data else []
    except:
        return []

def add_client(user_id, name, amount):
    """Add or update a client"""
    try:
        # Check if client exists
        existing = supabase.table("clients")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("name", name)\
            .execute()
        
        if existing.data:
            # Update existing
            new_amount = existing.data[0]["amount"] + amount
            supabase.table("clients")\
                .update({"amount": new_amount, "updated_at": datetime.now().isoformat()})\
                .eq("id", existing.data[0]["id"])\
                .execute()
            return "updated", existing.data[0]["amount"], new_amount
        else:
            # Insert new
            supabase.table("clients").insert({
                "user_id": user_id,
                "name": name,
                "amount": amount,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            return "added", 0, amount
    except Exception as e:
        print(f"Error adding client: {e}")
        return "error", 0, 0

def remove_client(user_id, name):
    """Remove a client completely"""
    try:
        result = supabase.table("clients")\
            .delete()\
            .eq("user_id", user_id)\
            .eq("name", name)\
            .execute()
        return True if result.data else False
    except:
        return False

def mark_paid(user_id, name):
    """Mark a client as paid (set amount to 0)"""
    try:
        result = supabase.table("clients")\
            .update({"amount": 0, "updated_at": datetime.now().isoformat()})\
            .eq("user_id", user_id)\
            .eq("name", name)\
            .execute()
        return result.data if result.data else None
    except:
        return None

def get_total_pending(user_id):
    """Get total pending amount for a user"""
    try:
        result = supabase.table("clients")\
            .select("amount")\
            .eq("user_id", user_id)\
            .execute()
        total = sum(client["amount"] for client in result.data) if result.data else 0
        return total
    except:
        return 0

def delete_all_clients(user_id):
    """Delete all clients for a user"""
    try:
        supabase.table("clients").delete().eq("user_id", user_id).execute()
        return True
    except:
        return False

# ============ BOT COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
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
    """Show help message"""
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
    """Add or update a client"""
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 3:
        await update.message.reply_text(
            "❌ **Usage:** `/add [name] [amount]`\n\nExample: `/add John 5000`",
            parse_mode="Markdown"
        )
        return
    
    # Handle names with spaces
    amount = float(parts[-1])
    if amount <= 0:
        await update.message.reply_text("❌ Amount must be greater than 0.")
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
    """List all pending clients"""
    user_id = update.effective_user.id
    clients = get_clients(user_id)
    
    if not clients or all(c["amount"] == 0 for c in clients):
        await update.message.reply_text(
            "📭 **No pending clients**\n\nAll clients are paid up! 🎉",
            parse_mode="Markdown"
        )
        return
    
    # Filter out zero amount clients
    active_clients = [c for c in clients if c["amount"] > 0]
    
    if not active_clients:
        await update.message.reply_text(
            "📭 **No pending clients**\n\nAll clients are paid up! 🎉",
            parse_mode="Markdown"
        )
        return
    
    msg = "📋 **Pending Clients**\n\n"
    total = 0
    
    # Sort by amount (highest first)
    sorted_clients = sorted(active_clients, key=lambda x: x["amount"], reverse=True)
    
    for i, client in enumerate(sorted_clients, 1):
        msg += f"{i}. **{client['name']}**: ₹{client['amount']}\n"
        total += client["amount"]
    
    msg += f"\n━━━━━━━━━━━━━━━━━━━━━\n💰 **Total:** ₹{total}"
    msg += f"\n👤 **Clients:** {len(sorted_clients)}"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a client as paid"""
    user_id = update.effective_user.id
    parts = update.message.text.split(" ")
    
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ **Usage:** `/paid [name]`\n\nExample: `/paid John`",
            parse_mode="Markdown"
        )
        return
    
    name = " ".join(parts[1:])
    
    # Check if client exists
    clients = get_clients(user_id)
    client = next((c for c in clients if c["name"] == name), None)
    
    if not client:
        await update.message.reply_text(
            f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.",
            parse_mode="Markdown"
        )
        return
    
    if client["amount"] == 0:
        await update.message.reply_text(
            f"✅ **{name}** is already paid up! 🎉",
            parse_mode="Markdown"
        )
        return
    
    result = mark_paid(user_id, name)
    
    if result:
        await update.message.reply_text(
            f"✅ **{name}** marked as paid!\n\n"
            f"💳 ₹{client['amount']} cleared.\n"
            f"📊 **Remaining Total:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a reminder to a client"""
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
    client = next((c for c in clients if c["name"] == name), None)
    
    if not client:
        await update.message.reply_text(
            f"❌ Client **{name}** not found.\n\nUse `/list` to see all clients.",
            parse_mode="Markdown"
        )
        return
    
    if client["amount"] == 0:
        await update.message.reply_text(f"✅ **{name}** doesn't have any pending amount.")
        return
    
    reminder_msg = f"""🔔 **Reminder for {name}**

Hi {name}, this is a gentle reminder that ₹{client['amount']} is pending payment.

Please settle at your earliest convenience. Thank you! 🙏

━━━━━━━━━━━━━━━━━━━━━
📱 **From:** @Introspection007"""

    # Send confirmation to the user
    await update.message.reply_text(
        f"📤 **Reminder sent for {name}**\n\n"
        f"💳 Amount: ₹{client['amount']}",
        parse_mode="Markdown"
    )
    
    # Send the actual reminder (you can modify this to send to the client)
    # For now, it sends back to the same user as a preview
    await update.message.reply_text(reminder_msg, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show financial status"""
    user_id = update.effective_user.id
    clients = get_clients(user_id)
    active_clients = [c for c in clients if c["amount"] > 0]
    total = sum(c["amount"] for c in active_clients)
    
    msg = f"💰 **Financial Status**\n\n"
    msg += f"📊 **Total Pending:** ₹{total}\n"
    msg += f"👤 **Active Clients:** {len(active_clients)}\n"
    msg += f"📋 **Total Clients:** {len(clients)}\n\n"
    
    if active_clients:
        highest = sorted(active_clients, key=lambda x: x["amount"], reverse=True)[0]
        msg += f"🏆 **Highest:** {highest['name']} (₹{highest['amount']})"
    else:
        msg += f"🎉 **All clients paid up!**"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def delete_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a client completely"""
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
    client = next((c for c in clients if c["name"] == name), None)
    
    if not client:
        await update.message.reply_text(
            f"❌ Client **{name}** not found.",
            parse_mode="Markdown"
        )
        return
    
    amount = client["amount"]
    success = remove_client(user_id, name)
    
    if success:
        await update.message.reply_text(
            f"🗑️ **{name}** removed!\n\n"
            f"💳 ₹{amount} removed from pending.\n"
            f"📊 **Remaining Total:** ₹{get_total_pending(user_id)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all clients"""
    user_id = update.effective_user.id
    
    # Confirm deletion
    clients = get_clients(user_id)
    if not clients:
        await update.message.reply_text("📭 No clients to delete.")
        return
    
    # Create inline keyboard for confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete All", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"⚠️ **WARNING:** This will delete ALL {len(clients)} clients.\n\n"
        f"Total pending: ₹{sum(c['amount'] for c in clients)}\n\n"
        f"Are you sure?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "confirm_reset":
        delete_all_clients(user_id)
        await query.edit_message_text(
            "🗑️ **All clients deleted!**\n\n"
            "Your data has been cleared.",
            parse_mode="Markdown"
        )
    elif query.data == "cancel_reset":
        await query.edit_message_text(
            "✅ Reset cancelled. Your data is safe.",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any message not recognized as a command"""
    text = update.message.text
    if not text:
        return
    
    # Check if it's a command (starts with /)
    if text.startswith('/'):
        await update.message.reply_text(
            f"🤖 Unknown command: `{text}`\n\n"
            "Type `/help` to see all available commands.",
            parse_mode="Markdown"
        )
        return
    
    # Respond to non-command messages
    await update.message.reply_text(
        "🤖 I'm a credit tracker bot. Please use the following commands:\n\n"
        "/add [name] [amount] - Add a client\n"
        "/list - Show all clients\n"
        "/paid [name] - Mark as paid\n"
        "/help - Show all commands",
        parse_mode="Markdown"
    )

# ============ MAIN ============

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_client_command))
    app.add_handler(CommandHandler("list", list_clients))
    app.add_handler(CommandHandler("paid", paid_command))
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("delete", delete_client))
    app.add_handler(CommandHandler("reset", reset_command))
    
    # Add callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for non-command messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("✅ Credit Tracker Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
