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

### Frontend (Next.js 16)
```bash
cd frontend
npm install                       # Install dependencies
npm run dev                       # Start dev server (localhost:3000)
npm run build                     # Build production bundle
npm run lint                      # Run ESLint
```

## Architecture

```
Frontend (Next.js)         Backend (FastAPI)           External APIs
     |                          |                           |
     |-- GET /arbitrage ------->|                           |
     |                          |-- Polymarket CLOB API --->|
     |                          |-- Kalshi Trade API ------>|
     |                          |-- Binance Price API ----->|
     |<-- JSON Response --------|                           |
     |                          |                           |
(polls every 1s)           (orchestrates & calculates)
```

### Backend Modules (`/backend`)
- **api.py**: FastAPI server, single `/arbitrage` endpoint, coordinates data fetching
- **arbitrage_bot.py**: Standalone CLI monitoring script
- **fetch_current_polymarket.py**: Polymarket CLOB API + Binance price fetching
- **fetch_current_kalshi.py**: Kalshi markets API fetching
- **get_current_markets.py**: Determines current active market URLs (UTC/ET timezone handling)
- **find_new_market.py** / **find_new_kalshi_market.py**: URL generation utilities

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

Arbitrage exists when `total_cost < $1.00`, margin = `$1.00 - total_cost`

### Price Normalization
- Polymarket: CLOB API returns decimals (e.g., 0.38)
- Kalshi: API returns cents (0-100), converted to dollars in backend

### Timezone Handling
Markets defined in ET (Eastern Time), normalized to UTC internally using pytz.

## Code Style
- Python: PEP 8
- React: Functional components, TypeScript
- Styling: Tailwind CSS
