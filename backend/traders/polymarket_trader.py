"""
Polymarket Trading Client

Handles wallet-based authentication and order placement on Polymarket CLOB.
Supports EOA wallets, email/Magic wallets, and browser wallets.
"""
import sys
sys.path.append('..')

from config.settings import settings

class PolymarketTrader:
    def __init__(self):
        self.client = None
        self._initialized = False

        if settings.validate_polymarket():
            self._initialize_client()

    def _initialize_client(self):
        """Initialize the Polymarket CLOB client"""
        try:
            from py_clob_client.client import ClobClient

            # Initialize client with wallet credentials
            self.client = ClobClient(
                host=settings.POLYMARKET_HOST,
                key=settings.POLYMARKET_PRIVATE_KEY,
                chain_id=settings.POLYMARKET_CHAIN_ID,
                signature_type=settings.POLYMARKET_SIGNATURE_TYPE,
                funder=settings.POLYMARKET_FUNDER_ADDRESS
            )

            # Generate or derive API credentials for L2 authentication
            api_creds = self.client.create_or_derive_api_creds()
            self.client.set_api_creds(api_creds)

            self._initialized = True
            sig_type_names = {0: "EOA", 1: "Email/Magic", 2: "Browser"}
            print(f"[Polymarket] Initialized with {sig_type_names.get(settings.POLYMARKET_SIGNATURE_TYPE, 'Unknown')} wallet")

        except ImportError:
            print("[Polymarket] SDK not installed. Run: pip install py-clob-client")
        except Exception as e:
            print(f"[Polymarket] Initialization error: {e}")

    def is_ready(self):
        """Check if trader is initialized and ready"""
        return self._initialized

    def get_balance(self):
        """Get USDC balance for trading"""
        if not self._initialized:
            return None
        try:
            # Balance check depends on wallet type
            # For now, return None - would need web3 integration for full balance check
            return None
        except Exception as e:
            print(f"[Polymarket] Balance error: {e}")
            return None

    def place_limit_order(self, token_id: str, side: str, size: float, price: float):
        """
        Place a limit order on Polymarket

        Args:
            token_id: The CLOB token ID for the outcome
            side: "BUY" or "SELL"
            size: Number of shares (float)
            price: Price per share (0.01 to 0.99)

        Returns:
            Order response or None on failure
        """
        if not self._initialized:
            print("[Polymarket] Not initialized - cannot place order")
            return None

        if settings.PAPER_TRADING:
            print(f"[Polymarket] PAPER TRADE: {side} {size} shares @ ${price:.3f}")
            return {"paper_trade": True, "token_id": token_id, "side": side, "size": size, "price": price}

        try:
            from py_clob_client.clob_types import OrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL

            order_side = BUY if side.upper() == "BUY" else SELL

            order = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=order_side
            )

            signed_order = self.client.create_order(order)
            response = self.client.post_order(signed_order, OrderType.GTC)

            print(f"[Polymarket] Order placed: {side} {size} shares @ ${price:.3f}")
            return response

        except Exception as e:
            print(f"[Polymarket] Order error: {e}")
            return None

    def place_market_order(self, token_id: str, side: str, amount: float):
        """
        Place a market order (fill or kill) on Polymarket

        Args:
            token_id: The CLOB token ID for the outcome
            side: "BUY" or "SELL"
            amount: Dollar amount to spend

        Returns:
            Order response or None on failure
        """
        if not self._initialized:
            print("[Polymarket] Not initialized - cannot place order")
            return None

        if settings.PAPER_TRADING:
            print(f"[Polymarket] PAPER MARKET ORDER: {side} ${amount}")
            return {"paper_trade": True, "token_id": token_id, "side": side, "amount": amount}

        try:
            from py_clob_client.clob_types import MarketOrderArgs, OrderType
            from py_clob_client.order_builder.constants import BUY, SELL

            order_side = BUY if side.upper() == "BUY" else SELL

            market_order = MarketOrderArgs(
                token_id=token_id,
                amount=amount,
                side=order_side
            )

            signed_order = self.client.create_market_order(market_order)
            response = self.client.post_order(signed_order, OrderType.FOK)

            print(f"[Polymarket] Market order filled: {side} ${amount}")
            return response

        except Exception as e:
            print(f"[Polymarket] Market order error: {e}")
            return None

    def cancel_order(self, order_id: str):
        """Cancel an existing order"""
        if not self._initialized:
            return None
        try:
            response = self.client.cancel(order_id)
            return response
        except Exception as e:
            print(f"[Polymarket] Cancel error: {e}")
            return None

    def cancel_all_orders(self):
        """Cancel all open orders"""
        if not self._initialized:
            return None
        try:
            response = self.client.cancel_all()
            return response
        except Exception as e:
            print(f"[Polymarket] Cancel all error: {e}")
            return None

    def get_open_orders(self):
        """Get all open orders"""
        if not self._initialized:
            return None
        try:
            response = self.client.get_orders()
            return response
        except Exception as e:
            print(f"[Polymarket] Get orders error: {e}")
            return None
