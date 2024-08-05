import logging
import schedule
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Your API ID, API hash, and bot token
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
BOT_TOKEN = 'YOUR_BOT_TOKEN'
OWNER_ID = int('YOUR_TELEGRAM_USER_ID')  # Replace with your Telegram user ID

# Dictionary to store custom messages
custom_messages = {
    'start': 'Hi! Welcome to the Subscription Bot. Use /add_user <user_id> to add a user.'
}

# Dictionary to store subscribed users
subscribed_users = {}
awaiting_utr = {}
awaiting_plan = {}
awaiting_new_plan = {}

# Create a Pyrogram Client
app = Client("subscription_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Handler for the /start command
@app.on_message(filters.command("start"))
def start(client: Client, message: Message):
    message.reply_text(custom_messages['start'])

# Handler for the /set_start command (only for the owner)
@app.on_message(filters.command("set_start") & filters.user(OWNER_ID))
def set_start(client: Client, message: Message):
    if len(message.command) > 1:
        custom_messages['start'] = ' '.join(message.command[1:])
        message.reply_text('Start message updated!')
    else:
        message.reply_text('Please provide a new start message.')

# Handler for the /add_user command (only for the owner)
@app.on_message(filters.command("add_user") & filters.user(OWNER_ID))
def add_user(client: Client, message: Message):
    if len(message.command) > 1:
        user_id = int(message.command[1])
        try:
            user = client.get_users(user_id)
            subscribed_users[user.id] = {'username': user.username, 'first_name': user.first_name, 'last_name': user.last_name}
            awaiting_utr[user.id] = True
            message.reply_text(f'User {user.first_name} ({user.username}) added successfully! Please send their UTR number.')
        except Exception as e:
            message.reply_text(f'Failed to add user: {e}')
    else:
        message.reply_text('Please provide a user ID.')

# Handler to collect UTR number
@app.on_message(filters.text & filters.user(OWNER_ID))
def collect_utr(client: Client, message: Message):
    user_id = message.chat.id
    if user_id in awaiting_utr:
        subscribed_users[user_id]['utr_number'] = message.text
        del awaiting_utr[user_id]
        awaiting_plan[user_id] = True
        message.reply_text('UTR number saved! Now please send the subscription plan end date (YYYY-MM-DD).')
    elif user_id in awaiting_plan:
        subscribed_users[user_id]['plan_end_date'] = message.text
        del awaiting_plan[user_id]
        message.reply_text('Subscription plan end date saved! User has been fully registered.')
    elif user_id in awaiting_new_plan:
        subscribed_users[user_id]['plan_end_date'] = message.text
        del awaiting_new_plan[user_id]
        message.reply_text('Subscription plan end date updated!')

# Handler for the /all_users command
@app.on_message(filters.command("all_users") & filters.user(OWNER_ID))
def all_users(client: Client, message: Message):
    if subscribed_users:
        buttons = [
            [InlineKeyboardButton(f"{user['first_name']} ({user_id})", callback_data=str(user_id))]
            for user_id, user in subscribed_users.items()
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        message.reply_text("List of all users:", reply_markup=reply_markup)
    else:
        message.reply_text("No users found.")

# Handler for the /help command
@app.on_message(filters.command("help"))
def help_command(client: Client, message: Message):
    help_text = (
        "/start - Start the bot and see the welcome message\n"
        "/set_start <message> - Set a new start message (Owner only)\n"
        "/add_user <user_id> - Add a user by their Telegram ID (Owner only)\n"
        "/remove_user <user_id> - Remove a user by their Telegram ID (Owner only)\n"
        "/all_users - List all users with inline buttons (Owner only)\n"
        "/user_info <user_id> - Get user information and actions (Owner only)\n"
        "/help - Show this help message"
    )
    message.reply_text(help_text)

# Handler for the /remove_user command (only for the owner)
@app.on_message(filters.command("remove_user") & filters.user(OWNER_ID))
def remove_user(client: Client, message: Message):
    if len(message.command) > 1:
        user_id = int(message.command[1])
        if user_id in subscribed_users:
            del subscribed_users[user_id]
            message.reply_text(f'User with ID {user_id} has been removed successfully.')
        else:
            message.reply_text(f'User with ID {user_id} not found.')
    else:
        message.reply_text('Please provide a user ID.')

# Handler for the /user_info command (only for the owner)
@app.on_message(filters.command("user_info") & filters.user(OWNER_ID))
def user_info(client: Client, message: Message):
    if len(message.command) > 1:
        user_id = int(message.command[1])
        user = subscribed_users.get(user_id)
        if user:
            details = (
                f"User Details:\n"
                f"First Name: {user['first_name']}\n"
                f"Last Name: {user['last_name']}\n"
                f"Username: {user['username']}\n"
                f"UTR Number: {user.get('utr_number', 'N/A')}\n"
                f"Subscription End Date: {user.get('plan_end_date', 'N/A')}"
            )
            buttons = [
                [InlineKeyboardButton("Remove User", callback_data=f"remove_{user_id}"),
                 InlineKeyboardButton("Edit Plan", callback_data=f"edit_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            message.reply_text(details, reply_markup=reply_markup)
        else:
            message.reply_text("User not found.")
    else:
        message.reply_text('Please provide a user ID.')

# Handler for the callback queries for removing or editing users
@app.on_callback_query()
def callback_query_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    if data.startswith("remove_"):
        user_id = int(data.split("_")[1])
        if user_id in subscribed_users:
            del subscribed_users[user_id]
            callback_query.message.edit_text(f'User with ID {user_id} has been removed successfully.')
        else:
            callback_query.message.edit_text('User not found.')
    elif data.startswith("edit_"):
        user_id = int(data.split("_")[1])
        awaiting_new_plan[user_id] = True
        callback_query.message.edit_text(f'Please send the new subscription plan end date for user ID {user_id} (YYYY-MM-DD).')

def check_subscriptions():
    today = datetime.now().date()
    two_days_later = today + timedelta(days=2)
    
    for user_id, user_info in subscribed_users.items():
        plan_end_date = datetime.strptime(user_info['plan_end_date'], "%Y-%m-%d").date()
        
        if plan_end_date == two_days_later:
            # Send reminder 2 days before end date
            message_text = (
                f"Reminder: Your subscription plan will end in 2 days on {plan_end_date}. "
                f"Please contact @Sam_Dude2 to renew your subscription."
            )
            app.send_message(user_id, message_text)
            app.send_message(OWNER_ID, f"Reminder: {user_info['first_name']}'s subscription will end in 2 days.")
        
        if plan_end_date == today:
            # Send notification on the end date
            message_text = (
                f"Your subscription plan ends today. Please contact @Sam_Dude2 to renew your subscription."
            )
            app.send_message(user_id, message_text)
            app.send_message(OWNER_ID, f"Notification: {user_info['first_name']}'s subscription ends today.")

# Schedule the job daily at 12:00 PM
schedule.every().day.at("12:00").do(check_subscriptions)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Start the Pyrogram client
    app.start()

    # Run the scheduler in a separate thread
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()

    # Run the bot
    app.idle()
