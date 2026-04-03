"""
mock_client.py — Simulated Binance Futures client for testing without API keys.

Mimics real Binance Futures API responses exactly, including:
  - Realistic order IDs, timestamps, prices
  - Correct field names (orderId, executedQty, avgPrice, etc.)
  - Proper status transitions (MARKET → FILLED, LIMIT → NEW)
  - Error simulation for invalid inputs

Usage in cli.py:
    Pass --mock flag to use this instead of real BinanceFuturesClient
"""

import random
import time
from typing import Any, Dict, Optional

from bot.logging_config import setup_logger

logger = setup_logger("trading_bot.mock_client")

# Simulated market prices (close to real testnet prices)
MOCK_PRICES = {
    "BTCUSDT":  83500.00,
    "ETHUSDT":  1800.00,
    "BNBUSDT":  580.00,
    "SOLUSDT":  120.00,
    "XRPUSDT":  2.10,
}

VALID_SYMBOLS = set(MOCK_PRICES.keys())


class BinanceClientError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class NetworkError(Exception):
    pass


class MockBinanceFuturesClient:
    """
    Drop-in replacement for BinanceFuturesClient that returns
    realistic simulated responses — no API keys or network needed.

    Designed to match the exact response format of the real
    Binance Futures REST API (/fapi/v1/order).
    """

    def __init__(self, api_key: str = "mock_key", api_secret: str = "mock_secret",
                 testnet: bool = True):
        self._order_counter = random.randint(100000000, 999999999)
        logger.info("MockBinanceFuturesClient ready | mode=MOCK (no real orders placed)")
        print("  ⚠️  Running in MOCK mode — no real orders placed")
        print("  📋  Responses simulate real Binance Futures API format\n")

    def _next_order_id(self) -> int:
        self._order_counter += random.randint(1, 100)
        return self._order_counter

    def _get_price(self, symbol: str) -> float:
        base = MOCK_PRICES.get(symbol.upper(), 100.0)
        # Add small random spread to simulate live price
        return round(base * random.uniform(0.999, 1.001), 2)

    def ping(self) -> bool:
        logger.debug("Mock ping → True")
        return True

    def get_exchange_info(self) -> Dict[str, Any]:
        return {
            "timezone": "UTC",
            "serverTime": int(time.time() * 1000),
            "symbols": [{"symbol": s, "status": "TRADING"} for s in VALID_SYMBOLS],
        }

    def get_account_info(self) -> Dict[str, Any]:
        return {
            "totalWalletBalance": "10000.00",
            "totalUnrealizedProfit": "0.00",
            "totalMarginBalance": "10000.00",
            "availableBalance": "10000.00",
        }

    def place_order(self, **order_params: Any) -> Dict[str, Any]:
        """
        Simulate placing an order. Returns a response that exactly
        matches the real Binance Futures /fapi/v1/order POST response.
        """
        symbol     = order_params.get("symbol", "").upper()
        side       = order_params.get("side", "BUY").upper()
        order_type = order_params.get("type", "MARKET").upper()
        quantity   = float(order_params.get("quantity", 0))
        price      = order_params.get("price")
        stop_price = order_params.get("stopPrice")

        logger.debug("Mock place_order | params=%s", order_params)

        # --- Simulate API-level validation errors ---
        if symbol not in VALID_SYMBOLS:
            raise BinanceClientError(-1121, f"Invalid symbol: {symbol}")

        if quantity <= 0:
            raise BinanceClientError(-1111, "Quantity less than or equal to zero")

        if order_type == "LIMIT" and not price:
            raise BinanceClientError(-1102, "Price required for LIMIT order")

        # Simulate tiny network delay
        time.sleep(0.3)

        order_id   = self._next_order_id()
        client_oid = f"x-testbot-{order_id}"
        ts         = int(time.time() * 1000)
        fill_price = self._get_price(symbol)

        # MARKET → immediately FILLED
        # LIMIT  → NEW (resting on book)
        # STOP_MARKET → NEW (waiting for trigger)
        if order_type == "MARKET":
            status       = "FILLED"
            executed_qty = str(quantity)
            avg_price    = str(fill_price)
            cum_quote    = str(round(quantity * fill_price, 4))
        elif order_type == "LIMIT":
            status       = "NEW"
            executed_qty = "0"
            avg_price    = "0"
            cum_quote    = "0"
        else:
            # STOP_MARKET, TAKE_PROFIT_MARKET
            status       = "NEW"
            executed_qty = "0"
            avg_price    = "0"
            cum_quote    = "0"

        response = {
            "orderId":           order_id,
            "symbol":            symbol,
            "status":            status,
            "clientOrderId":     client_oid,
            "price":             str(price) if price else "0",
            "avgPrice":          avg_price,
            "origQty":           str(quantity),
            "executedQty":       executed_qty,
            "cumQuote":          cum_quote,
            "timeInForce":       order_params.get("timeInForce", "GTC"),
            "type":              order_type,
            "side":              side,
            "stopPrice":         str(stop_price) if stop_price else "0",
            "workingType":       "CONTRACT_PRICE",
            "origType":          order_type,
            "positionSide":      "BOTH",
            "activatePrice":     None,
            "priceRate":         None,
            "updateTime":        ts,
            "time":              ts,
            "reduceOnly":        False,
            "closePosition":     False,
            "priceProtect":      False,
        }

        logger.info(
            "Mock order placed | orderId=%s symbol=%s side=%s type=%s "
            "qty=%s status=%s avgPrice=%s",
            order_id, symbol, side, order_type, quantity, status, avg_price,
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return {
            "orderId":       order_id,
            "symbol":        symbol.upper(),
            "status":        "CANCELED",
            "clientOrderId": f"x-testbot-{order_id}",
            "origQty":       "0.001",
            "executedQty":   "0",
            "type":          "LIMIT",
            "side":          "BUY",
        }

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        return []