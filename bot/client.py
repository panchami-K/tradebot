"""
client.py — Binance Spot Testnet client wrapper.

NOTE: Uses Binance Spot Testnet (testnet.binance.vision) because the
Futures Testnet UI geo-redirects in certain regions (India), preventing
API key generation. The Spot Testnet uses identical HMAC-SHA256 auth,
same order parameters, and same response format as Futures Testnet —
making it a valid substitute for demonstrating bot functionality.

Spot Testnet base URL : https://testnet.binance.vision
Order endpoint        : /api/v3/order  (same params as /fapi/v1/order)
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import setup_logger

logger = setup_logger("trading_bot.client")

BASE_URL = "https://testnet.binance.vision"


class BinanceClientError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class NetworkError(Exception):
    pass


class BinanceFuturesClient:
    """
    Testnet trading client using Binance Spot Testnet API.
    Identical auth mechanism (HMAC-SHA256) and order structure
    as the Futures Testnet.
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key    = api_key
        self._api_secret = api_secret
        self.base_url    = BASE_URL
        self._session    = requests.Session()
        self._session.headers.update({
            "X-MBX-APIKEY": self._api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        logger.info("BinanceFuturesClient ready | url=%s", self.base_url)

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            params["signature"] = self._sign(params)

        url  = f"{self.base_url}{endpoint}"
        safe = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("REQUEST  %s %s | params=%s", method.upper(), url, safe)

        try:
            if method.upper() == "GET":
                resp = self._session.get(url, params=params, timeout=10)
            elif method.upper() == "POST":
                resp = self._session.post(url, data=params, timeout=10)
            elif method.upper() == "DELETE":
                resp = self._session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s", exc)
            raise NetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout: %s", exc)
            raise NetworkError(f"Timeout: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Request error: %s", exc)
            raise NetworkError(f"Request error: {exc}") from exc

        logger.debug("RESPONSE status=%d | body=%s",
                     resp.status_code, resp.text[:500])

        try:
            data = resp.json()
        except ValueError:
            raise BinanceClientError(-1, f"Non-JSON response: {resp.text}")

        if isinstance(data, dict) and data.get("code", 0) < 0:
            logger.error("API error: %s", data)
            raise BinanceClientError(data["code"], data.get("msg", "Unknown error"))

        return data

    def ping(self) -> bool:
        try:
            self._request("GET", "/api/v3/ping")
            return True
        except Exception:
            return False

    def place_order(self, **order_params: Any) -> Dict[str, Any]:
        """
        Place a spot testnet order.
        Accepts same params as Futures: symbol, side, type, quantity, price, timeInForce.
        Strips Futures-only params (stopPrice, positionSide) that Spot API rejects.
        """
        # Spot API does not accept these Futures-only params
        futures_only = {"stopPrice", "positionSide", "reduceOnly",
                        "workingType", "priceProtect"}
        clean_params = {k: v for k, v in order_params.items()
                        if k not in futures_only and v is not None}

        logger.debug("place_order params: %s", clean_params)
        return self._request("POST", "/api/v3/order",
                             params=clean_params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return self._request("DELETE", "/api/v3/order",
                             params={"symbol": symbol, "orderId": order_id},
                             signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        params = {"symbol": symbol.upper()} if symbol else {}
        return self._request("GET", "/api/v3/openOrders",
                             params=params, signed=True)