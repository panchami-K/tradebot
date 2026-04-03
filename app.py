"""
app.py — Flask web frontend for the Binance Futures Testnet Trading Bot.

Run:
    uv run python app.py
Then open: http://localhost:5000
"""

import os
import sys
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from bot.orders import place_order
from bot.mock_client import MockBinanceFuturesClient
from bot.logging_config import setup_logger

logger = setup_logger("trading_bot.app")
app = Flask(__name__)


def get_client(mock: bool = False):
    if mock:
        return MockBinanceFuturesClient()
    from bot.client import BinanceFuturesClient
    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        raise ValueError("Missing API credentials in .env")
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/place-order", methods=["POST"])
def api_place_order():
    data = request.get_json()
    logger.info("Web order request: %s", data)

    mock       = data.get("mock", False)
    symbol     = data.get("symbol", "")
    side       = data.get("side", "")
    order_type = data.get("type", "")
    quantity   = data.get("quantity")
    price      = data.get("price")
    stop_price = data.get("stopPrice")
    tif        = data.get("timeInForce", "GTC")

    try:
        client = get_client(mock=mock)
        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price if price else None,
            stop_price=stop_price if stop_price else None,
            time_in_force=tif,
        )
        return jsonify(result)
    except Exception as exc:
        logger.error("Web order error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/ping")
def api_ping():
    try:
        mock = request.args.get("mock", "false").lower() == "true"
        client = get_client(mock=mock)
        ok = client.ping()
        return jsonify({"connected": ok})
    except Exception as exc:
        return jsonify({"connected": False, "error": str(exc)})


if __name__ == "__main__":
    print("\n🚀 Trading Bot Web UI running at http://localhost:5000\n")
    app.run(debug=True, port=5000)