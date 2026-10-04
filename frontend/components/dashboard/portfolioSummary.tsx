import { AlertTriangleIcon } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { formatDate, formatMoney } from "@/lib/format"
import type { Portfolio } from "@/lib/types"
import { Gain } from "./gain"

export function PortfolioSummary({ portfolio }: { portfolio: Portfolio }) {
  const { totals } = portfolio
  return (
    <Card>
      <CardContent className="grid gap-6 sm:grid-cols-[2fr_1fr_1fr_1fr]">
        <div>
          <p className="text-sm text-muted-foreground">Total portfolio value</p>
          <p className="text-5xl font-semibold tracking-tight">{formatMoney(totals.market_value)}</p>
          <p className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
            {portfolio.prices_mixed_dates && <AlertTriangleIcon className="size-3.5 text-[#fab219]" aria-label="Warning" />}
            Holdings as of {formatDate(portfolio.snapshot_date)} · prices as of {formatDate(portfolio.price_as_of)}
            {portfolio.prices_mixed_dates && " (some prices are older)"}
          </p>
        </div>
        <Stat label="Unrealised gain / loss">
          <Gain value={totals.unrealised_gain} pct={totals.unrealised_gain_pct} />
        </Stat>
        <Stat label="Cost basis">{formatMoney(totals.cost_basis)}</Stat>
        <Stat label="Positions">{totals.position_count}</Stat>
      </CardContent>
    </Card>
  )
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold">{children}</p>
    </div>
  )
}
