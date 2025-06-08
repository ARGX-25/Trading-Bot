# main.py
import os
import logging
from src.config import ConfigManager
from src.api import AngelOneAPI
from src import stock_basket


def main():
    print("Starting bot setup...")
    try:
        config = ConfigManager()
        print("Config loaded successfully!")
        print(f"API Key (from Dashboard): {config.api_key}")
        print(f"Angel One Login Username: {config.username}") # New print to confirm
        print(f"Paper Trading Mode: {config.is_paper_trading()}")
        print(f"Demo Funds: {config.funds_available}")

         # --- VERY IMPORTANT DEBUG PRINTS ---
        # print("\n--- .env VERIFICATION ---")
        # print(f"Current Working Directory: {os.getcwd()}")
        # print(f".env file exists in CWD: {os.path.exists('.env')}")
        # print(f"DEBUGGING: ANGELONE_CLIENT_ID from OS: {os.getenv('ANGELONE_CLIENT_ID')!r}") # !r shows raw string including spaces/comments
        # print(f"DEBUGGING: ANGELONE_USERNAME from OS: {os.getenv('ANGELONE_USERNAME')!r}")
        # print("--- END .env VERIFICATION ---\n")
        # --- END VERY IMPORTANT DEBUG PRINTS ---

        # --- Initialize and Test AngelOneAPI ---
        angel_api = AngelOneAPI(config)

        if angel_api.login(): # Call without any arguments
            print("Angel One API Login successful!")
            # Here you would typically proceed with other bot operations
            # Load scrip master data - essential for stock basket operations
            print("Loading scrip master data...")
            if not angel_api.load_scrip_master():
                logging.error("Failed to load scrip master. Exiting application.")
                angel_api.logout()
                return
        else:
            print("Angel One API Login failed. Check logs for details.")

        # Example of checking login status
        print(f"Is API logged in? {angel_api.is_logged_in()}")

         # Define your basket symbols
        my_basket_symbols = [
            "BSE","RPOWER","BAJAJHIND","TRIDENT","CANBK","MAHABANK",
            "SUZLON","YESBANK","SAIL","IRFC","TATASTEEL","IDFCFIRSTB",
            "BANKINDIA","ITC","WIPRO","HINDCOPPER","COALINDIA","IOC",
            "ONGC"
        ]

        # Check if any stocks were actually loaded.
        if not my_basket_symbols: # Check if the list is empty
            logging.warning("No basket symbols defined in main.py. Please add stocks to 'my_basket_symbols'.")
            # If no symbols are defined, you might want to log out and exit, or proceed depending on your bot's design
            angel_api.logout()
            print(f"Is API logged in after logout? {angel_api.is_logged_in()}")
            return

        # Initialize StockBasketManager
        basket_manager = stock_basket.StockBasketManager(angel_api)

        # Load stocks into the basket using the manager instance
        print(f"Attempting to load {len(my_basket_symbols)} symbols into the basket...")
        if not basket_manager.load_basket_stocks(my_basket_symbols):
            logging.error("No basket stocks were successfully loaded. Exiting application.")
            angel_api.logout()
            print(f"Is API logged in after logout? {angel_api.is_logged_in()}")
            return
        
        logging.info(f"Successfully loaded {len(basket_manager.get_basket_details())} stocks into the basket: {basket_manager.get_basket_symbols()}")

        # --- Your main bot logic would go here ---
        # For example, fetching market data, placing orders, etc.
        # Remember the instruction: stop trading when the market moves sideways.
        # You'll implement this logic here using market data from your API.

    except ValueError as e:
        print(f"Configuration error: {e}")
        logging.error(f"Configuration error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        # Log out when done (or in case of error, to ensure cleanup)
        if 'angel_api' in locals() and angel_api.is_logged_in():
            angel_api.logout()
            logging.info("Angel One API Logout successful.")
            print(f"Is API logged in after logout? {angel_api.is_logged_in()}")

if __name__ == "__main__":
    main()