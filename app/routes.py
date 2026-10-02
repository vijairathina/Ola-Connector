"""
Flask Web Application Routes and REST API Endpoints
"""

import os
import json
import time
import io
import csv
import yaml
from datetime import datetime
from functools import wraps
from flask import (
    Blueprint, render_template, request, jsonify, session,
    redirect, url_for, flash, Response, current_app
)

api = Blueprint("api", __name__)
web = Blueprint("web", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            return redirect(url_for("web.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------
# WEB PAGES
# -------------------------------------------------------------
@web.route("/")
def index():
    if "user" in session:
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))

@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = current_app.config["DB"]

        if db.verify_user(username, password):
            session["user"] = username
            flash("Welcome back!", "success")
            next_url = request.args.get("next") or url_for("web.dashboard")
            return redirect(next_url)
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@web.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("web.login"))

@web.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=session.get("user"))

@web.route("/history")
@login_required
def history():
    return render_template("history.html", user=session.get("user"))

@web.route("/settings")
@login_required
def settings():
    cfg = current_app.config["APP_CONFIG"]
    return render_template("settings.html", user=session.get("user"), config=cfg)

# -------------------------------------------------------------
# REST API: TELEMETRY & STATUS
# -------------------------------------------------------------
@api.route("/scooter/status")
@login_required
def get_status():
    bt = current_app.config["BLUETOOTH"]
    return jsonify(bt.get_status().to_dict())

@api.route("/scooter/battery")
@login_required
def get_battery():
    bt = current_app.config["BLUETOOTH"]
    status = bt.get_status()
    return jsonify({
        "connected": status.connected,
        "battery_percent": status.battery_percent,
        "estimated_range_km": status.estimated_range_km,
        "last_updated": status.last_updated
    })

@api.route("/scooter/range")
@login_required
def get_range():
    bt = current_app.config["BLUETOOTH"]
    status = bt.get_status()
    return jsonify({
        "connected": status.connected,
        "estimated_range_km": status.estimated_range_km,
        "mode": status.driving_mode
    })

@api.route("/scooter/charging")
@login_required
def get_charging():
    bt = current_app.config["BLUETOOTH"]
    status = bt.get_status()
    return jsonify({
        "connected": status.connected,
        "charging": status.charging,
        "charging_percent": status.charging_percent,
        "time_to_full_charge_min": status.time_to_full_charge_min
    })

@api.route("/scooter/connection")
@login_required
def get_connection():
    bt = current_app.config["BLUETOOTH"]
    status = bt.get_status()
    return jsonify({
        "connected": status.connected,
        "device_name": status.device_name,
        "device_address": status.device_address,
        "rssi": status.rssi,
        "is_simulated": status.is_simulated,
        "last_updated": status.last_updated
    })

# -------------------------------------------------------------
# REST API: LIVE SERVER-SENT EVENTS (SSE)
# -------------------------------------------------------------
@api.route("/scooter/events")
@login_required
def sse_events():
    bt = current_app.config["BLUETOOTH"]

    def stream():
        import queue
        q = queue.Queue(maxsize=20)

        def listener(status):
            try:
                q.put_nowait(status.to_dict())
            except queue.Full:
                pass

        bt.add_listener(listener)
        # Send current status initially
        initial_data = json.dumps(bt.get_status().to_dict())
        yield f"data: {initial_data}\n\n"

        try:
            while True:
                try:
                    data = q.get(timeout=25)
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    # Keep-alive heartbeat comment
                    yield ": keepalive\n\n"
        finally:
            bt.remove_listener(listener)

    return Response(stream(), mimetype="text/event-stream")

