"""
Telegram Bot Setup Helper

Run this script to set up Telegram alerts:
    python setup_telegram.py

It will guide you through:
1. Creating a Telegram bot via @BotFather
2. Getting your chat ID
3. Saving credentials to .env file
"""
import os
import requests
from pathlib import Path


def step1_create_bot():
    print("=" * 60)
    print("  STEP 1: Create a Telegram Bot")
    print("=" * 60)
    print()
    print("1. Open Telegram on your phone")
    print("2. Search for @BotFather")
    print("3. Send: /newbot")
    print("4. Enter a name for your bot (e.g., 'Nifty SAR Bot')")
    print("5. Enter a username (must end with 'bot', e.g., 'nifty_sar_bot')")
    print("6. BotFather will give you a TOKEN")
    print()
    token = input("Paste your Telegram Bot Token here: ").strip()
    return token


def step2_get_chat_id(token):
    print()
    print("=" * 60)
    print("  STEP 2: Get Your Chat ID")
    print("=" * 60)
    print()
    print("1. Open Telegram")
    print(f"2. Search for your bot (you just created it)")
    print("3. Send any message to your bot (e.g., 'hello')")
    print("4. The script will now fetch your chat ID...")
    print()

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()

        if not data.get("ok"):
            print(f"Error: {data}")
            return None

        results = data.get("result", [])
        if not results:
            print("No messages found. Please send a message to your bot first.")
            return None

        # Get the chat ID from the last message
        chat_id = results[-1]["message"]["chat"]["id"]
        chat_name = results[-1]["message"]["chat"].get("first_name", "Unknown")
        print(f"Found chat: {chat_name} (ID: {chat_id})")
        return str(chat_id)

    except Exception as e:
        print(f"Error fetching chat ID: {e}")
        return None


def step3_test_connection(token, chat_id):
    print()
    print("=" * 60)
    print("  STEP 3: Test Connection")
    print("=" * 60)
    print()

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 BB + Pure SAR Bot\n\n✅ Telegram connected successfully!",
        "parse_mode": "HTML",
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("✅ Test message sent successfully!")
            print("Check your Telegram for the message.")
            return True
        else:
            print(f"Error: {resp.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def save_credentials(token, chat_id):
    env_path = Path(__file__).parent / ".env"

    # Read existing .env if present
    existing = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line:
                key, val = line.split("=", 1)
                existing[key.strip()] = val.strip()

    # Update with Telegram credentials
    existing["TELEGRAM_TOKEN"] = token
    existing["TELEGRAM_CHAT_ID"] = chat_id

    # Write back
    with open(env_path, "w") as f:
        for key, val in existing.items():
            f.write(f"{key}={val}\n")

    print(f"\n✅ Credentials saved to {env_path}")


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║  TELEGRAM BOT SETUP — BB + Pure SAR Bot" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Step 1
    token = step1_create_bot()
    if not token:
        print("Invalid token. Please try again.")
        return

    # Step 2
    chat_id = step2_get_chat_id(token)
    if not chat_id:
        print("Failed to get chat ID. Please try again.")
        return

    # Step 3
    if not step3_test_connection(token, chat_id):
        print("Test failed. Please try again.")
        return

    # Save
    save_credentials(token, chat_id)

    print()
    print("=" * 60)
    print("  SETUP COMPLETE!")
    print("=" * 60)
    print()
    print("Your bot will now send alerts to Telegram:")
    print("  - BUY/SELL signals")
    print("  - Trade executions")
    print("  - Square-off alerts (15:15 IST)")
    print("  - Daily P&L summary")
    print()
    print("To start the bot:")
    print("  python run.py")
    print()


if __name__ == "__main__":
    main()
