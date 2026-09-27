"""
Flask Application Factory for Ola Scooter Web Controller
"""

import os
import yaml
import logging
from flask import Flask
from app.database import Database
from app.bluetooth.manager import ScooterBluetooth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

def create_app(config_path: str = "config.yaml", simulation_mode: bool = False) -> Flask:
    app = Flask(__name__)

    # Load YAML Configuration
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    app.config["APP_CONFIG"] = cfg
    app.config["SECRET_KEY"] = cfg.get("server", {}).get("secret_key", "dev-secret-key-pi")

    # Initialize SQLite Database
    db = Database()
    app.config["DB"] = db

    # Initialize Scooter Bluetooth Manager
    bt_manager = ScooterBluetooth(config=cfg, simulation_mode=simulation_mode)
    app.config["BLUETOOTH"] = bt_manager

    # Periodic DB telemetry logger listener
    def db_status_listener(status):
        if status.connected:
            try:
                db.log_status(status)
            except Exception as e:
                logger.error(f"Failed to log telemetry to DB: {e}")

    bt_manager.add_listener(db_status_listener)
    bt_manager.start()

    # Register Blueprints
    from app.routes import web, api
    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix="/api")

    logger.info(f"Ola Scooter Web App initialized (Simulation: {simulation_mode})")
    return app
