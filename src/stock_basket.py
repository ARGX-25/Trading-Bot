import logging
import time # Imported for potential future use or small delays if needed
from src.api import AngelOneAPI



# --- Setup Logging for this module ---
# This basicConfig will set up logging for this file if not already
# configured by a central logger.py or main.py.
# Using 'api_debug.log' here for consistency with other API-related logs.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("api_debug.log"), # Or a more specific log file if desired
                        logging.StreamHandler()
                    ])

class StockBasketManager:
    """
    Manages the pre-defined basket of stocks for the trading bot.
    It relies on the AngelOneAPI instance to lookup stock tokens from the scrip master.
    """
    def __init__(self, angel_api: AngelOneAPI):
        """
        Initializes the StockBasketManager.
        Args:
            angel_api (AngelOneAPI): An instance of the AngelOneAPI class.
                                     It is expected that angel_api.load_scrip_master()
                                     has been called successfully before using this manager.
        """
        self.angel_api = angel_api
        # Stores stock details: [{'symbol': 'INFY', 'token': '...', 'exchange': '...'}]
        self.basket_stocks = []
        logging.info("StockBasketManager initialized.")

    def load_basket_stocks(self, symbols: list, default_exchange_segment: str = 'NSE') -> bool:
        """
        Loads the basket of stocks by looking up their tokens and exchange segments
        using the AngelOneAPI's scrip master.
        Args:
            symbols (list): A list of human-readable stock symbols (e.g., ['RELIANCE', 'TCS']).
            default_exchange_segment (str): The default exchange segment to search within
                                            if not specified per symbol. Defaults to 'NSE'.
        Returns:
            bool: True if at least one stock was loaded successfully, False otherwise.
        """
        if not self.angel_api.scrip_data:
            logging.error("Scrip master data is not loaded in AngelOneAPI. Cannot load basket stocks.")
            logging.error("Please ensure angel_api.load_scrip_master() is called and successful before calling StockBasketManager.load_basket_stocks().")
            return False

        self.basket_stocks = [] # Clear any previously loaded stocks
        loaded_count = 0
        total_requested = len(symbols)

        logging.info(f"Attempting to load {total_requested} stocks into the basket from scrip master...")

        for symbol_name in symbols:
            # Use the AngelOneAPI's helper function to get scrip info
            # This is expected to return {'token': '...', 'exchange': '...'} or None
            scrip_info = self.angel_api.get_token_by_symbol(symbol_name, exchange_segment=default_exchange_segment)

            if scrip_info:
                # Validate the structure of scrip_info returned by api.py
                if 'token' in scrip_info and 'exchange' in scrip_info:
                    self.basket_stocks.append({
                        'symbol': symbol_name, # Original human-readable symbol (e.g., 'RELIANCE')
                        'token': scrip_info['token'],
                        'exchange': scrip_info['exchange']
                    })
                    loaded_count += 1
                    logging.info(f"Successfully added '{symbol_name}' (Token: {scrip_info['token']}) to basket.")
                else:
                    logging.warning(f"Invalid scrip_info format received for '{symbol_name}'. Expected 'token' and 'exchange' keys. Skipping.")
            else:
                logging.warning(f"Could not find valid scrip info for '{symbol_name}' in '{default_exchange_segment}' segment. Skipping this stock.")

        logging.info(f"Finished loading basket stocks. Loaded {loaded_count} out of {total_requested} requested stocks.")
        return loaded_count > 0 # Return True if at least one stock was loaded

    def get_basket_symbols(self) -> list[str]:
        """
        Returns a list of human-readable symbols currently in the basket.
        Returns:
            list[str]: A list of stock symbols.
        """
        return [stock['symbol'] for stock in self.basket_stocks]

    def get_basket_details(self) -> list[dict]:
        """
        Returns the full list of basket stock details (symbol, token, exchange).
        Returns:
            list[dict]: A list of dictionaries, each containing stock details.
        """
        return self.basket_stocks

    def get_market_data_for_basket(self, mode: str = "FULL") -> dict:
        """
        Fetches market data for all stocks currently in the basket.
        This method directly utilizes the AngelOneAPI instance.
        Args:
            mode (str): The data mode ("LTP", "OHLC", or "FULL"). Defaults to "FULL".
        Returns:
            dict: A dictionary where keys are stock symbols (human-readable) and
                  values are their market data, or None if data fetching failed for a specific stock.
                  Returns an empty dictionary if no stocks in basket or no data fetched.
        """
        all_market_data = {}
        if not self.basket_stocks:
            logging.warning("No stocks in the basket to fetch market data for.")
            return all_market_data

        logging.info(f"Attempting to fetch {mode} market data for all {len(self.basket_stocks)} stocks in the basket.")
        for stock_info in self.basket_stocks:
            symbol = stock_info['symbol']
            token = stock_info['token']
            exchange = stock_info['exchange']

            market_data = self.angel_api.get_market_data(exchange, token, mode=mode)
            if market_data:
                all_market_data[symbol] = market_data
                logging.info(f"Fetched {mode} data for {symbol}: LTP={market_data.get('ltp', 'N/A')}")
            else:
                logging.warning(f"Failed to get {mode} market data for {symbol}.")
            
            # Add a small delay to avoid hitting API rate limits. Adjust as necessary.
            time.sleep(0.2) # Reduced slightly, but monitor API limits

        logging.info("Completed market data fetching for basket stocks.")
        return all_market_data

