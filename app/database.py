"""
SQLite Database Storage Layer for Ola Scooter Telemetry & Security
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger("database")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
DB_PATH = os.path.join(DB_DIR, "scooter.db")

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Scooter Devices
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scooter_devices (
                address TEXT PRIMARY KEY,
                name TEXT,
                last_seen TEXT,
                rssi INTEGER,
                is_paired INTEGER DEFAULT 0
            )
            """)

            # 2. Status History
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS scooter_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                battery_percent INTEGER,
                range_km INTEGER,
                charging INTEGER,
                lock_status TEXT,
                speed REAL,
                odometer REAL,
                rssi INTEGER
            )
            """)

            # 3. Battery History (for graphs)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS battery_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                battery_percent INTEGER,
                range_km INTEGER,
                charging INTEGER
            )
            """)

            # 4. Charging Sessions
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS charging_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                start_battery INTEGER,
                end_battery INTEGER,
                duration_minutes REAL
            )
            """)

            # 5. Bluetooth Events
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS bluetooth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT
            )
            """)

            # 6. Command History / Audit Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                command TEXT NOT NULL,
                username TEXT,
                success INTEGER,
                error_message TEXT
            )
            """)

            # 7. Local Users & Auth
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                pin_hash TEXT,
                created_at TEXT NOT NULL
            )
            """)

            # 8. Key-Value Settings
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            conn.commit()

            # Create default admin user if none exists
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
            if cursor.fetchone()["cnt"] == 0:
                self.create_user("admin", "admin123", "1234")
                logger.info("Initialized default user: admin / admin123 (PIN: 1234)")

    # User Management
    def create_user(self, username: str, password: str, pin: Optional[str] = None):
        pw_hash = generate_password_hash(password)
        pin_hash = generate_password_hash(pin) if pin else None
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.cursor().execute("""
                INSERT OR REPLACE INTO users (username, password_hash, pin_hash, created_at)
                VALUES (?, ?, ?, ?)
            """, (username, pw_hash, pin_hash, now))
            conn.commit()

    def verify_user(self, username: str, password: str) -> bool:
        with self.get_connection() as conn:
            row = conn.cursor().execute("SELECT password_hash FROM users WHERE username = ?", (username,)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                return True
        return False

    def verify_pin(self, username: str, pin: str) -> bool:
        with self.get_connection() as conn:
            row = conn.cursor().execute("SELECT pin_hash FROM users WHERE username = ?", (username,)).fetchone()
            if row and row["pin_hash"]:
                return check_password_hash(row["pin_hash"], pin)
            # If no PIN configured, treat as valid
            return True

    # Telemetry & History logging
    def log_status(self, status):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scooter_status_history 
                (timestamp, battery_percent, range_km, charging, lock_status, speed, odometer, rssi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                status.battery_percent,
                status.estimated_range_km,
                1 if status.charging else 0,
                status.lock_status,
                status.speed_kmh,
                status.odometer_km,
                status.rssi
            ))

            if status.battery_percent is not None:
                cur.execute("""
                    INSERT INTO battery_history (timestamp, battery_percent, range_km, charging)
                    VALUES (?, ?, ?, ?)
                """, (now, status.battery_percent, status.estimated_range_km, 1 if status.charging else 0))

            conn.commit()

    def log_command(self, command: str, username: str, success: bool, error: Optional[str] = None):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO command_history (timestamp, command, username, success, error_message)
                VALUES (?, ?, ?, ?, ?)
            """, (now, command, username, 1 if success else 0, error))
            conn.commit()

    def log_event(self, event_type: str, details: str = ""):
        now = datetime.now().isoformat()
        with self.get_connection() as conn:
            conn.cursor().execute("""
                INSERT INTO bluetooth_events (timestamp, event_type, details)
                VALUES (?, ?, ?)
            """, (now, event_type, details))
            conn.commit()

    # Query Helpers for Dashboards
    def get_battery_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.cursor().execute("""
                SELECT timestamp, battery_percent, range_km, charging
                FROM battery_history
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in reversed(rows)]

    def get_charging_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.cursor().execute("""
                SELECT id, start_time, end_time, start_battery, end_battery, duration_minutes
                FROM charging_sessions
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.cursor().execute("""
                SELECT timestamp, command, username, success, error_message
                FROM command_history
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def clear_history(self):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM scooter_status_history")
            cur.execute("DELETE FROM battery_history")
            cur.execute("DELETE FROM charging_sessions")
            cur.execute("DELETE FROM command_history")
            cur.execute("DELETE FROM bluetooth_events")
            conn.commit()
