import random
import string
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import time
import nest_asyncio
import sqlite3
from datetime import datetime

# Apply nest_asyncio
nest_asyncio.apply()

# Owner ID and user data
OWNER_ID = 5855843544  # Replace with your Telegram ID
AUTHORIZED_USERS = [OWNER_ID]  # Authorized users
USER_DATA = {}  # User data dictionary
REDEEM_CODES = {}  # Redeem codes dictionary
START_TIME = time.time()  # Bot start time

# Helper function: Initialize user data
def initialize_user(user_id):
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {
            "credits": 0,
            "keys_redeemed": 0,
            "registered_at": datetime.now(),
            "premium_expiry": None  # New field for premium expiration date
        }

# Initialize SQLite database
conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    credits INTEGER DEFAULT 0,
    keys_redeemed INTEGER DEFAULT 0,
    registered_at TEXT,
    premium_expiry TEXT
)
""")
conn.commit()

# Add a new user to the database
def add_user_to_db(user_id, name):
    cursor.execute("""
    INSERT OR IGNORE INTO users (id, name, credits, keys_redeemed, registered_at, premium_expiry)
    VALUES (?, ?, 0, 0, ?, NULL)
    """, (user_id, name, datetime.now()))
    conn.commit()

# Update user data in the database
def update_user_in_db(user_id, credits=None, keys_redeemed=None, premium_expiry=None):
    cursor.execute("""
    UPDATE users
    SET credits = COALESCE(?, credits),
        keys_redeemed = COALESCE(?, keys_redeemed),
        premium_expiry = COALESCE(?, premium_expiry)
    WHERE id = ?
    """, (credits, keys_redeemed, premium_expiry, user_id))
    conn.commit()

# Fetch user data from the database
def get_user_from_db(user_id):
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    return result

# Check if a user is registered
def is_user_registered(user_id):
    cursor.execute("SELECT registered_at FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    return result is not None and result[0] is not None

#start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not get_user_from_db(user.id):
        add_user_to_db(user.id, user.first_name)

    if user.id == OWNER_ID:
        await update.message.reply_text(
            "To view owner and user commands, use the /menu command."
        )
    else:
        if not is_user_registered(user.id):
            await update.message.reply_text(
                "To use the bot, please register first by typing /register."
            )
        else:
            await update.message.reply_text(
                "Welcome back! Use /menu to see the available commands."
            )

# `/register` Command
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_user_registered(user.id):
        add_user_to_db(user.id, user.first_name)
        cursor.execute("""
        UPDATE users SET registered_at = ? WHERE id = ?
        """, (datetime.now(), user.id))
        conn.commit()

        await update.message.reply_text(
            f"Registration Successful ✓\n"
            f"━━━━━━━━━━━━━━\n"
            f"● Name: {user.first_name}\n"
            f"● User ID: {user.id}\n"
            f"● Role: Free\n\n"
            f"To explore bot commands, type /menu."
        )
    else:
        await update.message.reply_text("❌ You are already registered!")


# `/info` Command with updated expiration logic for normal users and owners
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    initialize_user(user.id)
    user_data = USER_DATA[user.id]

    # Determine user status and expiration based on credits
    if user.id == OWNER_ID:
        # For Owner, show "Unlimited Credits" and "No Date Lifetime"
        credits = "Unlimited Credits"
        premium_status = "Premium"
        expired_plan = "Lifetime"  # Owner has lifetime plan
        expiration_date = "No Date Lifetime"
    else:
        credits = user_data["credits"]
        if credits >= 100:
            premium_status = "Premium"
            # Set expiration date to 30 days from now for users with enough credits
            expired_plan = "Active"
            expiration_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            premium_status = "Basic"
            expired_plan = "N/A"
            expiration_date = "N/A"

    profile_link = f"https://t.me/{user.username}" if user.username else "No Username"
    tg_premium = "Yes" if user.is_premium else "No"

    await update.message.reply_text(
        f"✓ Your Information:\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"● Name: {user.first_name}\n"
        f"● ID: {user.id}\n"
        f"● Username: {profile_link}\n"
        f"● Telegram Premium: {tg_premium}\n"
        f"● Status: {premium_status}\n"
        f"● Credits: {credits}\n"
        f"● Keys Redeemed: {user_data['keys_redeemed']}\n"
        f"● Registered At: {user_data['registered_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"● Plan Status: {expired_plan}\n"
        f"● Expiration Date: {expiration_date}\n"
    )


# `/balance` Command
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    initialize_user(user.id)

    # Determine credits based on user type (Owner or Normal User)
    if user.id == OWNER_ID:
        credits = "Unlimited Credits"  # Owner gets unlimited credits
    else:
        credits = USER_DATA[user.id]["credits"]  # Normal user gets their actual credit balance

    # Send the balance information to the user
    await update.message.reply_text(
        f"✓ Your Current Balance:\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"● Credits: {credits}\n"
    )

# `/genredeem` Command (Owner only)
async def generate_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        num_codes = int(context.args[0])  # Number of codes to generate
        credit_amount = int(context.args[1])  # Credits per code
        codes = []

        for _ in range(num_codes):
            # Generate a random redeem code
            random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
            code = f"RIYOSTER-{random_part}-RIYO"  # New format for redeem codes
            REDEEM_CODES[code] = credit_amount  # Save the code with credits
            codes.append(code)

        # Format all generated codes into a single message
        codes_text = "\n".join(codes)
        message = (
            f"Redeem Codes Generated ✅\n\n"
            f"Each code adds {credit_amount} credits.\n\n"
            f"{codes_text}\n\n"
            f"Use the codes with the following command:\n"
            f"`/redeem <code>`"
        )

        # Send the message
        await update.message.reply_text(message, parse_mode="Markdown")

    except (IndexError, ValueError):
        await update.message.reply_text("❌ Correct usage: /genredeem <number_of_codes> <credit_amount>")

# `/redeem` Command
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    initialize_user(user_id)

    try:
        # Check if a code was provided
        code = context.args[0]
        if code in REDEEM_CODES:
            # Redeem the code
            credits = REDEEM_CODES.pop(code)  # Remove code after use
            USER_DATA[user_id]["credits"] += credits
            USER_DATA[user_id]["keys_redeemed"] += 1

            # Update expiration if the user goes above 100 credits
            if USER_DATA[user_id]["credits"] >= 100:
                USER_DATA[user_id]["premium_expiry"] = datetime.now() + timedelta(days=30)  # Set 1 month expiration

            # Determine user status
            if USER_DATA[user_id]["credits"] >= 100:
                premium_status = "Premium"
            else:
                premium_status = "Basic"

            # Send confirmation to the user
            await update.message.reply_text(
                f"Redeemed Successfully ✅\n"
                f"━━━━━━━━━━━━━━━\n"
                f"● Giftcode: {code}\n"
                f"● User ID: {user_id}\n\n"
                f"Message: Congratz! Your Provided Giftcode Successfully Redeemed to Your Account, "
                f"And You Got \"{credits} Credits + {premium_status} Subscription\"."
            )
        else:
            # Handle invalid or already used codes
            if code.startswith("MONSTER-"):
                await update.message.reply_text(
                    "❌ Invalid or already used code.\n\n"
                    "➔ Ensure the code is correct.\n"
                    "➔ Check if the code has been used before."
                )
            else:
                await update.message.reply_text(
                    "❌ Invalid code format.\n\n"
                    "➔ Codes should start with 'MONSTER-'.\n"
                    "➔ Use `/genredeem` to generate new codes (Owner only)."
                )
    except IndexError:
        # Handle case where no code was provided
        await update.message.reply_text(
            "❌ Correct usage: `/redeem <code>`\n\n"
            "➔ Replace `<code>` with your redeem code."
        )

# `/bc` Command (Broadcast)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("❌ Correct usage: /bc <message>")
        return

    cursor.execute("SELECT id FROM users WHERE registered_at IS NOT NULL")
    users = cursor.fetchall()

    broadcast_count = 0
    for user_id, in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            broadcast_count += 1
        except Exception:
            pass

    await update.message.reply_text(f"✅ Broadcast message sent to {broadcast_count} users.")

# `/adcre` Command (Owner only)
async def add_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        initialize_user(user_id)

        USER_DATA[user_id]["credits"] += amount
        await context.bot.send_message(user_id, f"✅ {amount} credits have been added to your account by the owner.")
        await update.message.reply_text(f"✅ Added {amount} credits to user {user_id}.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Correct usage: /adcre <user_id> <amount>")

# `/lescre` Command (Owner only)
async def subtract_credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        initialize_user(user_id)

        if USER_DATA[user_id]["credits"] >= amount:
            USER_DATA[user_id]["credits"] -= amount
            await context.bot.send_message(user_id, f"❌ {amount} credits have been deducted from your account by the owner.")
            await update.message.reply_text(f"✅ Subtracted {amount} credits from user {user_id}.")
        else:
            await update.message.reply_text("❌ User does not have enough credits.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Correct usage: /lescre <user_id> <amount>")

# `/status` Command (Owner only)
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    total_users = len(USER_DATA)
    premium_users = sum(1 for data in USER_DATA.values() if data["credits"] >= 100)

    uptime = time.time() - START_TIME
    days, remainder = divmod(int(uptime), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    await update.message.reply_text(
        f"✓ Bot Status:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"● Total Users: {total_users}\n"
        f"● Premium Users: {premium_users}\n"
        f"● Uptime: {days}d {hours}h {minutes}m {seconds}s\n"
    )

# `/usinfo` Command (Owner only)
async def user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        user_id = int(context.args[0])
        initialize_user(user_id)
        user_data = USER_DATA[user_id]

        credits = user_data["credits"]
        plan_status = "Active" if credits >= 100 else "Inactive"
        expiration_date = user_data["premium_expiry"].strftime("%Y-%m-%d") if user_data["premium_expiry"] else "No Date Lifetime"

        await update.message.reply_text(
            f"✓ User Information:\n"
            f"━━━━━━━━━━━━━━━\n"
            f"● User ID: {user_id}\n"
            f"● Credits: {credits}\n"
            f"● Plan Status: {plan_status}\n"
            f"● Expiration Date: {expiration_date}\n"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Correct usage: /usinfo <user_id>")

# `/menu` Command
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == OWNER_ID:
        commands = (
            "Owner Commands:\n"
            "- /genredeem <amount> <credits>: Generate redeem codes\n"
            "- /bc <message>: Broadcast a message to all users\n"
            "- /status: View bot status\n"
            "- /adcre <user_id> <amount>: Add credits to a user\n"
            "- /lescre <user_id> <amount>: Subtract credits from a user\n"
            "- /usinfo <user_id>: View user info\n\n"
            "User Commands:\n"
            "- /info: View account details\n"
            "- /redeem <code>: Redeem credits\n"
            "- /balance: Check credits\n"
            "- /ping: Check bot status\n"
        )
    else:
        commands = (
            "User Commands:\n"
            "- /info: View account details\n"
            "- /redeem <code>: Redeem credits\n"
            "- /balance: Check credits\n"
            "- /ping: Check bot status\n"
        )

    await update.message.reply_text(commands)

# Main function to start the bot
if __name__ == "__main__":
    app = ApplicationBuilder().token('7762457523:AAEATcT6c2p04pDnqgU7L8n6kiGjetX1Ejg').build()

    # Add handlers for each command
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("genredeem", generate_redeem))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("bc", broadcast))
    app.add_handler(CommandHandler("adcre", add_credits))
    app.add_handler(CommandHandler("lescre", subtract_credits))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("usinfo", user_info))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("menu", menu))


   # Run the bot
    app.run_polling()
