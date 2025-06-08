# src/api.py
from SmartApi import SmartConnect
import pyotp
import datetime
import logging
import os 
import json

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("api_debug.log"),
                        logging.StreamHandler()
                    ])

class AngelOneAPI:
    def __init__(self, config_manager):
        self.config = config_manager
        self.smartapi = None
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        self.session_expiry_time = None
        self.scrip_data = None # Initialize scrip_data
        self._scrip_data_by_token = None # Initialize _scrip_data_by_token

    def login(self): 
        """
        Logs into the Angel One SmartAPI and obtains session tokens.
        """
        try:
            # 1. Initialize SmartConnect with the API Key from the dashboard
            self.smartapi = SmartConnect(api_key=self.config.api_key,)
            logging.info("SmartConnect instance created with API Key.")

            # 2. Generate TOTP
            totp = pyotp.TOTP(self.config.totp_secret).now()
            logging.info(f"TOTP generated: {totp}")

            # 3. Perform login using Angel One trading account username, password, and TOTP
            data = self.smartapi.generateSession(self.config.username, self.config.pin, totp)
            logging.info(f"Angel One login response: {data}")

            if data and data.get("status"):
                self.jwt_token = data['data']['jwtToken']
                self.refresh_token = data['data']['refreshToken']
                self.feed_token = data['data']['feedToken']
                # Token usually valid for a day, adjust if SmartAPI docs say otherwise
                self.session_expiry_time = datetime.datetime.now() + datetime.timedelta(hours=24) 

                logging.info("Login successful! Tokens obtained.")
                logging.info(f"JWT Token: {self.jwt_token[:10]}...")
                logging.info(f"Feed Token: {self.feed_token}")
                return True
            else:
                error_message = data.get("message", "Unknown login error")
                logging.error(f"Login failed: {error_message}")
                logging.error(f"Full response: {data}")
                return False

        except Exception as e:
            logging.error(f"An error occurred during Angel One login: {e}")
            return False

    def logout(self):
        """
        Logs out from the Angel One SmartAPI session.
        """
        if self.smartapi:
            try:
                self.smartapi.terminateSession(self.config.username) # Use username for termination
                logging.info("Logged out from Angel One SmartAPI.")
            except Exception as e:
                logging.error(f"Error during Angel One logout: {e}")
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        self.session_expiry_time = None
        self.smartapi = None

    def is_logged_in(self):
        """Checks if the bot is currently logged in and session is not expired."""
        if not self.jwt_token or not self.feed_token or not self.smartapi:
            return False
        if self.session_expiry_time and datetime.datetime.now() > self.session_expiry_time:
            logging.warning("Angel One session token expired. Re-login required.")
            return False
        return True
    
    def load_scrip_master(self):
        """
        Loads the scrip master JSON file from the path specified in ConfigManager
        and stores it in self.scrip_data for quick lookup. This file is large,
        so it should be loaded once.
        Returns:
            bool: True if scrip master is loaded successfully, False otherwise.
        """
        if self.scrip_data: # Check if data is already loaded
            logging.info("Scrip master already loaded.")
            return True

        scrip_path = self.config.scrip_master_path
        try:
            if not os.path.exists(scrip_path):
                logging.error(f"Scrip master file not found at {scrip_path}. Please download it from: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
                return False

            logging.info(f"Loading scrip master from {scrip_path}...")
            with open(scrip_path, 'r') as f:
                raw_data = json.load(f)

            # Optimizing lookup: Store as {symbol: {token, exch_seg, name}}
            # We are assuming 'symbol' in the JSON is sufficient for lookup.
            # If Angel One uses 'SYMBOL-EQ' for equities in the master,
            # you might need to adjust your basket symbols accordingly.
            self.scrip_data = {
                entry.get('symbol'): { # Use .get() for safety
                    'token': entry.get('token'),
                    'exch_seg': entry.get('exch_seg'),
                    'name': entry.get('name')
                }
                for entry in raw_data
                if all(k in entry for k in ['symbol', 'token', 'exch_seg', 'name']) # Ensure all keys exist
            }
            # Also add an alternative lookup by token if needed later
            self._scrip_data_by_token = {
                entry.get('token'): {
                    'symbol': entry.get('symbol'),
                    'exch_seg': entry.get('exch_seg'),
                    'name': entry.get('name')
                }
                for entry in raw_data
                if all(k in entry for k in ['symbol', 'token', 'exch_seg', 'name'])
            }
            logging.info(f"Scrip master loaded with {len(self.scrip_data)} entries.")
            return True
        except FileNotFoundError:
            logging.error(f"Scrip master file not found at {scrip_path}. Please verify path and file existence.")
            return False
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding scrip master JSON from {scrip_path}: {e}", exc_info=True)
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred loading scrip master from {scrip_path}: {e}", exc_info=True)
            return False

    def get_token_by_symbol(self, symbol: str, exchange_segment: str = 'NSE'):
        """
        Looks up the token and exchange segment for a given stock symbol.
        Defaults to 'NSE' for equity segment.
        Args:
            symbol (str): The human-readable stock symbol (e.g., 'RELIANCE', 'TCS').
            exchange_segment (str): The exchange segment (e.g., 'NSE', 'BSE', 'NFO'). Defaults to 'NSE'.
        Returns:
            dict: A dictionary {'token': '...', 'exchange': '...'} if found, None otherwise.
        """
        if not self.scrip_data:
            logging.error("Scrip master data not loaded. Call load_scrip_master() first.")
            return None

        # Angel One scrip master might use 'SYMBOL-EQ' for equity.
        # It's safest to iterate and find the best match.
        # Or, if you know the exact symbol as it appears in the JSON, use direct lookup.
        
        # Let's refine the search for robustness:
        # We'll prioritize exact match, then symbol + -EQ match.
        
        target_symbol_exact = symbol.upper()
        target_symbol_eq = f"{symbol.upper()}-EQ"

        found_info = None

        # Check for exact match in the symbol field and correct exchange segment
        if target_symbol_exact in self.scrip_data:
            data = self.scrip_data[target_symbol_exact]
            if data['exch_seg'] == exchange_segment:
                found_info = data
        
        # If not found, check for SYMBOL-EQ format
        if not found_info and target_symbol_eq in self.scrip_data:
            data = self.scrip_data[target_symbol_eq]
            if data['exch_seg'] == exchange_segment:
                found_info = data
        
        if found_info:
            logging.info(f"Found token {found_info['token']} for {symbol} on {exchange_segment}.")
            return {'token': found_info['token'], 'exchange': found_info['exch_seg']}
        else:
            logging.warning(f"Symbol '{symbol}' not found in '{exchange_segment}' segment (checked exact and -EQ forms).")
            return None


    def get_market_data(self, exchange: str, symbol_token: str, mode: str = "FULL"):
        """
        Fetches market data for a given symbol token.
        Args:
            exchange (str): The exchange type (e.g., "NSE", "BSE", "NFO").
            symbol_token (str): The unique scrip token for the instrument.
            mode (str): The data mode ("LTP", "OHLC", or "FULL"). Defaults to "FULL".
        Returns:
            dict: A dictionary containing market data if successful, None otherwise.
        """
        if not self.is_logged_in():
            logging.error("Not logged in to Angel One. Cannot fetch market data.")
            return None

        try:
            payload = {
                "mode": mode,
                "exchangeType": exchange,
                "scripToken": symbol_token
            }
            logging.info(f"Requesting {mode} market data for {exchange}:{symbol_token}")
            response = self.smartapi.getMarketData(payload)

            if response and response.get('status'):
                logging.info(f"Successfully fetched {mode} data for {exchange}:{symbol_token}.")
                return response['data']
            else:
                message = response.get('message', 'Unknown market data error')
                error_code = response.get('errorcode', 'N/A')
                logging.error(f"Failed to fetch {mode} market data for {exchange}:{symbol_token}: {message} (Error Code: {error_code})")
                # Log full response if it contains useful error details
                if response:
                    logging.error(f"Full market data response for debug: {response}")
                return None
        except Exception as e:
            logging.error(f"Error fetching {mode} market data for {exchange}:{symbol_token}: {e}", exc_info=True)
            return None
