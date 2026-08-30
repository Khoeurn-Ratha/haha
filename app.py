    import os
    import json
    import csv
    import io
    from datetime import datetime, date
    from flask import Flask, render_template, request, jsonify, Response, send_file
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    app = Flask(__name__)

    # Base directory & DB configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLITE_DB_PATH = os.path.join(BASE_DIR, "trading_tracker.db")

    # Parse DATABASE_URL (Render PostgreSQL)
    RAW_DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://ramote_user:KB6MBdQ5zXkT5zDZ5APXNmBAVgUx6SDZ@dpg-da8k9vijnfac73emabgg-
          a/ramote").strip()
    if RAW_DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = RAW_DATABASE_URL

    USE_POSTGRES = False

    def test_postgres_connection():
        global USE_POSTGRES
        if not DATABASE_URL:
            return False
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=4)
            conn.close()
            USE_POSTGRES = True
            return True
        except Exception as e:
            print(f" [DB WARNING] PostgreSQL connection check failed: {e}")
            USE_POSTGRES = False
            return False

    # Initialize connection mode
    test_postgres_connection()

    TRADING_RULES = [
        {"id": 1, "text": "Don't FOMO", "desc": "Wait patiently for your setup. Do not chase moving candles."},
        {"id": 2, "text": "Don't entry with another signal", "desc": "Trust your own strategy. Never follow random
  caller signals."},
        {"id": 3, "text": "1 Day = 1 or 2 setups maximum", "desc": "Quality over quantity. Strict maximum of 2 trades
  per day."},
        {"id": 4, "text": "Risk minimum 1:2 RR", "desc": "Never take trades below 1:2 Risk to Reward ratio."},
        {"id": 5, "text": "TF 15m Flow + 1m Entry (MSS & TS)", "desc": "Check 15m market structure/flow, drop to 1m
  for Market Structure Shift and Time & Symmetry entry."},
        {"id": 6, "text": "1H Key Level + 5m/3m Entry (MSS)", "desc": "Identify 1H key support/resistance/order block,
  enter on 5m or 3m confirmed MSS."},
        {"id": 7, "text": "4H Key Level + 15m/5m Entry (MSS)", "desc": "Identify 4H major zone, enter on 15m or 5m
  confirmed MSS."},
        {"id": 8, "text": "Daily Target $5-$10 | Max Risk $5 (Stop if -$5)", "desc": "Daily profit goal $5-$10. Max
  daily loss $5. If you lose $5, immediately STOP trading!"}
    ]

    def get_db():
        global USE_POSTGRES
        if USE_POSTGRES and DATABASE_URL:
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(DATABASE_URL)
                return conn, "postgres"
            except Exception as e:
                print(f" [DB ERROR] PostgreSQL reconnect failed ({e}). Falling back to SQLite.")
                USE_POSTGRES = False

        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

    def get_cursor(conn, db_type):
        if db_type == "postgres":
            import psycopg2.extras
            return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn.cursor()

    def serialize_trade(r):
        trade_dict = dict(r)
        if "id" in trade_dict and trade_dict["id"] is not None:
            trade_dict["id"] = int(trade_dict["id"])

        float_fields = [
            "entry_price", "exit_price", "stop_loss", "take_profit",
            "lot_size", "profit_loss", "pips", "rr_ratio", "compliance_rate"
        ]
        for f in float_fields:
            if f in trade_dict and trade_dict[f] is not None:
                try:
                    trade_dict[f] = float(trade_dict[f])
                except (ValueError, TypeError):
                    pass

        if "created_at" in trade_dict and trade_dict["created_at"] is not None:
            if hasattr(trade_dict["created_at"], "isoformat"):
                trade_dict["created_at"] = trade_dict["created_at"].isoformat()
            else:
                trade_dict["created_at"] = str(trade_dict["created_at"])

        if "rules_followed" in trade_dict:
            raw_rules = trade_dict["rules_followed"]
            if isinstance(raw_rules, list):
                trade_dict["rules_followed"] = raw_rules
            elif isinstance(raw_rules, str) and raw_rules.strip():
                try:
                    trade_dict["rules_followed"] = json.loads(raw_rules)
                except Exception:
                    trade_dict["rules_followed"] = []
            else:
                trade_dict["rules_followed"] = []

        return trade_dict

    def init_db():
        global USE_POSTGRES
        defaults = {
            "initial_balance": "100.00",
            "target_balance": "1000.00",
            "daily_profit_target": "10.00",
            "daily_max_loss": "5.00",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "telegram_enabled": "0"
        }

        if DATABASE_URL:
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key VARCHAR(255) PRIMARY KEY,
                        value TEXT
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id SERIAL PRIMARY KEY,
                        trade_date VARCHAR(64) NOT NULL,
                        pair VARCHAR(64) NOT NULL,
                        direction VARCHAR(32) NOT NULL,
                        entry_price DOUBLE PRECISION,
                        exit_price DOUBLE PRECISION,
                        stop_loss DOUBLE PRECISION,
                        take_profit DOUBLE PRECISION,
                        lot_size DOUBLE PRECISION DEFAULT 0.01,
                        profit_loss DOUBLE PRECISION NOT NULL,
                        pips DOUBLE PRECISION DEFAULT 0,
                        setup_type VARCHAR(255) NOT NULL,
                        timeframe VARCHAR(64),
                        rr_ratio DOUBLE PRECISION DEFAULT 2.0,
                        rules_followed TEXT,
                        compliance_rate DOUBLE PRECISION DEFAULT 100.0,
                        notes TEXT,
                        screenshot_url TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                for k, v in defaults.items():
                    cursor.execute(
                        "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
                        (k, v)
                    )

                conn.commit()
                conn.close()
                USE_POSTGRES = True
                print(" [DB OK] PostgreSQL tables and settings initialized successfully.")
                return
            except Exception as e:
                print(f" [DB WARNING] PostgreSQL init failed ({e}). Initializing SQLite fallback.")
                USE_POSTGRES = False

        # SQLite fallback initialization
        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                pair TEXT NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                stop_loss REAL,
                take_profit REAL,
                lot_size REAL DEFAULT 0.01,
                profit_loss REAL NOT NULL,
                pips REAL DEFAULT 0,
                setup_type TEXT NOT NULL,
                timeframe TEXT,
                rr_ratio REAL DEFAULT 2.0,
                rules_followed TEXT,
                compliance_rate REAL DEFAULT 100.0,
                notes TEXT,
                screenshot_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
        conn.close()
        print(" [DB OK] SQLite tables and settings initialized successfully.")

    init_db()

    def get_setting(key, default=""):
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        placeholder = "%s" if db_type == "postgres" else "?"
        cursor.execute(f"SELECT value FROM settings WHERE key = {placeholder}", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row and row["value"] is not None else default

    def set_setting(key, value):
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        if db_type == "postgres":
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.
  value",
                (key, str(value))
            )
        else:
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
        conn.commit()
        conn.close()

    def send_telegram_message(message_text):
        token = get_setting("telegram_bot_token", "").strip()
        chat_id = get_setting("telegram_chat_id", "").strip()
        enabled = get_setting("telegram_enabled", "0") == "1"

        if not enabled or not token or not chat_id:
            return False, "Telegram notifications are disabled or not configured."

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML"
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            data = res.json()
            if res.status_code == 200 and data.get("ok"):
                return True, "Message sent successfully"
            else:
                return False, data.get("description", "Failed to send Telegram message")
        except Exception as e:
            return False, str(e)

    # ----------------- ROUTES ----------------- #

    @app.route("/")
    def index():
        return render_template("index.html", rules=TRADING_RULES)

    @app.route("/api/rules", methods=["GET"])
    def get_rules():
        return jsonify(TRADING_RULES)

    @app.route("/api/db-status", methods=["GET"])
    def db_status():
        global USE_POSTGRES
        return jsonify({
            "db_type": "PostgreSQL (Render)" if USE_POSTGRES else "SQLite (Local)",
            "postgres_active": USE_POSTGRES,
            "database_url_configured": bool(DATABASE_URL)
        })

    @app.route("/api/settings", methods=["GET", "POST"])
    def settings_endpoint():
        if request.method == "GET":
            conn, db_type = get_db()
            cursor = get_cursor(conn, db_type)
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()
            conn.close()
            return jsonify({row["key"]: row["value"] for row in rows})

        data = request.get_json() or {}
        for key, val in data.items():
            set_setting(key, val)
        return jsonify({"status": "success", "message": "Settings updated successfully"})

    @app.route("/api/telegram/test", methods=["POST"])
    def test_telegram():
        data = request.get_json() or {}
        token = data.get("telegram_bot_token") or get_setting("telegram_bot_token", "")
        chat_id = data.get("telegram_chat_id") or get_setting("telegram_chat_id", "")

        if not token or not chat_id:
            return jsonify({"status": "error", "message": "Please provide both Bot Token and Chat ID."}), 400

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        msg = (
            "🤖 <b>RATHA QUANT BOT Connected!</b>\n\n"
            "⚡ Challenge: <b>$100 ➔ $1,000 in 1 Month</b>\n"
            "🎯 Daily Target: <b>$5 - $10</b> | Max Risk: <b>$5</b>\n"
            "🛡️ <i>RATHA discipline protocol & trading alerts are active!</i>"
        )
        payload = {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
        try:
            res = requests.post(url, json=payload, timeout=8)
            data = res.json()
            if res.status_code == 200 and data.get("ok"):
                return jsonify({"status": "success", "message": "Telegram test message sent successfully!"})
            else:
                return jsonify({"status": "error", "message": data.get("description", "Failed to connect to
  Telegram")}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": f"Connection error: {str(e)}"}), 500

    @app.route("/api/trades", methods=["GET", "POST"])
    def trades_endpoint():
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        placeholder = "%s" if db_type == "postgres" else "?"

        if request.method == "GET":
            pair = request.args.get("pair")
            setup = request.args.get("setup")
            outcome = request.args.get("outcome") # win, loss, be
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")

            query = "SELECT * FROM trades WHERE 1=1"
            params = []

            if pair:
                query += f" AND UPPER(pair) LIKE UPPER({placeholder})"
                params.append(f"%{pair.strip()}%")
            if setup:
                query += f" AND setup_type = {placeholder}"
                params.append(setup)
            if start_date:
                query += f" AND trade_date >= {placeholder}"
                params.append(start_date)
            if end_date:
                query += f" AND trade_date <= {placeholder}"
                params.append(end_date)
            if outcome == "win":
                query += " AND profit_loss > 0"
            elif outcome == "loss":
                query += " AND profit_loss < 0"
            elif outcome == "be":
                query += " AND profit_loss = 0"

            query += " ORDER BY trade_date DESC, id DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            trades = [serialize_trade(r) for r in rows]
            conn.close()
            return jsonify(trades)

        elif request.method == "POST":
            data = request.get_json() or {}

            trade_date = data.get("trade_date") or date.today().isoformat()
            pair = (data.get("pair") or "XAUUSD").upper().strip()
            direction = (data.get("direction") or "BUY").upper()
            entry_price = float(data.get("entry_price") or 0)
            exit_price = float(data.get("exit_price") or 0)
            stop_loss = float(data.get("stop_loss") or 0)
            take_profit = float(data.get("take_profit") or 0)
            lot_size = float(data.get("lot_size") or 0.01)
            profit_loss = float(data.get("profit_loss") or 0)
            pips = float(data.get("pips") or 0)
            setup_type = data.get("setup_type") or "15m Flow + 1m Entry (MSS & TS)"
            timeframe = data.get("timeframe") or "15m/1m"
            rr_ratio = float(data.get("rr_ratio") or 2.0)
            rules_followed = data.get("rules_followed") or []
            notes = data.get("notes") or ""
            screenshot_url = data.get("screenshot_url") or ""

            total_rules = len(TRADING_RULES)
            compliance_rate = round((len(rules_followed) / total_rules) * 100.0, 1) if total_rules > 0 else 100.0

            insert_params = (
                trade_date, pair, direction, entry_price, exit_price, stop_loss,
                take_profit, lot_size, profit_loss, pips, setup_type, timeframe,
                rr_ratio, json.dumps(rules_followed), compliance_rate, notes, screenshot_url
            )

            if db_type == "postgres":
                cursor.execute("""
                    INSERT INTO trades (
                        trade_date, pair, direction, entry_price, exit_price, stop_loss,
                        take_profit, lot_size, profit_loss, pips, setup_type, timeframe,
                        rr_ratio, rules_followed, compliance_rate, notes, screenshot_url
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, insert_params)
                inserted_row = cursor.fetchone()
                trade_id = inserted_row["id"] if inserted_row else 0
            else:
                cursor.execute("""
                    INSERT INTO trades (
                        trade_date, pair, direction, entry_price, exit_price, stop_loss,
                        take_profit, lot_size, profit_loss, pips, setup_type, timeframe,
                        rr_ratio, rules_followed, compliance_rate, notes, screenshot_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_params)
                trade_id = cursor.lastrowid

            conn.commit()

            # Calculate stats for Telegram notification
            cursor.execute("SELECT SUM(profit_loss) as total_pl, COUNT(*) as total_count FROM trades")
            overall = cursor.fetchone()
            total_pl = float(overall["total_pl"] or 0.0) if overall else 0.0

            init_bal = float(get_setting("initial_balance", "100"))
            target_bal = float(get_setting("target_balance", "1000"))
            current_bal = init_bal + total_pl
            challenge_progress = round(((current_bal - init_bal) / (target_bal - init_bal)) * 100, 1) if target_bal >
  init_bal else 0

            # Check today's stats
            cursor.execute(f"SELECT SUM(profit_loss) as day_pl, COUNT(*) as day_trades FROM trades WHERE trade_date =
  {placeholder}", (trade_date,))
            day_stat = cursor.fetchone()
            day_pl = float(day_stat["day_pl"] or 0.0) if day_stat else 0.0
            day_trades_count = int(day_stat["day_trades"] or 0) if day_stat else 0

            max_daily_loss = float(get_setting("daily_max_loss", "5.0"))
            stop_trading_alert = day_pl <= -max_daily_loss

            conn.close()

            # Send Telegram notification
            pl_emoji = "🟢 WIN (+$" if profit_loss > 0 else ("🔴 LOSS (-$" if profit_loss < 0 else "⚪ BREAKEVEN ($")
            pl_formatted = f"+${profit_loss:.2f}" if profit_loss > 0 else (f"-${abs(profit_loss):.2f}" if profit_loss
  < 0 else "$0.00")

            tg_msg = (
                f"⚡ <b>NEW TRADE LOGGED</b> ⚡\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 <b>Asset:</b> {pair} (<b>{direction}</b>)\n"
                f"📈 <b>Setup:</b> {setup_type}\n"
                f"💰 <b>P&L:</b> <b>{pl_formatted}</b> ({pl_emoji.split()[0]})\n"
                f"🎯 <b>R:R Ratio:</b> 1:{rr_ratio:.1f}\n"
                f"🛡️ <b>Rules Followed:</b> {len(rules_followed)}/{total_rules} ({compliance_rate}%)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💼 <b>Current Balance:</b> ${current_bal:.2f} / ${target_bal:.2f} ({challenge_progress}%)\n"
                f"📅 <b>Today's P&L:</b> {'+$' if day_pl >= 0 else '-$'}{abs(day_pl):.2f} (Trades:
  {day_trades_count}/2)\n"
            )

            if stop_trading_alert:
                tg_msg += (
                    f"\n🚨 <b>DAILY LOSS LIMIT HIT (${max_daily_loss})!</b> 🚨\n"
                    f"🛑 <b>STOP TRADING FOR TODAY!</b>\n"
                    f"<i>Rule 8 Enforced: Protect your capital and come back tomorrow!</i>"
                )
            elif day_trades_count > 2:
                tg_msg += (
                    f"\n⚠️ <b>RULE 3 WARNING:</b> You took {day_trades_count} trades today (Max recommended is 2)!"
                )

            send_telegram_message(tg_msg)

            return jsonify({
                "status": "success",
                "trade_id": trade_id,
                "message": "Trade logged successfully!",
                "daily_loss_limit_hit": stop_trading_alert,
                "day_trades_count": day_trades_count
            })

    @app.route("/api/trades/<int:trade_id>", methods=["PUT", "DELETE"])
    def trade_detail_endpoint(trade_id):
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        placeholder = "%s" if db_type == "postgres" else "?"

        if request.method == "DELETE":
            cursor.execute(f"DELETE FROM trades WHERE id = {placeholder}", (trade_id,))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Trade deleted successfully"})

        elif request.method == "PUT":
            data = request.get_json() or {}
            trade_date = data.get("trade_date")
            pair = (data.get("pair") or "XAUUSD").upper().strip()
            direction = (data.get("direction") or "BUY").upper()
            entry_price = float(data.get("entry_price") or 0)
            exit_price = float(data.get("exit_price") or 0)
            stop_loss = float(data.get("stop_loss") or 0)
            take_profit = float(data.get("take_profit") or 0)
            lot_size = float(data.get("lot_size") or 0.01)
            profit_loss = float(data.get("profit_loss") or 0)
            pips = float(data.get("pips") or 0)
            setup_type = data.get("setup_type") or "15m Flow + 1m Entry (MSS & TS)"
            timeframe = data.get("timeframe") or "15m/1m"
            rr_ratio = float(data.get("rr_ratio") or 2.0)
            rules_followed = data.get("rules_followed") or []
            notes = data.get("notes") or ""
            screenshot_url = data.get("screenshot_url") or ""

            total_rules = len(TRADING_RULES)
            compliance_rate = round((len(rules_followed) / total_rules) * 100.0, 1) if total_rules > 0 else 100.0

            cursor.execute(f"""
                UPDATE trades SET
                    trade_date = {placeholder}, pair = {placeholder}, direction = {placeholder},
                    entry_price = {placeholder}, exit_price = {placeholder}, stop_loss = {placeholder},
                    take_profit = {placeholder}, lot_size = {placeholder}, profit_loss = {placeholder},
                    pips = {placeholder}, setup_type = {placeholder}, timeframe = {placeholder},
                    rr_ratio = {placeholder}, rules_followed = {placeholder},
                    compliance_rate = {placeholder}, notes = {placeholder}, screenshot_url = {placeholder}
                WHERE id = {placeholder}
            """, (
                trade_date, pair, direction, entry_price, exit_price, stop_loss,
                take_profit, lot_size, profit_loss, pips, setup_type, timeframe,
                rr_ratio, json.dumps(rules_followed), compliance_rate, notes, screenshot_url,
                trade_id
            ))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Trade updated successfully"})

    @app.route("/api/stats", methods=["GET"])
    def get_stats():
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)

        # Settings
        initial_balance = float(get_setting("initial_balance", "100.00"))
        target_balance = float(get_setting("target_balance", "1000.00"))
        daily_profit_target = float(get_setting("daily_profit_target", "10.00"))
        daily_max_loss = float(get_setting("daily_max_loss", "5.00"))

        cursor.execute("SELECT * FROM trades ORDER BY trade_date ASC, id ASC")
        raw_trades = cursor.fetchall()
        conn.close()

        trades = [serialize_trade(t) for t in raw_trades]

        total_trades = len(trades)
        total_pl = 0.0
        wins = 0
        losses = 0
        breakevens = 0
        gross_profit = 0.0
        gross_loss = 0.0
        total_rr = 0.0
        total_compliance = 0.0

        equity_curve = [{"date": "Start", "balance": initial_balance, "pl": 0.0, "cum_pl": 0.0}]
        running_balance = initial_balance

        daily_pl_map = {}
        setup_stats_map = {}
        pair_stats_map = {}
        rule_adherence_wins = {"full_compliant": {"wins": 0, "total": 0}, "broken_rules": {"wins": 0, "total": 0}}

        today_str = date.today().isoformat()
        today_pl = 0.0
        today_trades_count = 0

        for t in trades:
            pl = float(t.get("profit_loss") or 0.0)
            total_pl += pl
            running_balance += pl
            total_rr += float(t.get("rr_ratio") or 0.0)
            total_compliance += float(t.get("compliance_rate") or 0.0)

            t_date = str(t.get("trade_date") or "")

            # Today tracking
            if t_date == today_str:
                today_pl += pl
                today_trades_count += 1

            # Outcomes
            if pl > 0:
                wins += 1
                gross_profit += pl
            elif pl < 0:
                losses += 1
                gross_loss += abs(pl)
            else:
                breakevens += 1

            # Equity curve
            equity_curve.append({
                "date": t_date,
                "trade_id": t["id"],
                "pair": t["pair"],
                "balance": round(running_balance, 2),
                "pl": round(pl, 2),
                "cum_pl": round(total_pl, 2)
            })

            # Daily breakdown
            if t_date not in daily_pl_map:
                daily_pl_map[t_date] = {"pl": 0.0, "trades": 0, "wins": 0, "losses": 0}
            daily_pl_map[t_date]["pl"] += pl
            daily_pl_map[t_date]["trades"] += 1
            if pl > 0:
                daily_pl_map[t_date]["wins"] += 1
            elif pl < 0:
                daily_pl_map[t_date]["losses"] += 1

            # Setup breakdown
            setup = t.get("setup_type") or "Other"
            if setup not in setup_stats_map:
                setup_stats_map[setup] = {"trades": 0, "wins": 0, "pl": 0.0}
            setup_stats_map[setup]["trades"] += 1
            setup_stats_map[setup]["pl"] += pl
            if pl > 0:
                setup_stats_map[setup]["wins"] += 1

            # Pair breakdown
            pair = t.get("pair") or "Unknown"
            if pair not in pair_stats_map:
                pair_stats_map[pair] = {"trades": 0, "wins": 0, "pl": 0.0}
            pair_stats_map[pair]["trades"] += 1
            pair_stats_map[pair]["pl"] += pl
            if pl > 0:
                pair_stats_map[pair]["wins"] += 1

            # Discipline correlation
            compliance = float(t.get("compliance_rate") or 0.0)
            if compliance >= 100.0:
                rule_adherence_wins["full_compliant"]["total"] += 1
                if pl > 0:
                    rule_adherence_wins["full_compliant"]["wins"] += 1
            else:
                rule_adherence_wins["broken_rules"]["total"] += 1
                if pl > 0:
                    rule_adherence_wins["broken_rules"]["wins"] += 1

        current_balance = initial_balance + total_pl
        win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if
  gross_profit > 0 else 1.0)
        avg_win = round(gross_profit / wins, 2) if wins > 0 else 0.0
        avg_loss = round(gross_loss / losses, 2) if losses > 0 else 0.0
        avg_rr = round(total_rr / total_trades, 2) if total_trades > 0 else 0.0
        avg_compliance = round(total_compliance / total_trades, 1) if total_trades > 0 else 100.0

        # Challenge progress percentage
        progress_pct = round(((current_balance - initial_balance) / (target_balance - initial_balance)) * 100, 1) if
  (target_balance - initial_balance) > 0 else 0.0
        progress_pct = max(0.0, min(100.0, progress_pct))

        # Stop trading check (Rule 8)
        daily_stop_loss_hit = today_pl <= -daily_max_loss

        # Format daily P&L list
        daily_pnl_list = [
            {"date": d, "pl": round(data["pl"], 2), "trades": data["trades"], "wins": data["wins"], "losses":
  data["losses"]}
            for d, data in sorted(daily_pl_map.items())
        ]

        return jsonify({
            "account": {
                "initial_balance": initial_balance,
                "target_balance": target_balance,
                "current_balance": round(current_balance, 2),
                "total_pl": round(total_pl, 2),
                "progress_pct": progress_pct,
                "remaining_to_goal": round(max(0.0, target_balance - current_balance), 2),
                "daily_profit_target": daily_profit_target,
                "daily_max_loss": daily_max_loss
            },
            "performance": {
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "breakevens": breakevens,
                "win_rate": win_rate,
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "profit_factor": profit_factor,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "avg_rr": avg_rr,
                "avg_compliance": avg_compliance
            },
            "today": {
                "date": today_str,
                "pl": round(today_pl, 2),
                "trades_count": today_trades_count,
                "stop_loss_hit": daily_stop_loss_hit,
                "max_trades_warning": today_trades_count >= 2,
                "target_achieved": today_pl >= daily_profit_target
            },
            "charts": {
                "equity_curve": equity_curve,
                "daily_pnl": daily_pnl_list,
                "setups": setup_stats_map,
                "pairs": pair_stats_map,
                "discipline": rule_adherence_wins
            }
        })

    @app.route("/api/export", methods=["GET"])
    def export_csv():
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        cursor.execute("SELECT * FROM trades ORDER BY trade_date ASC, id ASC")
        rows = cursor.fetchall()
        conn.close()

        trades = [serialize_trade(r) for r in rows]

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "ID", "Date", "Pair", "Direction", "Entry Price", "Exit Price", "Stop Loss",
            "Take Profit", "Lot Size", "Profit/Loss ($)", "Pips", "Setup Type",
            "Timeframe", "R:R Ratio", "Compliance (%)", "Notes", "Screenshot URL"
        ])

        for r in trades:
            writer.writerow([
                r.get("id"), r.get("trade_date"), r.get("pair"), r.get("direction"),
                r.get("entry_price"), r.get("exit_price"), r.get("stop_loss"),
                r.get("take_profit"), r.get("lot_size"), r.get("profit_loss"),
                r.get("pips"), r.get("setup_type"), r.get("timeframe"),
                r.get("rr_ratio"), r.get("compliance_rate"), r.get("notes"),
                r.get("screenshot_url")
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=trades_history.csv"}
        )

    @app.route("/api/seed", methods=["POST"])
    def seed_sample_data():
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        placeholder = "%s" if db_type == "postgres" else "?"

        cursor.execute("DELETE FROM trades")

        sample_trades = [
            ("2026-08-20", "XAUUSD", "BUY", 2480.50, 2492.50, 2475.00, 2495.00, 0.01, 12.00, 120, "15m Flow + 1m Entry
  (MSS & TS)", "15m/1m", 2.2, json.dumps([1,2,3,4,5,8]), 75.0, "Perfect MSS on 1m after 15m sweep. Clean run.", ""),
            ("2026-08-21", "EURUSD", "SELL", 1.09200, 1.09000, 1.09300, 1.08900, 0.02, 4.00, 20, "1H Key Level + 5m/3m
  Entry (MSS)", "1H/5m", 2.0, json.dumps([1,2,3,4,6,8]), 75.0, "1H resistance tapped, entered 5m MSS.", ""),
            ("2026-08-22", "BTCUSDT", "BUY", 64200.0, 63850.0, 63800.0, 65000.0, 0.01, -4.50, -350, "4H Key Level +
  15m/5m Entry (MSS)", "4H/15m", 2.0, json.dumps([1,2,3,4,7,8]), 75.0, "Stopped out right before reversal. Followed $5
  max risk rule.", ""),
            ("2026-08-24", "XAUUSD", "BUY", 2502.00, 2515.00, 2496.00, 2520.00, 0.01, 13.00, 130, "15m Flow + 1m Entry
  (MSS & TS)", "15m/1m", 2.5, json.dumps([1,2,3,4,5,8]), 75.0, "High conviction MSS + TS session open trade.", ""),
            ("2026-08-25", "US30", "SELL", 41200.0, 41050.0, 41270.0, 40900.0, 0.01, 15.00, 150, "1H Key Level + 5m/3m
  Entry (MSS)", "1H/3m", 2.1, json.dumps([1,2,3,4,6,8]), 75.0, "Clean breakdown after liquidity grab at 1H high.", ""),
            ("2026-08-26", "GBPUSD", "BUY", 1.31500, 1.31250, 1.31200, 1.32100, 0.02, -5.00, -25, "15m Flow + 1m Entry
  (MSS & TS)", "15m/1m", 2.0, json.dumps([1,2,3,4,5,8]), 75.0, "Loss hit max $5 risk stop. Stopped immediately.", ""),
            ("2026-08-27", "XAUUSD", "SELL", 2525.00, 2512.00, 2530.00, 2505.00, 0.01, 13.00, 130, "4H Key Level +
  15m/5m Entry (MSS)", "4H/15m", 2.6, json.dumps([1,2,3,4,7,8]), 75.0, "4H supply reaction. Hit TP easily.", ""),
            ("2026-08-28", "EURUSD", "BUY", 1.08500, 1.09000, 1.08250, 1.09100, 0.02, 10.00, 50, "15m Flow + 1m Entry
  (MSS & TS)", "15m/1m", 2.0, json.dumps([1,2,3,4,5,8]), 75.0, "London session continuation trade.", "")
        ]

        insert_sql = f"""
            INSERT INTO trades (
                trade_date, pair, direction, entry_price, exit_price, stop_loss,
                take_profit, lot_size, profit_loss, pips, setup_type, timeframe,
                rr_ratio, rules_followed, compliance_rate, notes, screenshot_url
            ) VALUES ({','.join([placeholder]*17)})
        """
        for t in sample_trades:
            cursor.execute(insert_sql, t)

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Demo sample trades loaded successfully!"})

    @app.route("/api/reset", methods=["POST"])
    def reset_data():
        conn, db_type = get_db()
        cursor = get_cursor(conn, db_type)
        cursor.execute("DELETE FROM trades")
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "All trades cleared. Fresh state ready!"})

    if __name__ == "__main__":
        print("==================================================")
        print(" [OK] RATHA QUANT TRADING TRACKER STARTED")
        print(f" [*] Database Mode: {'PostgreSQL (Render)' if USE_POSTGRES else 'SQLite (Local)'}")
        print(" [*] URL: http://127.0.0.1:5000")
        print(" [*] Challenge: $100 -> $1,000 in 1 Month")
        print(" [*] Rules: 8 Strict Trading Discipline Rules Active")
        print("==================================================")
        app.run(host="0.0.0.0", port=5000, debug=True)
