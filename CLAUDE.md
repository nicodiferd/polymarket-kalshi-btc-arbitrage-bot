# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-time arbitrage detection bot for Bitcoin 1-Hour Price markets between Polymarket and Kalshi prediction markets. Identifies "risk-free" arbitrage when combined cost of opposing positions totals less than $1.00 (guaranteed payout).

## Commands

### Backend (Python/FastAPI)
```bash
cd backend
pip install -r requirements.txt   # Install dependencies
python3 api.py                    # Start API server (localhost:8000)
python3 arbitrage_bot.py          # Run CLI monitoring loop
```

### Frontend (Next.js 14)
```bash
cd frontend
npm install                       # Install dependencies
npm run dev                       # Start dev server (localhost:3000)
npm run build                     # Build production bundle
npm run lint                      # Run ESLint
```

### Docker (Full Stack with VPN)
```bash
docker-compose up -d              # Start all services (vpn, backend, frontend)
docker-compose logs -f backend    # Follow backend logs
docker-compose down               # Stop all services
```

## Architecture

```
Frontend (Next.js)         Backend (FastAPI)           External APIs
     |                          |                           |
     |-- GET /arbitrage ------->|                           |
     |                          |-- Polymarket CLOB API --->| (via VPN SOCKS5 proxy)
     |                          |-- Kalshi Trade API ------>| (DIRECT - faster!)
     |                          |-- Binance Price API ----->| (DIRECT - faster!)
     |<-- JSON Response --------|                           |
     |                          |                           |
(polls every 1s)           (async parallel fetching)
```

**Split VPN Routing**: Only Polymarket requests go through VPN (geo-restricted in US). Kalshi and Binance use direct connections for lower latency.

- **VPN container (gluetun)**: Exposes SOCKS5 proxy on port 1080
- **Backend**: Uses `VPN_PROXY_URL=socks5://vpn:1080` for Polymarket only
- **async_fetcher.py**: Parallel API calls with split routing (~200-300ms vs 1.5-2s)

### Backend Modules (`/backend`)
- **api.py**: FastAPI server with `/arbitrage`, `/trading/status`, `/trading/auto-trade`, `/trading/execute` endpoints. Includes hour-boundary protection to prevent trading during market transitions (±2 min around hour marks)
- **async_fetcher.py**: High-performance async data fetcher with split VPN routing and caching
- **fees.py**: Fee calculation module for both platforms
- **arbitrage_bot.py**: Standalone CLI monitoring script
- **fetch_current_polymarket.py**: Polymarket CLOB API + Binance.US price fetching (sync fallback)
- **fetch_current_kalshi.py**: Kalshi markets API fetching (sync fallback)
- **get_current_markets.py**: Determines current active market URLs (UTC/ET timezone handling)
- **config/settings.py**: Environment variable configuration (pydantic settings)
- **traders/kalshi_trader.py**: Kalshi trading client (RSA-PSS signed API requests)
- **traders/polymarket_trader.py**: Polymarket CLOB trading client

### Frontend Components (`/frontend`)
- **app/page.tsx**: Main dashboard - polls backend, displays hero card, market cards, analysis table
- **components/ui/**: shadcn/ui components (Card, Badge, Table, Progress)
- Uses Tailwind CSS 4, React 19, TypeScript

### Pre-generated Data
- `market_urls_2025.txt`: Polymarket URLs for 2025
- `kalshi_urls_2025.txt`: Kalshi URLs for 2025

## Key Technical Details

### Arbitrage Logic
Selects Kalshi markets within ±5 positions of closest strike to Polymarket strike, then checks:
1. **Poly > Kalshi**: Buy Poly DOWN + Kalshi YES
2. **Poly < Kalshi**: Buy Poly UP + Kalshi NO
3. **Poly == Kalshi**: Check both strategies

Arbitrage exists when `total_cost < $1.00`, gross_margin = `$1.00 - total_cost`

**Important**: Gross margin ≠ Net profit. Fees must be subtracted.

### Fee Structure
**Polymarket US:**
- Trading: 0.01% taker fee (1 basis point)
- Gas: ~$0.02 per transaction on Polygon

**Kalshi:**
- Formula: `ceil(0.07 × contracts × price × (1-price))`
- Max: 1.75¢ per contract (at price = $0.50)
- Maker fees: $0

**Net Profitability:**
- `net_margin = gross_margin - (total_fees / contracts)`
- Kalshi fees dominate at ~350x Polymarket fees
- Typically need 3-5% gross margin for net profitability at 100 contracts

### Price Normalization
- Polymarket: CLOB API returns decimals (e.g., 0.38)
- Kalshi: API returns cents (0-100), converted to dollars in backend

### Timezone Handling
Markets defined in ET (Eastern Time), normalized to UTC internally using pytz.

## Configuration

Environment variables in `backend/.env` (or `.env` in project root for Docker):
```bash
# Kalshi (get from kalshi.com/account/api or demo.kalshi.co)
KALSHI_API_KEY_ID=your-key-id
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem  # Docker: /app/keys/kalshi_private_key.pem
KALSHI_USE_DEMO=true  # false for production

# Polymarket (export from wallet settings)
POLYMARKET_PRIVATE_KEY=0x...
POLYMARKET_FUNDER_ADDRESS=0x...
POLYMARKET_SIGNATURE_TYPE=1  # 0=EOA, 1=Email, 2=Browser

# Trading
PAPER_TRADING=true  # false for real trades
MIN_PROFIT_MARGIN=0.02
MAX_POSITION_SIZE=100

# VPN (Docker only - for Polymarket geo-restriction bypass)
MULLVAD_PRIVATE_KEY=...
MULLVAD_ADDRESS=...
```

## Code Style
- Python: PEP 8
- React: Functional components, TypeScript
- Styling: Tailwind CSS
