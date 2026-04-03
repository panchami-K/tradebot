from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient, BinanceClientError, NetworkError
from bot.logging_config import setup_logger
from bot.validators import validate_all, ValidationError

logger = setup_logger("trading_bot.orders")


# ---------------------------------------------------------------------------
# Result dataclass (plain dict for simplicity — no external deps needed)
# ---------------------------------------------------------------------------

def _build_result(success: bool, raw: Optional[Dict] = None, error: str = "") -> Dict:
    """Normalise every outcome into a consistent result dict."""
    if success and raw:
        return {
            "success":      True,
            "order_id":     raw.get("orderId"),
            "client_id":    raw.get("clientOrderId"),
            "symbol":       raw.get("symbol"),
            "side":         raw.get("side"),
            "type":         raw.get("type"),
            "status":       raw.get("status"),
            "price":        raw.get("price"),          # original order price
            "avg_price":    raw.get("avgPrice"),        # fill price (MARKET)
            "orig_qty":     raw.get("origQty"),
            "executed_qty": raw.get("executedQty"),
            "time_in_force": raw.get("timeInForce"),
            "raw":          raw,
        }
    return {"success": False, "error": error, "raw": raw}


# ---------------------------------------------------------------------------
# Core order function
# ---------------------------------------------------------------------------

def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
    stop_price: Any = None,
    time_in_force: str = "GTC",
) -> Dict:
    """
    Validate inputs, build the Binance API payload, place the order,
    and return a normalised result dict.

    Args:
        client:        Authenticated BinanceFuturesClient instance.
        symbol:        Trading pair, e.g. 'BTCUSDT'.
        side:          'BUY' or 'SELL'.
        order_type:    'MARKET', 'LIMIT', 'STOP_MARKET', 'TAKE_PROFIT_MARKET'.
        quantity:      Order size (will be cast to float).
        price:         Required for LIMIT orders.
        stop_price:    Required for STOP_MARKET / TAKE_PROFIT_MARKET orders.
        time_in_force: Default 'GTC'; only sent for LIMIT orders.

    Returns:
        A dict with 'success', 'order_id', 'status', etc.
        On failure: {'success': False, 'error': '<message>'}.
    """

    # 1. Validate -------------------------------------------------------
    try:
        validated = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValidationError as exc:
        logger.warning("Validation failed: %s", exc)
        return _build_result(success=False, error=str(exc))

    v_symbol     = validated["symbol"]
    v_side       = validated["side"]
    v_type       = validated["order_type"]
    v_qty        = validated["quantity"]
    v_price      = validated["price"]
    v_stop_price = validated["stop_price"]

    # 2. Build payload --------------------------------------------------
    payload: Dict[str, Any] = {
        "symbol":   v_symbol,
        "side":     v_side,
        "type":     v_type,
        "quantity": v_qty,
    }

    if v_type == "LIMIT":
        payload["price"]       = f"{v_price:.8f}"
        payload["timeInForce"] = time_in_force

    if v_stop_price is not None:
        payload["stopPrice"] = f"{v_stop_price:.8f}"

    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s stop=%s",
        v_side, v_type, v_symbol, v_qty,
        v_price or "N/A", v_stop_price or "N/A",
    )

    # 3. Call API -------------------------------------------------------
    try:
        raw_response = client.place_order(**payload)
        logger.info(
            "Order placed successfully | orderId=%s status=%s executedQty=%s avgPrice=%s",
            raw_response.get("orderId"),
            raw_response.get("status"),
            raw_response.get("executedQty"),
            raw_response.get("avgPrice"),
        )
        return _build_result(success=True, raw=raw_response)

    except ValidationError as exc:
        logger.warning("Late validation error: %s", exc)
        return _build_result(success=False, error=str(exc))

    except BinanceClientError as exc:
        logger.error("Binance API error while placing order: [%d] %s", exc.code, exc.message)
        return _build_result(success=False, error=str(exc))

    except NetworkError as exc:
        logger.error("Network error while placing order: %s", exc)
        return _build_result(success=False, error=str(exc))

    except Exception as exc:
        logger.exception("Unexpected error while placing order: %s", exc)
        return _build_result(success=False, error=f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# Convenience wrappers (readable call sites in cli.py)
# ---------------------------------------------------------------------------

def place_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Any,
) -> Dict:
    """Shorthand for placing a MARKET order."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="MARKET",
        quantity=quantity,
    )


def place_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Any,
    price: Any,
    time_in_force: str = "GTC",
) -> Dict:
    """Shorthand for placing a LIMIT order."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=quantity,
        price=price,
        time_in_force=time_in_force,
    )


def place_stop_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: Any,
    stop_price: Any,
) -> Dict:
    """Shorthand for placing a STOP_MARKET order (bonus order type)."""
    return place_order(
        client=client,
        symbol=symbol,
        side=side,
        order_type="STOP_MARKET",
        quantity=quantity,
        stop_price=stop_price,
    )