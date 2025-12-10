import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Kalshi Configuration
    KALSHI_API_KEY_ID = os.getenv("KALSHI_API_KEY_ID")
    KALSHI_PRIVATE_KEY_PATH = os.getenv("KALSHI_PRIVATE_KEY_PATH")
    KALSHI_USE_DEMO = os.getenv("KALSHI_USE_DEMO", "true").lower() == "true"

    @property
    def KALSHI_HOST(self):
        if self.KALSHI_USE_DEMO:
            return "https://demo-api.kalshi.co/trade-api/v2"
        return "https://api.elections.kalshi.com/trade-api/v2"

    # Polymarket Configuration
    POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
    POLYMARKET_FUNDER_ADDRESS = os.getenv("POLYMARKET_FUNDER_ADDRESS")
    POLYMARKET_SIGNATURE_TYPE = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "1"))
    POLYMARKET_HOST = "https://clob.polymarket.com"
    POLYMARKET_CHAIN_ID = 137  # Polygon mainnet

    # Trading Configuration
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "100"))
    MIN_PROFIT_MARGIN = float(os.getenv("MIN_PROFIT_MARGIN", "0.02"))
    PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"

    def validate_kalshi(self):
        """Check if Kalshi credentials are configured"""
        return bool(self.KALSHI_API_KEY_ID and self.KALSHI_PRIVATE_KEY_PATH)

    def validate_polymarket(self):
        """Check if Polymarket credentials are configured"""
        return bool(self.POLYMARKET_PRIVATE_KEY)

settings = Settings()
