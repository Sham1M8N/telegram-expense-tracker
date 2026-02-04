import logging
import sqlite3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import csv
import io
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
from datetime import datetime, time, timedelta, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
# (Keep Update, ContextTypes, CommandHandler, etc.)

# --- CONFIGURATION ---
load_dotenv() # Load the .env file
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") # Fetch the hidden variable

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found in .env file!")
    exit()
# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # 1. Expense Table (Existing)
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            date TEXT
        )
    ''')
    
    # 2. NEW: Budget Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            user_id INTEGER PRIMARY KEY,
            monthly_limit REAL
        )
    ''')
    
    conn.commit()
    conn.close()

# --- COMMAND HANDLERS ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    category = data[0]
    amount = float(data[1])
    user_id = query.from_user.id

    # 1. Save Data
    save_expense_to_db(user_id, amount, category) 

    # 2. Check Budget (New Logic)
    budget_msg = check_budget_status(user_id)

    # 3. Reply
    await query.edit_message_text(
        text=f"✅ Saved: RM {amount:.2f} for {category}{budget_msg}", 
        parse_mode='HTML'
    )

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # 1. Fetch data from Database
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("SELECT date, category, amount FROM expenses WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Nothing to export yet! Add some expenses first.")
        return

    # 2. Write to a "Text" Buffer (In-Memory CSV)
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Add a header row so Excel knows what the columns are
    writer.writerow(['Date', 'Category', 'Amount (RM)'])
    writer.writerows(rows)
    
    # 3. Convert to "Binary" Buffer for Telegram
    # We move the cursor to the start of the file with seek(0)
    output.seek(0)
    
    # Convert string data to bytes
    mem_file = io.BytesIO(output.getvalue().encode('utf-8'))
    mem_file.seek(0)
    
    # 4. Name the file (Telegram requires a filename for documents)
    mem_file.name = f"expenses_{datetime.now().strftime('%Y%m%d')}.csv"

    # 5. Send the file
    await update.message.reply_document(document=mem_file, caption="Here is your expense history! 📂")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # --- NEW: SCHEDULE REMINDER ---
    # 1. Remove old jobs if they exist (prevents duplicates)
    current_jobs = context.job_queue.get_jobs_by_name(str(user_id))
    for job in current_jobs:
        job.schedule_removal()
    
    # 2. Set time: 9:00 PM Malaysia Time (UTC+8)
    # 21:00 = 9 PM. Change this if you want a different time!
    reminder_time = time(hour=21, minute=00, tzinfo=timezone(timedelta(hours=8)))
    
    # 3. Add the job
    context.job_queue.run_daily(daily_reminder, reminder_time, chat_id=user_id, name=str(user_id))
    # ------------------------------

    help_text = """
<b>💰 Expense Tracker Bot Guide</b>

<b>1️⃣ Adding Expenses</b>
• <code>/add 10</code> → Add RM 10 (Select category via buttons)
• <code>/add 15 Lunch</code> → Add RM 15 to "Lunch" immediately.

<b>2️⃣ Managing Data</b>
• <code>/list</code> → View recent expenses & their IDs.
• <code>/delete_id 5</code> → Delete specific item.
• <code>/delete</code> → ⚠️ Delete <b>ALL</b> history.

<b>3️⃣ Budget & Insights</b>
• <code>/setbudget 500</code> → Set a monthly limit.
• <code>/chart</code> → View Pie Chart 📊.
• <code>/export</code> → Download CSV 📂.

<i>🔔 Daily Reminder set for 9:00 PM!</i>
    """
    await update.message.reply_text(help_text, parse_mode='HTML')

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Usage: /add <amount> [category]")
            return

        amount = float(context.args[0])
        user_id = update.effective_user.id

        # --- NEW LOGIC START ---
        # Check if the user typed a category (e.g., /add 2 food)
        # context.args would look like ['2', 'food']
        if len(context.args) > 1:
            # .title() makes "food" -> "Food" and "nasi lemak" -> "Nasi Lemak"
            category = " ".join(context.args[1:]).title() 
            
            # 1. Save directly
            save_expense_to_db(user_id, amount, category)
            
            # 2. Check budget
            budget_msg = check_budget_status(user_id)
            
            # 3. Reply
            await update.message.reply_text(f"✅ Saved: RM {amount:.2f} for {category}{budget_msg}", parse_mode='HTML')
            return
      

        # If we reach here, it means NO category was typed. Show the buttons.
        categories = ["Food", "Transport", "Shopping", "Games", "Utilities", "Other"]
        
        keyboard = [
            [
                InlineKeyboardButton(f"🍔 {cat}", callback_data=f"{cat}|{amount}") 
                for cat in categories[:3]
            ],
            [
                InlineKeyboardButton(f"📦 {cat}", callback_data=f"{cat}|{amount}") 
                for cat in categories[3:]
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Select category for RM {amount:.2f}:", reply_markup=reply_markup)

    except ValueError:
        await update.message.reply_text("❌ Error: Amount must be a number.")

async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        conn = sqlite3.connect('expenses.db')
        c = conn.cursor()
        
        c.execute("SELECT id, amount, category, date FROM expenses WHERE user_id=? ORDER BY date DESC LIMIT 10", (user_id,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            await update.message.reply_text("No expenses recorded yet.")
            return

        message = "<b>Your Recent Expenses:</b>\n\n"
        for row in rows:
            r_id, amount, category, date = row
            message += f"🆔 <b>{r_id}</b> | RM {amount:.2f} - {category}\n"
        
        # FIX: Changed <ID> to [ID] so Telegram doesn't think it's HTML code
        message += "\nTo delete an item, type: <code>/delete_id [ID]</code>" 
        
        await update.message.reply_text(message, parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching list: {e}")

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Usage: /setbudget <amount> (e.g., /setbudget 500)")
            return

        limit = float(context.args[0])
        user_id = update.effective_user.id

        conn = sqlite3.connect('expenses.db')
        c = conn.cursor()
        # INSERT OR REPLACE ensures we update the existing row if it exists
        c.execute("INSERT OR REPLACE INTO budgets (user_id, monthly_limit) VALUES (?, ?)", (user_id, limit))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Monthly budget set to RM {limit:.2f}")

    except ValueError:
        await update.message.reply_text("❌ Error: Budget must be a number.")

async def delete_specific_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("Usage: /delete_id <ID> (e.g., /delete_id 5)")
            return

        target_id = int(context.args[0])
        user_id = update.effective_user.id

        conn = sqlite3.connect('expenses.db')
        c = conn.cursor()
        
        # Check if the item belongs to this user before deleting (Security check!)
        c.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (target_id, user_id))
        
        if c.rowcount > 0:
            msg = f"✅ Item {target_id} deleted successfully."
        else:
            msg = f"❌ Could not delete item {target_id}. It might not exist or belongs to someone else."
            
        conn.commit()
        conn.close()
        
        await update.message.reply_text(msg)

    except ValueError:
        await update.message.reply_text("❌ Error: ID must be a number.")

async def delete_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("🗑️ All your expenses have been deleted.")

async def chart_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # SQL Magic: Group by category and sum the amounts
    c.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? GROUP BY category", (user_id,))
    data = c.fetchall()
    conn.close()

    if not data:
        await update.message.reply_text("No data to visualize yet! Add some expenses first.")
        return

    # Prepare data for the chart
    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    # Create the Pie Chart
    plt.figure(figsize=(6, 6)) # Size of the image
    plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=140)
    plt.title('My Spending Habits')
    
    # Save the chart to a memory buffer (RAM) instead of a file
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0) # Rewind the buffer to the beginning so we can read it
    plt.close() # Close the plot to free up memory

    # Send the image to Telegram
    await update.message.reply_photo(photo=buf, caption="Here is your spending breakdown! 📊")
def check_budget_status(user_id):
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    
    # 1. Get User's Budget
    c.execute("SELECT monthly_limit FROM budgets WHERE user_id=?", (user_id,))
    budget_row = c.fetchone()
    
    if not budget_row:
        conn.close()
        return "" # No budget set, no warning needed

    budget_limit = budget_row[0]

    # 2. Calculate Total Spent This Month
    current_month = datetime.now().strftime("%Y-%m")
    c.execute("SELECT SUM(amount) FROM expenses WHERE user_id=? AND date LIKE ?", (user_id, f"{current_month}%"))
    total_spent = c.fetchone()[0] or 0.0 # Handle case where total is None
    
    conn.close()

    # 3. Check Thresholds
    if total_spent > budget_limit:
        return f"\n\n🚨 <b>ALERT:</b> You have exceeded your budget of RM {budget_limit:.2f}!"
    elif total_spent > (budget_limit * 0.8):
        percent = int((total_spent / budget_limit) * 100)
        return f"\n\n⚠️ <b>Warning:</b> You've used {percent}% of your monthly budget."
    
    return ""

async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    # Get the chat_id from the job context
    job = context.job
    user_id = job.chat_id
    
    # 1. Check if user added anything today
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect('expenses.db')
    c = conn.cursor()
    # We use LIKE '2026-02-04%' to match the date part of the timestamp
    c.execute("SELECT id FROM expenses WHERE user_id=? AND date LIKE ?", (user_id, f"{today}%"))
    row = c.fetchone()
    conn.close()
    
    # 2. If no data found, send the nag message!
    if not row:
        await context.bot.send_message(
            chat_id=user_id, 
            text="📅 <b>Reminder:</b> You haven't tracked any expenses today!\nDon't break your streak! Use /add to log something.", 
            parse_mode='HTML'
        )

def save_expense_to_db(user_id, amount, category, db_name='expenses.db'):
    """
    Independent function to save data.
    We pass the db_name so we can use a fake DB for testing!
    """
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    # Ensure table exists (just in case)
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            date TEXT
        )
    ''')
    c.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)", 
              (user_id, amount, category, date))
    conn.commit()
    conn.close()
    return True

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    # 1. Initialize Database
    init_db()
    
    # 2. Build the Bot (THIS WAS MISSING)
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # 3. Add Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('add', add_expense))
    application.add_handler(CommandHandler('list', list_expenses))
    application.add_handler(CommandHandler('delete', delete_history))
    application.add_handler(CommandHandler('chart', chart_expenses))
    application.add_handler(CommandHandler('export', export_data))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler('delete_id', delete_specific_expense)) 
    application.add_handler(CommandHandler('setbudget', set_budget)) 
    
    # 4. Start the Fake Web Server
    keep_alive()
    print("Web server started for Render!")
    
    # 5. Run the Bot
    print("Bot is running...")
    application.run_polling()