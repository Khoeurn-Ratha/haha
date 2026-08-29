# ⚡ RATHA // QUANT TRADE TRACKER & PERFORMANCE DASHBOARD
> **$100 ➔ $1,000 in 1 Month Discipline Protocol Web Application**

A full-stack trading journal, performance analytics engine, and discipline enforcer built with **Python (Flask)** and a **zoqira.pro-inspired cyberpunk dark UI**.

---

## 🎯 30-Day Growth Challenge ($100 ➔ $1,000)
- **Starting Capital**: $100.00
- **Target Capital**: $1,000.00 (10x growth)
- **Daily Target**: $5 - $10 (5% - 10% daily compound)
- **Max Daily Risk**: $5.00 (Stop trading if -$5 is reached)

---

## 🛡️ The 8 Golden Trading Rules Protocol

| # | Rule | Description |
|---|---|---|
| **1** | **Don't FOMO** | Wait patiently for high-probability setups. Never chase candles. |
| **2** | **Don't entry with another signal** | Stick strictly to your own edge. Never blindly follow caller groups. |
| **3** | **1 Day = 1 or 2 Setups Maximum** | Quality over quantity. Hard limit of 2 trades per day. |
| **4** | **Risk Minimum 1:2 RR** | Minimum 1:2 Risk to Reward on every trade execution. |
| **5** | **15m Flow + 1m Entry (MSS & TS)** | Check 15m structure flow, drop to 1m for Market Structure Shift (MSS) and Time & Symmetry (TS). |
| **6** | **1H Key Level + 5m/3m Entry (MSS)** | React at 1H key support/resistance, enter on 5m or 3m confirmed MSS. |
| **7** | **4H Key Level + 15m/5m Entry (MSS)** | Major 4H zone, enter on 15m or 5m confirmed MSS. |
| **8** | **Daily Target $5-$10 \| Risk $5 (Stop if -$5)** | Stop trading immediately if daily loss hits -$5! |

---

## 🚀 Key Features

1. **Cyberpunk Dark Glassmorphic Dashboard**: Sleek aesthetic inspired by `zoqira.pro` with neon glow cards, ambient lighting, and high-tech typography.
2. **Dynamic Rule 8 Stop Loss Lockout Banner**: Automatically turns red and flashes a capital preservation warning when daily loss reaches -$5.
3. **Interactive Charts**:
   - **Equity Growth Curve** ($100 starting line to $1,000 goal line)
   - **Daily P&L Bar Chart** (Green profit, Red loss)
   - **Win Rate & Outcomes Donut Chart**
   - **Setup Performance Comparison** (15m/1m MSS vs 1H vs 4H)
4. **Interactive Pre-Flight Rules Checklist**: 8-point checklist before submitting each trade.
5. **Instant Telegram Alerts**:
   - Sends formatted trade summaries directly to your Telegram bot.
   - Triggers emergency stop trading alerts when daily risk limit is breached.
6. **Built-in Risk & Lot Size Calculator**:
   - Calculates exact lot sizes for Gold, Forex, Crypto, and Indices to risk exactly $5.00 per trade.
7. **CSV Export & Journal Management**: Full trade log history with search filters and editing.

---

## 🛠️ Installation & Run

1. Open a terminal in this directory:
   ```bash
   py -m pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   py app.py
   ```
   *Or double click `start.bat` on Windows.*

3. Open your browser at:
   ```
   http://127.0.0.1:5000
   ```

---

## 🤖 Setting Up Telegram Notifications

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to create your bot and copy the **Bot Token**.
3. Search for `@userinfobot` or `@RawDataBot` to find your personal **Chat ID** (a number like `123456789`).
4. Click **"Telegram Alerts"** in the web dashboard header.
5. Paste your **Bot Token** and **Chat ID**, toggle Telegram ON, and click **"Send Test Alert"**.
