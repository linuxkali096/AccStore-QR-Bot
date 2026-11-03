<div align="center">

# ⚡ QR GENERATOR PRO ⚡
### 🚀 The Ultimate High-Performance Telegram UPI, Crypto & Math Bot

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram Bot API](https://img.shields.io/badge/Telegram_Bot_API-v21.5-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Status](https://img.shields.io/badge/Status-Production_Ready-00C853?style=for-the-badge&logo=render&logoColor=white)](#)
[![Security](https://img.shields.io/badge/Security-Audit_Passed-blueviolet?style=for-the-badge&logo=shield&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-black?style=for-the-badge)](#)

<p align="center">
  <b>Generate instant, high-contrast UPI QR codes with custom profile photos, check real-time crypto prices with 0ms delay, and solve chat math in real-time.</b><br>
  <i>Built with async Python, persistent connection pools, and rock-solid crash recovery.</i>
</p>

---

</div>

## 📖 Table of Contents
- [🌟 What is QR Generator Pro?](#-what-is-qr-generator-pro)
- [✨ Key Features](#-key-features)
- [🕹️ Commands Cheatsheet](#️-commands-cheatsheet)
- [🧮 Smart Chat Calculator](#-smart-chat-calculator)
- [🪙 Zero-Delay Crypto Engine](#-zero-delay-crypto-engine)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [⚙️ Environment Settings (.env)](#️-environment-settings-env)
- [🌐 VPS Deployment & Keep-Alive](#-vps-deployment--keep-alive)
- [🛡️ Security & Reliability](#️-security--reliability)
- [🤝 Community & Support](#-community--support)

---

## 🌟 What is QR Generator Pro?

**QR Generator Pro** is a modern, enterprise-grade Telegram bot designed for merchants, freelancers, OTC crypto traders, and community groups.

It combines:
1. **Instant UPI Payments**: Scan-ready QR codes embedded with merchant name, amount, note, and your Telegram profile picture.
2. **One-Tap "Copy UPI"**: Modern Telegram clipboard action for users on desktop or broken cameras.
3. **Live Crypto Rates**: Zero-delay market data for Bitcoin, Ethereum, Solana, and USDT/INR.
4. **Smart Math Calculator**: Auto-detects expressions in chat (e.g., `300+340+85 = 725`) and percentage discounts.

---

## ✨ Key Features

- ⚡ **Lightning Fast (0ms USDT Cache)**: USDT-INR exchange rates are kept hot in memory with background polling.
- 🎨 **Custom Brand Canvas**: Generates loss-free 300 DPI payment cards with stylish neon accents.
- 📋 **Native Clipboard Button**: Copies your UPI ID instantly with 1 tap using Telegram Bot API 7.0+.
- 🔢 **Safe AST Math Parser**: Evaluates complex expressions (`sqrt`, `pow`, percentages) without dangerous `eval()`.
- 📊 **O(N) Leaderboard**: Instant rank calculation without heavy database sorting.
- 🧹 **Automatic Disk Hygiene**: Self-cleans old profile images from `cache/` every 24 hours.
- 💾 **Crash-Proof Atomic Storage**: Writes database updates via temporary files to prevent data corruption.
- 🛡️ **Built-in Security Guards**: Formula injection defense, strict rate limiting, and ban lists.

---

## 🕹️ Commands Cheatsheet

### 👤 User Commands

| Command | Example | What It Does |
| :--- | :--- | :--- |
| **`/start`** | `/start` | Opens your interactive control dashboard. |
| **`/pay`** | `/pay 500 Dinner` | Generates a custom payment QR with amount and note. |
| **`/setup`** | `/setup` | Links your UPI ID (`name@bank`) and merchant name. |
| **`/price`** | `/price btc` | Checks live cryptocurrency rates from Binance & MEXC. |
| **`/<coin>`** | `/eth` or `/sol` | Shortcut command for instant crypto market cards. |
| **`/calc`** | `/calc 1500 * 0.18` | Solves math calculations safely. |
| **`/ping`** | `/ping` | Displays bot response latency in milliseconds. |
| **`/device`** | `/device` | Shows live VPS CPU, RAM, and server health. |
| **`/help`** | `/help` | Displays quick user guide and tutorial. |

### 👑 Admin Commands

| Command | Example | What It Does |
| :--- | :--- | :--- |
| **`/admin`** | `/admin` | Opens the full visual admin management panel. |
| **`/searchuser`** | `/searchuser 123456` | Looks up any user's profile and generation history. |
| **`/searchupi`** | `/searchupi name@okaxis` | Finds a user account by their UPI address. |
| **`/ban` / `/unban`** | `/ban 123456` | Blocks or restores access for a specific user ID. |
| **`/dm`** | `/dm 123456 Hello!` | Sends a direct message to a user via the bot. |
| **`/wipeuser`** | `/wipeuser 123456` | Completely removes a user profile from the database. |
| **`/resetstats`** | `/resetstats 123456` | Resets QR generation count for a specific user. |
| **`/restart`** | `/restart` | Safely reboots the bot process on the server. |

---

## 🧮 Smart Chat Calculator

No need to open another app! Just type your math directly into private or group chats:

- **Addition & Subtraction:** `380 + 330` ➔ `380 + 330 = 710`
- **Multi-term Bills:** `300 + 340 + 85` ➔ `300 + 340 + 85 = 725`
- **Percentage Discounts:** `500 - 10%` ➔ `450`
- **Parenthesized Tax / GST:** `(100 + 200) + 18%` ➔ `354`
- **Advanced Operations:** `sqrt(144) * 5` ➔ `60`

*All math is parsed through Python's `ast` engine with zero arbitrary code execution risk.*

---

## 🪙 Zero-Delay Crypto Engine

Get live market data delivered in under 1 millisecond:

- 💵 **USDT / INR**: Maintained in memory with 20-second automatic background refresh.
- 🪙 **Top Tickers**: `/btc`, `/eth`, `/sol`, `/pepe`, `/doge`, `/trx`, `/bnb`, etc.
- ⚡ **15-Second In-Memory Cache**: Eliminates redundant external API calls and prevents rate limits.
- 🔄 **Dual Provider Fallback**: Automatically queries Binance first, failing over to MEXC seamlessly.

---

## 🚀 Quick Start & Installation

Setting up the bot is simple. Follow these 4 easy steps:

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/qr-generator-bot.git
cd qr-generator-bot
```

### 2️⃣ Create Virtual Environment & Install Packages
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3️⃣ Configure `.env` File
Create a `.env` file in the root directory:
```bash
cp .env.example .env
nano .env
```

### 4️⃣ Start the Bot
```bash
python3 main.py
```

---

## ⚙️ Environment Settings (.env)

| Variable | Required | Description | Example |
| :--- | :---: | :--- | :--- |
| **`BOT_TOKEN`** | **Yes** | Telegram Bot API token from [@BotFather](https://t.me/BotFather) | `123456789:ABCdefGhI...` |
| **`ADMIN_ID`** | **Yes** | Telegram ID(s) of bot owners (comma-separated) | `987654321,11223344` |
| **`BOT_NAME`** | No | Display name used in headers and cards | `QR Generator Pro` |
| **`BOT_USERNAME`**| No | Official bot username handle | `@Qr_Generator_Pro_Robot` |
| **`SUPPORT_USERNAME`**| No | Support admin handle for user help | `@YourSupport` |
| **`LOG_CHANNEL_ID`** | No | Telegram channel ID for live QR creation logs | `-1001234567890` |
| **`FORCE_SUB_CHANNEL`**| No | Channel username or ID for mandatory join | `@YourChannel` |

---

## 🌐 VPS Deployment & Keep-Alive

### 🔄 Auto-Restarting Supervisor Loop
For 24/7 reliability on Ubuntu/Debian VPS, run inside a persistent GNU Screen session:

```bash
screen -dmS qr_bot bash -c "cd /root/qr_bot && ulimit -n 65535 && while true; do ./venv/bin/python main.py 2>&1 | tee -a bot.log; echo '[qr_bot] Bot stopped. Restarting in 5s...'; sleep 5; done"
```

### 🖥️ Useful VPS Commands
- **View Live Logs**: `screen -r qr_bot` (Press `Ctrl+A` then `D` to detach safely)
- **Check Tail Logs**: `tail -f /root/qr_bot/bot.log`
- **Automated Deploy Script**: Run `node deploy.js` to sync files and restart remotely.

---

## 🛡️ Security & Reliability

This bot adheres to the **Cloudflare Security Audit Standard**:

- 🔒 **Formula Injection Defense (CWE-1236)**: User data exported to CSV is sanitized to prevent spreadsheet macro exploits.
- 🗄️ **Atomic File Writes**: `users.json` uses atomic `.tmp` swapping to survive server power outages.
- ⏱️ **Leaky-Bucket Rate Limiter**: Automatically drops spam traffic while keeping legitimate user flows snappy.
- 🚦 **Safe URL Validation**: Gracefully handles private channels without triggering Telegram button crashes.
- 🧹 **Automatic Disk Eviction**: Deletes temporary avatar caches after 24 hours to prevent disk exhaustion.

---

## 🤝 Community & Support

- 💬 **Need Help or Customization?** Contact support via Telegram: [@YourSupport](https://t.me/)
- ⭐ **Found this useful?** Star this repository on GitHub!
- 📜 **License**: Distributed under the permissive [MIT License](LICENSE).

<div align="center">
  <br>
  <b>Crafted with ❤️ for the global Telegram community.</b>
</div>
