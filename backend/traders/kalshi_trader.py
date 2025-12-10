"""
Kalshi Trading Client

Handles authentication and order placement on Kalshi.
Supports both demo and production environments.
"""
import sys
sys.path.append('..')

from config.settings import settings

class KalshiTrader:
    def __init__(self):
        self.client = None
        self._initialized = False

        if settings.validate_kalshi():
            self._initialize_client()

    def _initialize_client(self):
        """Initialize the Kalshi client with API credentials"""
        try:
            from kalshi_python import KalshiClient, Configuration

            # Read private key from file
            with open(settings.KALSHI_PRIVATE_KEY_PATH, "r") as f:
                private_key = f.read()

            # Configure the client
            config = Configuration(host=settings.KALSHI_HOST)
            config.api_key_id = settings.KALSHI_API_KEY_ID
            config.private_key_pem = private_key

            # Initialize Kalshi client
            self.client = KalshiClient(config)

            self._initialized = True
            env = "DEMO" if settings.KALSHI_USE_DEMO else "PRODUCTION"
            print(f"[Kalshi] Initialized in {env} mode")

        except ImportError as e:
            print(f"[Kalshi] SDK not installed or import error: {e}")
        except FileNotFoundError:
            print(f"[Kalshi] Private key file not found: {settings.KALSHI_PRIVATE_KEY_PATH}")
        except Exception as e:
            print(f"[Kalshi] Initialization error: {e}")

    def is_ready(self):
        """Check if trader is initialized and ready"""
        return self._initialized

    def get_balance(self):
        """Get current account balance"""
        if not self._initialized:
            return None
        try:
            response = self.client.get_balance()
            return response.balance / 100  # Convert cents to dollars
        except Exception as e:
            print(f"[Kalshi] Balance error: {e}")
            return None

    def place_order(self, ticker: str, side: str, quantity: int, price_cents: int):
        """
        Place a limit order on Kalshi

        Args:
            ticker: Market ticker (e.g., "KXBTCD-25DEC1016-B93250")
            side: "yes" or "no"
            quantity: Number of contracts
            price_cents: Price in cents (1-99)

        Returns:
            Order response or None on failure
        """
        if not self._initialized:
            print("[Kalshi] Not initialized - cannot place order")
            return None

        if settings.PAPER_TRADING:
            print(f"[Kalshi] PAPER TRADE: {side.upper()} {quantity}x {ticker} @ {price_cents}¢")
            return {"paper_trade": True, "ticker": ticker, "side": side, "quantity": quantity, "price": price_cents}

        try:
            from kalshi_python.models import CreateOrderRequest

            order_request = CreateOrderRequest(
                ticker=ticker,
                side=side,
                count=quantity,
                type="limit",
                yes_price=price_cents if side == "yes" else None,
                no_price=price_cents if side == "no" else None,
            )

            response = self.client.create_order(order_request)
            print(f"[Kalshi] Order placed: {side.upper()} {quantity}x {ticker} @ {price_cents}¢")
            return response

        except Exception as e:
            print(f"[Kalshi] Order error: {e}")
            return None

    def cancel_order(self, order_id: str):
        """Cancel an existing order"""
        if not self._initialized:
            return None
        try:
            response = self.client.cancel_order(order_id)
            return response
        except Exception as e:
            print(f"[Kalshi] Cancel error: {e}")
            return None

    def get_positions(self):
        """Get current positions"""
        if not self._initialized:
            return None
        try:
            response = self.client.get_positions()
            return response.market_positions
        except Exception as e:
            print(f"[Kalshi] Positions error: {e}")
            return None
