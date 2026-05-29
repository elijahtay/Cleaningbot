# HOGC FM Report Bot

A Telegram bot for HOGC Facilities Management — allows members to quickly report missing items, broken equipment, or unresolved issues directly to the FM team group chat.

---

## Features

- 🛒 **Missing / Used Up** — report consumables that ran out or items gone missing
- 🔧 **Broken Equipment** — flag damaged or malfunctioning equipment
- ⚠️ **Unresolved Issue** — report something spotted but couldn't be resolved
- 📍 Location selection from predefined list
- 📸 Optional photo attachment
- 📬 Reports forwarded to FM group chat with submitter name and timestamp

---

## Setup

### Step 1: Create the Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** you receive

### Step 2: Get the FM Group Chat ID

1. Add **@userinfobot** to your FM group chat
2. It will reply with the group's chat ID (a negative number like `-1001234567890`)
3. Remove @userinfobot after getting the ID

   **Alternative:** Add the bot to the group, send a message, then visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   Look for `"chat":{"id":` in the response.

### Step 3: Add Bot to FM Group

1. Add your new bot to the FM group chat
2. Make it an **admin** (so it can send messages)

### Step 4: Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
FM_GROUP_CHAT_ID=-1001234567890
```

---

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in env file
cp .env.example .env

# Run the bot
python bot.py
```

---

## Deploy to Railway

### Option A: Via GitHub (Recommended)

1. Push this folder to a GitHub repository
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Select your repo
4. Go to **Variables** tab and add:
   - `BOT_TOKEN` = your bot token
   - `FM_GROUP_CHAT_ID` = your group chat ID
5. Railway will auto-deploy. Done!

### Option B: Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and init
railway login
railway init

# Set environment variables
railway variables set BOT_TOKEN=your_token_here
railway variables set FM_GROUP_CHAT_ID=your_chat_id_here

# Deploy
railway up
```

> **Note:** The bot runs as a **worker** (long-running process), not a web server. No port needed.

---

## Customising Locations

Edit the `LOCATIONS` list in `bot.py` to match your actual areas:

```python
LOCATIONS = [
    "Atrium & Lift Lobby",
    "Auditorium",
    "Level 3",
    # ... add or remove as needed
]
```

---

## Sample Report (what the FM group receives)

```
🔴 FM REPORT — BROKEN EQUIPMENT
──────────────────────────────
📍 Location: Auditorium
📝 Details: Projector remote not responding, tried replacing batteries
──────────────────────────────
👤 Reported by: @johndoe
🕐 Time: 25 May 2026, 10:32 AM
```

With photo attached if submitted.

---

## Commands

| Command | Action |
|---------|--------|
| `/start` | Start a new report |
| `/report` | Same as /start |
| `/skip` | Skip photo step |
| `/cancel` | Cancel current report |
