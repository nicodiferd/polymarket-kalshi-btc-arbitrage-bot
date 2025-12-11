"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { AlertCircle, TrendingUp, Power, Zap, Settings, Clock } from "lucide-react"

interface TradingState {
  auto_trade_enabled: boolean
  kalshi_ready: boolean
  polymarket_ready: boolean
  paper_trading: boolean
  last_auto_trade: string | null
}

interface FeeBreakdown {
  polymarket_trading: number
  polymarket_gas: number
  kalshi: number
  total: number
}

interface Check {
  kalshi_strike: number
  type: string
  poly_leg: string
  kalshi_leg: string
  poly_cost: number
  kalshi_cost: number
  total_cost: number
  is_arbitrage: boolean
  margin: number
  gross_margin: number
  net_margin: number
  fees: FeeBreakdown
  is_profitable_after_fees: boolean
  hour_boundary_blocked?: boolean
}

interface HourBoundaryProtection {
  active: boolean
  minutes_until_safe: number
  reason: string | null
}

interface MarketData {
  timestamp: string
  contracts: number
  polymarket: {
    price_to_beat: number
    current_price: number
    prices: {
      Up: number
      Down: number
    }
    slug: string
  }
  kalshi: {
    event_ticker: string
    current_price: number
    markets: Array<{
      strike: number
      yes_ask: number
      no_ask: number
      subtitle: string
    }>
  }
  checks: Check[]
  opportunities: Check[]
  errors: string[]
  trading?: TradingState
  hour_boundary_protection?: HourBoundaryProtection
}

