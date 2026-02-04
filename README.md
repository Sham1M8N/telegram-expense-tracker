# 💰 Telegram Expense Tracker Bot

A full-featured personal finance bot built with Python that helps users track expenses, visualize spending habits, and manage budgets directly within Telegram.

## 🚀 Features

* **Smart Logging:** Log expenses via simple commands (`/add 15 Lunch`) or interactive inline buttons.
* **Data Visualization:** Generates and sends a Pie Chart of spending habits directly to the chat.
* **Budget Alerts:** Set a monthly limit (`/setbudget`) and receive real-time warnings when you approach your cap.
* **Data Portability:** Export your entire expense history to a `.csv` file for use in Excel or Google Sheets.
* **Persistence:** Uses SQLite to store data securely and reliably.
* **Daily Reminders:** Automated "Job Queue" system that reminds you to log expenses if you forget.

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **Libraries:** `python-telegram-bot`, `matplotlib`, `sqlite3`, `python-dotenv`
* **Database:** SQLite (Lightweight & Serverless)
* **Automation:** `APScheduler` (via Telegram JobQueue)

## ⚙️ Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/telegram-expense-tracker.git](https://github.com/YOUR_USERNAME/telegram-expense-tracker.git)
    cd telegram-expense-tracker
    ```

2.  **Install dependencies**
    ```bash
    pip install python-telegram-bot[job-queue] matplotlib python-dotenv
    ```

3.  **Configure Environment**
    Create a `.env` file in the root directory and add your Telegram Bot Token:
    ```env
    TELEGRAM_TOKEN=your_token_here
    ```

4.  **Run the Bot**
    ```bash
    python main.py
    ```

## 📖 Commands

| Command | Description |
| :--- | :--- |
| `/start` | Initialize the bot and view the dashboard |
| `/add <amount> [category]` | Add a new expense (e.g., `/add 15 Food`) |
| `/list` | Show the last 10 expenses with IDs |
| `/delete_id <ID>` | Delete a specific expense by ID |
| `/chart` | Generate a spending breakdown chart |
| `/export` | Download a CSV file of all data |
| `/setbudget <amount>` | Set a monthly spending limit |

## 📂 Project Structure

```text
├── main.py           # The bot logic and handlers
├── tests.py          # Unit tests for database functions
├── .env              # (Ignored) Stores API keys
├── .gitignore        # Prevents uploading sensitive data
└── README.md         # Project documentation