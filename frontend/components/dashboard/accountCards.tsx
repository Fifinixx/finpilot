import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyState } from "@/components/states"
import { formatMoney, humanize } from "@/lib/format"
import type { PortfolioAccount } from "@/lib/types"
import { Gain } from "./gain"

export function AccountCards({ accounts }: { accounts: PortfolioAccount[] }) {
  if (accounts.length === 0) return <EmptyState title="No accounts" />
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {accounts.map((a) => (
        <Card key={a.account_id} size="sm">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-2">
              {humanize(a.account_type)}
              <Badge variant={a.status === "ACTIVE" ? "secondary" : "outline"}>{humanize(a.status)}</Badge>
            </CardTitle>
            <CardDescription>
              <span className="font-mono">{a.account_id}</span> · {a.provider}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-2xl font-semibold">{formatMoney(a.market_value)}</p>
            {Number(a.cost_basis) > 0 ? (
              <p className="text-sm">
                <Gain value={a.unrealised_gain} pct={a.unrealised_gain_pct} />
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">No positions in the latest snapshot</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