export default function Dashboard() {
  const [data, setData] = useState<MarketData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
  const [autoTradeEnabled, setAutoTradeEnabled] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [contracts, setContracts] = useState(100)

  const fetchData = async () => {
    try {
      const res = await fetch(`http://localhost:8000/arbitrage?contracts=${contracts}`)
      const json = await res.json()
      setData(json)
      setLastUpdated(new Date())
      setLoading(false)
      // Sync auto-trade state from server
      if (json.trading) {
        setAutoTradeEnabled(json.trading.auto_trade_enabled)
      }
    } catch (err) {
      console.error("Failed to fetch data", err)
    }
  }

  const toggleAutoTrade = async () => {
    try {
      const newState = !autoTradeEnabled
      const res = await fetch(`http://localhost:8000/trading/auto-trade?enabled=${newState}`, {
        method: 'POST',
      })
      const json = await res.json()
      setAutoTradeEnabled(json.auto_trade_enabled)
    } catch (err) {
      console.error("Failed to toggle auto-trade", err)
    }
  }

  const executeManualTrade = async (opportunity: any) => {
    if (isExecuting) return
    setIsExecuting(true)
    try {
      const res = await fetch("http://localhost:8000/trading/execute", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kalshi_strike: opportunity.kalshi_strike,
          poly_leg: opportunity.poly_leg,
          kalshi_leg: opportunity.kalshi_leg,
          poly_cost: opportunity.poly_cost,
          kalshi_cost: opportunity.kalshi_cost,
          quantity: 1,
        }),
      })
      const json = await res.json()
      console.log("Trade executed:", json)
      alert(json.paper_trading
        ? `Paper trade executed! Status: ${json.trade.status}`
        : `Trade executed! Status: ${json.trade.status}`)
    } catch (err) {
      console.error("Failed to execute trade", err)
      alert("Trade execution failed")
    } finally {
      setIsExecuting(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 1000)
    return () => clearInterval(interval)
  }, [contracts])

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>

  if (!data) return <div className="p-8">No data available</div>

  const bestOpp = data.opportunities.length > 0
    ? data.opportunities.reduce((prev, current) => (prev.margin > current.margin) ? prev : current)
    : null

  return (
    <div className="p-8 space-y-8 bg-slate-50 min-h-screen">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight">Arbitrage Bot Dashboard</h1>
          <Badge variant="outline" className="animate-pulse bg-green-100 text-green-800 border-green-200">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            Live
          </Badge>
        </div>
        <div className="text-sm text-muted-foreground">
          Last updated: {lastUpdated.toLocaleTimeString()}
        </div>
      </div>

      {/* Trading Controls */}
      <Card className="border-2 border-slate-200">
        <CardContent className="py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-slate-500" />
                <span className="font-semibold">Trading Controls</span>
              </div>

              {/* Platform Status */}
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Kalshi:</span>
                <Badge variant={data.trading?.kalshi_ready ? "default" : "secondary"} className={data.trading?.kalshi_ready ? "bg-green-600" : ""}>
                  {data.trading?.kalshi_ready ? "Ready" : "Not Connected"}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">Polymarket:</span>
                <Badge variant={data.trading?.polymarket_ready ? "default" : "secondary"} className={data.trading?.polymarket_ready ? "bg-green-600" : ""}>
                  {data.trading?.polymarket_ready ? "Ready" : "Not Connected"}
                </Badge>
              </div>

              {/* Paper Trading Indicator */}
              {data.trading?.paper_trading && (
                <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
                  Paper Trading Mode
                </Badge>
              )}
            </div>

            {/* Contract Quantity */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Contracts:</span>
              <select
                value={contracts}
                onChange={(e) => setContracts(Number(e.target.value))}
                className="border rounded px-2 py-1 text-sm bg-white"
              >
                <option value={10}>10</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={250}>250</option>
                <option value={500}>500</option>
                <option value={1000}>1,000</option>
              </select>
            </div>

            {/* Auto Trade Toggle */}
            <div className="flex items-center gap-3">
              <Button
                variant={autoTradeEnabled ? "default" : "outline"}
                className={autoTradeEnabled ? "bg-green-600 hover:bg-green-700" : ""}
                onClick={toggleAutoTrade}
              >
                <Power className="h-4 w-4 mr-2" />
                Auto-Trade: {autoTradeEnabled ? "ON" : "OFF"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {data.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md flex items-start gap-2">
          <AlertCircle className="h-5 w-5 mt-0.5" />
          <div>
            <strong className="font-bold block mb-1">Errors Detected:</strong>
            <ul className="list-disc ml-5 text-sm">
              {data.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Hour Boundary Protection Warning */}
      {data.hour_boundary_protection?.active && (
        <div className="bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-md flex items-center gap-3">
          <Clock className="h-5 w-5 flex-shrink-0" />
          <div className="flex-1">
            <strong className="font-semibold">Market Transition in Progress</strong>
            <p className="text-sm">
              Hour boundary detected - trading paused to avoid false signals from closing/opening markets.
              Resuming in <span className="font-mono font-bold">{data.hour_boundary_protection.minutes_until_safe}</span> minute{data.hour_boundary_protection.minutes_until_safe !== 1 ? 's' : ''}.
            </p>
          </div>
          <Badge variant="outline" className="bg-amber-100 text-amber-700 border-amber-400 flex-shrink-0">
            Paused
          </Badge>
        </div>
      )}

      {/* Best Opportunity Hero Card */}
      {bestOpp ? (
        <Card className={`bg-gradient-to-r shadow-sm ${bestOpp.is_profitable_after_fees ? 'from-green-50 to-emerald-50 border-green-200' : 'from-yellow-50 to-amber-50 border-yellow-200'}`}>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className={`flex items-center gap-2 ${bestOpp.is_profitable_after_fees ? 'text-green-700' : 'text-yellow-700'}`}>
                <TrendingUp className="h-5 w-5" />
                <CardTitle>{bestOpp.is_profitable_after_fees ? 'Profitable Opportunity Found' : 'Opportunity Found (Unprofitable After Fees)'}</CardTitle>
              </div>
              <Button
                className={data.hour_boundary_protection?.active ? "bg-amber-600 hover:bg-amber-700" : bestOpp.is_profitable_after_fees ? "bg-green-600 hover:bg-green-700" : "bg-yellow-600 hover:bg-yellow-700"}
                onClick={() => executeManualTrade(bestOpp)}
                disabled={isExecuting || !bestOpp.is_profitable_after_fees || data.hour_boundary_protection?.active}
              >
                {data.hour_boundary_protection?.active ? (
                  <>
                    <Clock className="h-4 w-4 mr-2" />
                    Paused - {data.hour_boundary_protection.minutes_until_safe}m
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    {isExecuting ? "Executing..." : `Buy ${contracts} Contracts`}
                  </>
                )}
              </Button>
            </div>
            <CardDescription>
              {bestOpp.is_profitable_after_fees
                ? `Net profit of $${(bestOpp.net_margin * contracts).toFixed(2)} on ${contracts} contracts`
                : `Fees exceed gross margin - need larger spread`}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row justify-between items-start gap-4">
              {/* Margin Display */}
              <div className="flex gap-6">
                <div className="text-center">
                  <div className="text-xs text-muted-foreground uppercase">Gross Margin</div>
                  <div className="text-2xl font-bold text-slate-600">${bestOpp.gross_margin?.toFixed(3) || '0.000'}</div>
                  <div className="text-xs text-slate-500">per contract</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-muted-foreground uppercase">Net Margin</div>
                  <div className={`text-2xl font-bold ${bestOpp.net_margin > 0 ? 'text-green-700' : 'text-red-600'}`}>
                    ${bestOpp.net_margin?.toFixed(3) || '0.000'}
                  </div>
                  <div className="text-xs text-slate-500">after fees</div>
                </div>
                <div className="text-center">
                  <div className="text-xs text-muted-foreground uppercase">Total Profit</div>
                  <div className={`text-2xl font-bold ${bestOpp.net_margin > 0 ? 'text-green-700' : 'text-red-600'}`}>
                    ${((bestOpp.net_margin || 0) * contracts).toFixed(2)}
                  </div>
                  <div className="text-xs text-slate-500">{contracts} contracts</div>
                </div>
              </div>

              {/* Strategy & Fees */}
              <div className="flex-1 bg-white p-4 rounded-lg border border-slate-200 w-full">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-slate-700">Strategy</span>
                  <Badge className={bestOpp.is_profitable_after_fees ? "bg-green-600" : "bg-yellow-600"}>
                    {bestOpp.is_profitable_after_fees ? 'Profitable' : 'Unprofitable'}
                  </Badge>
                </div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Polymarket {bestOpp.poly_leg}</span>
                  <span className="font-mono">${bestOpp.poly_cost.toFixed(3)}</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Kalshi {bestOpp.kalshi_leg} (${bestOpp.kalshi_strike.toLocaleString()})</span>
                  <span className="font-mono">${bestOpp.kalshi_cost.toFixed(3)}</span>
                </div>
                <div className="pt-2 border-t border-dashed border-slate-200 flex justify-between text-sm">
                  <span>Total Cost</span>
                  <span className="font-mono font-semibold">${bestOpp.total_cost.toFixed(3)}</span>
                </div>

                {/* Fee Breakdown */}
                {bestOpp.fees && (
                  <div className="mt-3 pt-2 border-t border-slate-200">
                    <div className="text-xs text-muted-foreground uppercase mb-1">Fees ({contracts} contracts)</div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                      <span className="text-slate-500">Polymarket:</span>
                      <span className="font-mono text-right">${(bestOpp.fees.polymarket_trading + bestOpp.fees.polymarket_gas).toFixed(4)}</span>
                      <span className="text-slate-500">Kalshi:</span>
                      <span className="font-mono text-right">${bestOpp.fees.kalshi.toFixed(4)}</span>
                      <span className="text-slate-600 font-medium">Total Fees:</span>
                      <span className="font-mono text-right font-medium">${bestOpp.fees.total.toFixed(4)}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-gradient-to-r from-slate-50 to-slate-100 border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2 text-slate-600">
              <TrendingUp className="h-5 w-5" />
              <CardTitle>No Arbitrage Opportunities</CardTitle>
            </div>
            <CardDescription>Markets are currently efficient - monitoring for price discrepancies</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-sm text-muted-foreground">Best Total Cost</div>
                <div className="text-3xl font-bold text-slate-600">
                  ${data.checks.length > 0 ? Math.min(...data.checks.map(c => c.total_cost)).toFixed(3) : "N/A"}
                </div>
                <div className="text-xs text-slate-500">Need &lt; $1.00 for arbitrage</div>
              </div>
              <div className="flex-1 text-sm text-slate-500">
                <p>The bot is actively scanning {data.checks.length} strike combinations every second. An opportunity will appear here when the combined cost of opposing positions drops below $1.00.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Polymarket Card */}
        <Card>
          <CardHeader>
            <CardTitle>Polymarket</CardTitle>
            <CardDescription>Target: {data.polymarket.slug}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-100 p-3 rounded-md">
                  <div className="text-xs text-muted-foreground uppercase font-bold">Price to Beat</div>
                  <div className="text-xl font-mono font-semibold">${data.polymarket.price_to_beat?.toLocaleString()}</div>
                </div>
                <div className="bg-slate-100 p-3 rounded-md">
                  <div className="text-xs text-muted-foreground uppercase font-bold">Current Price</div>
                  <div className="text-xl font-mono font-semibold">${data.polymarket.current_price?.toLocaleString()}</div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span>UP Contract</span>
                  <span className="font-mono font-medium">${data.polymarket.prices.Up?.toFixed(3)}</span>
                </div>
                <Progress value={data.polymarket.prices.Up * 100} className="h-2 bg-slate-100" indicatorClassName="bg-green-500" />

                <div className="flex justify-between items-center text-sm mt-2">
                  <span>DOWN Contract</span>
                  <span className="font-mono font-medium">${data.polymarket.prices.Down?.toFixed(3)}</span>
                </div>
                <Progress value={data.polymarket.prices.Down * 100} className="h-2 bg-slate-100" indicatorClassName="bg-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Kalshi Card */}
        <Card>
          <CardHeader>
            <CardTitle>Kalshi</CardTitle>
            <CardDescription>Ticker: {data.kalshi.event_ticker}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-slate-100 p-3 rounded-md mb-4">
                <div className="text-xs text-muted-foreground uppercase font-bold">Current Price</div>
                <div className="text-xl font-mono font-semibold">${data.kalshi.current_price?.toLocaleString()}</div>
              </div>

              <div className="space-y-3 max-h-[200px] overflow-y-auto pr-2">
                {data.kalshi.markets
                  .filter(m => Math.abs(m.strike - data.polymarket.price_to_beat) < 2500)
                  .map((m, i) => (
                    <div key={i} className="text-sm border-b pb-2 last:border-0">
                      <div className="flex justify-between font-medium mb-1">
                        <span>{m.subtitle}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Yes: {m.yes_ask}¢</span>
                          <span>No: {m.no_ask}¢</span>
                        </div>
                        <div className="flex h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                          <div className="bg-green-500 h-full" style={{ width: `${m.yes_ask}%` }}></div>
                          <div className="bg-red-500 h-full" style={{ width: `${m.no_ask}%` }}></div>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Arbitrage Checks Table */}
      <Card>
        <CardHeader>
          <CardTitle>Arbitrage Analysis</CardTitle>
          <CardDescription>Real-time comparison of all potential strategies</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[100px]">Type</TableHead>
                <TableHead>Kalshi Strike</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Cost Analysis</TableHead>
                <TableHead className="text-right">Total Cost</TableHead>
                <TableHead className="text-right">Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.checks.map((check, i) => {
                const hasGrossArb = check.total_cost < 1.00
                const isNetProfitable = check.is_profitable_after_fees
                const percentCost = Math.min(check.total_cost * 100, 100)

                return (
                  <TableRow key={i} className={isNetProfitable ? "bg-green-50/50" : hasGrossArb ? "bg-yellow-50/30" : ""}>
                    <TableCell>
                      <Badge variant="outline" className="whitespace-nowrap">
                        {check.type.replace("Poly", "P").replace("Kalshi", "K")}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      ${check.kalshi_strike.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-xs">
                      <div className="flex flex-col">
                        <span>Buy P-{check.poly_leg}</span>
                        <span>Buy K-{check.kalshi_leg}</span>
                      </div>
                    </TableCell>
                    <TableCell className="w-[30%]">
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>${check.poly_cost.toFixed(3)} + ${check.kalshi_cost.toFixed(3)}</span>
                          <span>{Math.round(check.total_cost * 100)}%</span>
                        </div>
                        <Progress
                          value={percentCost}
                          className="h-2"
                          indicatorClassName={isNetProfitable ? "bg-green-500" : hasGrossArb ? "bg-yellow-500" : "bg-slate-400"}
                        />
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-mono font-bold">
                      ${check.total_cost.toFixed(3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {check.hour_boundary_blocked ? (
                        <div className="flex flex-col items-end">
                          <Badge variant="outline" className="text-amber-600 border-amber-400 whitespace-nowrap">
                            <Clock className="h-3 w-3 mr-1" />
                            Blocked
                          </Badge>
                          <span className="text-xs text-muted-foreground mt-1">
                            Market transition
                          </span>
                        </div>
                      ) : isNetProfitable ? (
                        <div className="flex flex-col items-end">
                          <Badge className="bg-green-600 hover:bg-green-700 whitespace-nowrap">
                            +${check.net_margin?.toFixed(3)} net
                          </Badge>
                          <span className="text-xs text-muted-foreground mt-1">
                            (${check.gross_margin?.toFixed(3)} gross)
                          </span>
                        </div>
                      ) : hasGrossArb ? (
                        <div className="flex flex-col items-end">
                          <Badge variant="outline" className="text-yellow-600 border-yellow-400 whitespace-nowrap">
                            ${check.net_margin?.toFixed(3)} net
                          </Badge>
                          <span className="text-xs text-muted-foreground mt-1">
                            Fees: ${check.fees?.total?.toFixed(2)}
                          </span>
                        </div>
                      ) : (
                        <Badge variant="outline" className="text-slate-500 border-slate-300">
                          No Arb
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
