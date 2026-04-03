# Binance Futures Testnet Trading Bot

A command-line Python trading bot for placing orders on Binance Futures Testnet (USDT-M).
Built with clean layered architecture: CLI → orders → client, with full logging and error handling.

> ⚠️ **Uses Binance Futures Testnet only** — no real money, no KYC required.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (auth, signing, HTTP)
│   ├── orders.py          # Order placement logic + convenience wrappers
│   ├── validators.py      # Input validation (symbol, side, qty, price)
│   └── logging_config.py  # Shared logger (file + console)
├── cli.py                 # CLI entry point (argparse)
├── .env.example           # Credential template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet API Keys

1. Open **[https://demo.binance.com](https://demo.binance.com)** in an incognito window
2. Click **Login → GitHub** (do NOT use email or Binance account)
3. After login: Profile → **API Management** → Create API Key
4. Copy your **API Key** and **Secret**

> **Note:** The old `testnet.binancefuture.com` now redirects elsewhere.
> The current testnet base URL is `https://demo-fapi.binance.com` (used automatically by this bot).

### 2. Install Dependencies

```bash
# Python 3.8+ required
pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
cp .env.example .env
# Edit .env and paste your API Key + Secret
```

Your `.env` file should look like:
```
BINANCE_API_KEY=abc123...
BINANCE_API_SECRET=xyz789...
```

---

## How to Run

### Place a MARKET BUY order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place a LIMIT SELL order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 100000
```

### Place a STOP_MARKET order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 80000
```

### All CLI options

```
--symbol       Trading pair (e.g. BTCUSDT)           [required]
--side         BUY or SELL                            [required]
--type         MARKET / LIMIT / STOP_MARKET           [required]
--quantity     Order size                             [required]
--price        Limit price (required for LIMIT)       [optional]
--stop-price   Trigger price (required for STOP_*)    [optional]
--tif          Time-in-force: GTC / IOC / FOK         [default: GTC]
```

---

## Sample Output

```
━━━━━━━━━━━━  ORDER REQUEST  ━━━━━━━━━━━━
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅  ORDER PLACED SUCCESSFULLY

━━━━━━━━━━━━  ORDER RESPONSE  ━━━━━━━━━━━━
  Order ID     : 3951823749
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Orig Qty     : 0.001
  Executed Qty : 0.001
  Avg Price    : 83412.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Logging

All API requests, responses, and errors are logged to **`trading_bot.log`** in the project root.

- Console shows INFO level and above (clean summary)
- Log file shows DEBUG level (full request/response bodies)

---

## Assumptions

- USDT-M Futures only (not COIN-M)
- Testnet environment only — base URL is `https://demo-fapi.binance.com`
- Default leverage is whatever the testnet account is set to
- Credentials are stored in a local `.env` file (never commit this file)
- Python 3.8+ required

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing price for LIMIT | Validation error before any API call |
| Price given for MARKET | Validation error — not allowed |
| Invalid symbol / side | Clear error message, exit code 1 |
| API authentication error | Logged + printed with Binance error code |
| Network timeout | Logged + printed, exit code 1 |