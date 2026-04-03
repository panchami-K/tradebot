from typing import Optional

# Supported values — extend as needed
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"}
VALID_TIME_IN_FORCE = {"GTC", "IOC", "FOK", "GTX"}


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""
    pass


def validate_symbol(symbol: str) -> str:
    """
    Symbols must be non-empty uppercase strings like 'BTCUSDT'.
    We do not query the exchange at validation time — that's done in orders.py.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol must be a non-empty string (e.g. BTCUSDT).")
    cleaned = symbol.strip().upper()
    if len(cleaned) < 3:
        raise ValidationError(f"Symbol '{symbol}' is too short to be valid.")
    return cleaned


def validate_side(side: str) -> str:
    """Side must be BUY or SELL (case-insensitive)."""
    if not side:
        raise ValidationError("Side is required.")
    upper = side.strip().upper()
    if upper not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return upper


def validate_order_type(order_type: str) -> str:
    """Order type must be one of the supported types (case-insensitive)."""
    if not order_type:
        raise ValidationError("Order type is required.")
    upper = order_type.strip().upper()
    if upper not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return upper


def validate_quantity(quantity: any) -> float:
    """Quantity must be a positive number."""
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0. Got: {qty}.")
    return qty


def validate_price(price: any, order_type: str) -> Optional[float]:
    """
    Price is required for LIMIT orders, must be positive.
    For MARKET orders, price should be None / omitted.
    """
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            p = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValidationError(f"Price must be greater than 0. Got: {p}.")
        return p

    # MARKET order — price must not be provided
    if price is not None:
        raise ValidationError(
            f"Price should not be provided for {order_type} orders. "
            "Remove the --price argument."
        )
    return None


def validate_stop_price(stop_price: any, order_type: str) -> Optional[float]:
    """Stop price is required for STOP_MARKET and TAKE_PROFIT_MARKET orders."""
    stop_required_types = {"STOP_MARKET", "TAKE_PROFIT_MARKET"}
    if order_type in stop_required_types:
        if stop_price is None:
            raise ValidationError(
                f"--stop-price is required for {order_type} orders."
            )
        try:
            sp = float(stop_price)
        except (TypeError, ValueError):
            raise ValidationError(f"Stop price '{stop_price}' is not a valid number.")
        if sp <= 0:
            raise ValidationError(f"Stop price must be greater than 0. Got: {sp}.")
        return sp
    return None


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: any,
    price: any = None,
    stop_price: any = None,
) -> dict:
    """
    Run all validations in one call.
    Returns a dict of cleaned, validated values ready for the order layer.
    Raises ValidationError with a descriptive message on any failure.
    """
    cleaned_type = validate_order_type(order_type)  # validate type first (others depend on it)
    return {
        "symbol":     validate_symbol(symbol),
        "side":       validate_side(side),
        "order_type": cleaned_type,
        "quantity":   validate_quantity(quantity),
        "price":      validate_price(price, cleaned_type),
        "stop_price": validate_stop_price(stop_price, cleaned_type),
    }