# -------------------------------------------------------------
# REST API: BLE DISCOVERY & CONNECTION MANAGEMENT
# -------------------------------------------------------------
@api.route("/scooter/scan", methods=["GET"])
@login_required
def scan_scooters():
    bt = current_app.config["BLUETOOTH"]
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        devices = loop.run_until_complete(bt.scan())
        return jsonify({
            "success": True,
            "devices": [d.to_dict() for d in devices]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

@api.route("/scooter/connect", methods=["POST"])
@login_required
def connect_scooter():
    bt = current_app.config["BLUETOOTH"]
    db = current_app.config["DB"]
    data = request.get_json() or {}
    address = data.get("address") or bt.target_address

    if not address:
        return jsonify({"success": False, "error": "No device address specified"}), 400

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        success = loop.run_until_complete(bt.connect(address))
        db.log_event("CONNECT", f"Address: {address}, Success: {success}")
        return jsonify({
            "success": success,
            "connected": bt.status.connected,
            "address": address
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

@api.route("/scooter/disconnect", methods=["POST"])
@login_required
def disconnect_scooter():
    bt = current_app.config["BLUETOOTH"]
    db = current_app.config["DB"]
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        success = loop.run_until_complete(bt.disconnect())
        db.log_event("DISCONNECT", "Manual disconnect from dashboard")
        return jsonify({"success": success, "connected": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

@api.route("/scooter/feed_packet", methods=["POST"])
@login_required
def feed_telemetry_packet():
    bt = current_app.config["BLUETOOTH"]
    db = current_app.config["DB"]
    data = request.get_json(silent=True) or {}
    hex_str = (data.get("hex") or "").strip().replace(" ", "").replace(":", "")
    if not hex_str:
        logger.warning(f"feed_packet: missing or empty hex string, data={data}")
        return jsonify({"success": False, "error": "No hex payload provided"}), 400
    try:
        raw_bytes = bytes.fromhex(hex_str)
        name = data.get("name", "OLAS1")
        addr = data.get("address", "87:1A:44:60:00:28")
        bt.ingest_telemetry_bytes(raw_bytes, device_name=name, address=addr)
        db.save_status(bt.status)
        logger.info(f"Successfully ingested telemetry packet: {hex_str[:20]}... (Len: {len(raw_bytes)})")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"feed_packet parsing error: {e}, hex={hex_str}")
        return jsonify({"success": False, "error": str(e)}), 400

# -------------------------------------------------------------
# REST API: VEHICLE CONTROL COMMANDS (AUDITED & PIN GATED)
# -------------------------------------------------------------
def _validate_command_request():
    cfg = current_app.config["APP_CONFIG"]
    db = current_app.config["DB"]
    req = request.get_json() or {}

    if not cfg.get("security", {}).get("remote_commands_enabled", True):
        return False, "Remote vehicle commands are currently disabled in Settings."

    if cfg.get("security", {}).get("require_pin", True):
        pin = req.get("pin")
        if not pin or not db.verify_pin(session.get("user", "admin"), pin):
            return False, "Invalid or missing vehicle security PIN."

    if not req.get("confirmed"):
        return False, "Command confirmation is required."

    return True, None

@api.route("/scooter/lock", methods=["POST"])
@login_required
def lock_scooter():
    bt = current_app.config["BLUETOOTH"]
    db = current_app.config["DB"]
    user = session.get("user", "unknown")

    valid, err = _validate_command_request()
    if not valid:
        db.log_command("LOCK", user, False, err)
        return jsonify({"success": False, "error": err}), 400

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        success = loop.run_until_complete(bt.lock())
        db.log_command("LOCK", user, success)
        return jsonify({
            "success": success,
            "command": "lock",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        db.log_command("LOCK", user, False, str(e))
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

@api.route("/scooter/unlock", methods=["POST"])
@login_required
def unlock_scooter():
    bt = current_app.config["BLUETOOTH"]
    db = current_app.config["DB"]
    user = session.get("user", "unknown")

    valid, err = _validate_command_request()
    if not valid:
        db.log_command("UNLOCK", user, False, err)
        return jsonify({"success": False, "error": err}), 400

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        success = loop.run_until_complete(bt.unlock())
        db.log_command("UNLOCK", user, success)
        return jsonify({
            "success": success,
            "command": "unlock",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        db.log_command("UNLOCK", user, False, str(e))
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()

@api.route("/scooter/simulation/toggle_charging", methods=["POST"])
@login_required
def toggle_simulation_charging():
    bt = current_app.config["BLUETOOTH"]
    data = request.get_json() or {}
    enable = data.get("enable", not bt.status.charging)
    bt.toggle_simulation_charging(enable)
    return jsonify({
        "success": True,
        "charging": bt.status.charging
    })

# -------------------------------------------------------------
# REST API: HISTORY & SETTINGS
# -------------------------------------------------------------
@api.route("/history/battery")
@login_required
def get_battery_history():
    db = current_app.config["DB"]
    limit = int(request.args.get("limit", 100))
    return jsonify(db.get_battery_history(limit))

@api.route("/history/charging")
@login_required
def get_charging_history():
    db = current_app.config["DB"]
    limit = int(request.args.get("limit", 20))
    return jsonify(db.get_charging_sessions(limit))

@api.route("/history/commands")
@login_required
def get_command_history():
    db = current_app.config["DB"]
    limit = int(request.args.get("limit", 50))
    return jsonify(db.get_command_history(limit))

@api.route("/history/clear", methods=["POST"])
@login_required
def clear_history():
    db = current_app.config["DB"]
    db.clear_history()
    return jsonify({"success": True, "message": "History cleared"})

@api.route("/history/export_csv")
@login_required
def export_csv():
    db = current_app.config["DB"]
    history = db.get_battery_history(1000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Battery %", "Range (km)", "Charging"])
    for row in history:
        writer.writerow([row["timestamp"], row["battery_percent"], row["range_km"], row["charging"]])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=scooter_battery_history.csv"}
    )

@api.route("/settings/update", methods=["POST"])
@login_required
def update_settings():
    db = current_app.config["DB"]
    cfg = current_app.config["APP_CONFIG"]
    form = request.form

    # Update security PIN or password
    new_pw = form.get("new_password")
    new_pin = form.get("new_pin")
    if new_pw:
        db.create_user(session.get("user", "admin"), new_pw, new_pin)
    elif new_pin:
        # update pin
        with db.get_connection() as conn:
            from werkzeug.security import generate_password_hash
            conn.cursor().execute("UPDATE users SET pin_hash = ? WHERE username = ?", (generate_password_hash(new_pin), session.get("user")))
            conn.commit()

    # Update YAML settings
    cfg["bluetooth"]["device_address"] = form.get("device_address", cfg["bluetooth"]["device_address"])
    cfg["bluetooth"]["auto_connect"] = form.get("auto_connect") == "on"
    cfg["bluetooth"]["reconnect"] = form.get("reconnect") == "on"
    cfg["security"]["remote_commands_enabled"] = form.get("remote_commands_enabled") == "on"
    cfg["security"]["require_pin"] = form.get("require_pin") == "on"

    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    try:
        with open(config_path, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False)
        flash("Settings saved successfully.", "success")
    except Exception as e:
        flash(f"Error saving config file: {e}", "danger")

    return redirect(url_for("web.settings"))
