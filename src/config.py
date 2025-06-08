# src/config.py
import os
from dotenv import load_dotenv

class ConfigManager:
    def __init__(self):
        load_dotenv() # Load environment variables from .env file

        def get_env_var(var_name, default=None):
            """Helper to get, clean, and strip environment variables."""
            value = os.getenv(var_name, default)
            if value:
                return value.split('#')[0].strip()
            return None

        # --- API Application Credentials (from SmartAPI Dashboard) ---
        self.api_key = get_env_var("ANGELONE_CLIENT_ID")
        self.client_secret = get_env_var("ANGELONE_CLIENT_SECRET")
        self.redirect_uri = get_env_var("ANGELONE_REDIRECT_URI")

        # --- Angel One Trading Account Login Credentials ---
        self.username = get_env_var("ANGELONE_USERNAME") # Your Angel One login ID (e.g., A58519592)
        # self.password = os.getenv("ANGELONE_PASSWORD") # Your Angel One login password
        self.pin = get_env_var("ANGELONE_PIN")           # <-- ADD THIS NEW LINE (this will hold your MPIN)

        self.totp_secret = get_env_var("ANGELONE_TOTP_SECRET")

        # --- Path to Scrip Master File ---
        # Ensure you have SCRIP_MASTER_PATH in your .env or adjust the default.
        self.scrip_master_path = get_env_var("SCRIP_MASTER_PATH", "OpenAPIScripMaster.json")


        # --- Paper Trading Settings ---
        self.funds_available = float(get_env_var("DEMO_FUNDS", "60000.0")) # Default 60k
        self.paper_trading_mode = True # Set to False for live trading later

        # --- Data Logging Settings ---
        self.trade_logs_file = "trade_logs.csv" # Or JSON, etc.

        # Add other configurations here as needed
        if not all([self.api_key, self.client_secret, self.redirect_uri,
                    self.username, self.pin, self.totp_secret]):
            raise ValueError("Missing one or more Angel One API/Login credentials in .env file. Please check ANGELONE_CLIENT_ID, ANGELONE_CLIENT_SECRET, ANGELONE_USERNAME, ANGELONE_PIN, ANGELONE_TOTP_SECRET, ANGELONE_REDIRECT_URI.")

    def is_paper_trading(self):
        return self.paper_trading_mode