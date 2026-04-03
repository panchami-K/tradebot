"""
cli.py — Entry point for the Binance Futures Testnet trading bot.

Modes:
  Real mode (default):  connects to testnet.binancefuture.com using .env credentials
  Mock mode (--mock):   uses MockBinanceFuturesClient, no API keys or network needed

Usage:
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
  python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --mock
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000
  python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 80000
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.logging_config import setup_logger
from bot.orders import place_order

load_dotenv()
logger = setup_logger("trading_bot.cli")

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _c(colour: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"{colour}{text}{RESET}"
    return text


def print_request_summary(args: argparse.Namespace) -> None:
    print()
    print(_c(BOLD, "━━━━━━━━━━━━  ORDER REQUEST  ━━━━━━━━━━━━"))
    print(f"  Symbol     : {_c(CYAN, args.symbol.upper())}")
    print(f"  Side       : {_c(GREEN if args.side.upper() == 'BUY' else RED, args.side.upper())}")
    print(f"  Type       : {args.type.upper()}")
    print(f"  Quantity   : {args.quantity}")
    if args.price:
        print(f"  Price      : {args.price}")
    if args.stop_price:
        print(f"  Stop Price : {args.stop_price}")
    if args.mock:
        print(f"  Mode       : {_c(YELLOW, 'MOCK (simulated)')}")
    print(_c(BOLD, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()


def print_order_result(result: dict) -> None:
    if result["success"]:
        print(_c(GREEN, _c(BOLD, "✅  ORDER PLACED SUCCESSFULLY")))
        print()
        print(_c(BOLD, "━━━━━━━━━━━━  ORDER RESPONSE  ━━━━━━━━━━━━"))
        print(f"  Order ID     : {result.get('order_id')}")
        print(f"  Client ID    : {result.get('client_id')}")
        print(f"  Symbol       : {result.get('symbol')}")
        print(f"  Side         : {result.get('side')}")
        print(f"  Type         : {result.get('type')}")
        print(f"  Status       : {_c(YELLOW, str(result.get('status')))}")
        print(f"  Orig Qty     : {result.get('orig_qty')}")
        print(f"  Executed Qty : {result.get('executed_qty')}")
        print(f"  Avg Price    : {result.get('avg_price') or 'N/A'}")
        print(f"  Price        : {result.get('price') or 'N/A'}")
        print(f"  Time In Force: {result.get('time_in_force') or 'N/A'}")
        print(_c(BOLD, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    else:
        print(_c(RED, _c(BOLD, "❌  ORDER FAILED")))
        print()
        print(f"  Reason: {_c(RED, result.get('error', 'Unknown error'))}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples (real mode — requires .env with API keys):
  python cli.py --symbol BTCUSDT --side BUY  --type MARKET     --quantity 0.001
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT       --quantity 0.001 --price 100000
  python cli.py --symbol BTCUSDT --side BUY  --type STOP_MARKET --quantity 0.001 --stop-price 80000

Examples (mock mode — no API keys needed):
  python cli.py --symbol BTCUSDT --side BUY  --type MARKET     --quantity 0.001 --mock
  python cli.py --symbol BTCUSDT --side SELL --type LIMIT       --quantity 0.001 --price 100000 --mock
  python cli.py --symbol BTCUSDT --side BUY  --type STOP_MARKET --quantity 0.001 --stop-price 80000 --mock
        """,
    )
    parser.add_argument("--symbol",     required=True,
                        help="Trading pair e.g. BTCUSDT")
    parser.add_argument("--side",       required=True,
                        choices=["BUY","SELL","buy","sell"])
    parser.add_argument("--type",       required=True, dest="type",
                        choices=["MARKET","LIMIT","STOP_MARKET","TAKE_PROFIT_MARKET",
                                 "market","limit","stop_market","take_profit_market"])
    parser.add_argument("--quantity",   required=True, type=float)
    parser.add_argument("--price",      type=float, default=None,
                        help="Required for LIMIT orders")
    parser.add_argument("--stop-price", type=float, default=None, dest="stop_price",
                        help="Required for STOP_MARKET / TAKE_PROFIT_MARKET")
    parser.add_argument("--tif",        default="GTC", choices=["GTC","IOC","FOK"],
                        help="Time-in-force for LIMIT orders (default: GTC)")
    parser.add_argument("--mock",       action="store_true",
                        help="Run in mock mode — simulates orders without API keys")
    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # ── Choose client based on --mock flag ──────────────────────────────────
    if args.mock:
        from bot.mock_client import MockBinanceFuturesClient
        client = MockBinanceFuturesClient()
        logger.info("Starting in MOCK mode")
    else:
        from bot.client import BinanceFuturesClient

        api_key    = os.getenv("BINANCE_API_KEY", "").strip()
        api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

        if not api_key or not api_secret:
            print(_c(RED, "❌  Missing API credentials."))
            print("    Add BINANCE_API_KEY and BINANCE_API_SECRET to .env")
            print("    Or run with --mock flag to test without credentials.")
            sys.exit(1)

        try:
            client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
        except ValueError as exc:
            print(_c(RED, f"❌  Client init failed: {exc}"))
            sys.exit(1)

    # ── Print request summary ───────────────────────────────────────────────
    print_request_summary(args)
    logger.info(
        "CLI request | symbol=%s side=%s type=%s qty=%s price=%s stop=%s mock=%s",
        args.symbol, args.side, args.type, args.quantity,
        args.price, args.stop_price, args.mock,
    )

    # ── Place order ─────────────────────────────────────────────────────────
    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
        time_in_force=args.tif,
    )

    print_order_result(result)

    if not result["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()