import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { EmptyState } from "@/components/states"
import { formatDate, humanize } from "@/lib/format"
import type { RiskProfile } from "@/lib/types"

export function RiskSummary({ risk }: { risk: RiskProfile | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk profile</CardTitle>
      </CardHeader>
      <CardContent>
        {!risk ? (
          <EmptyState title="No risk profile on file" />
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-2xl font-semibold">{risk.risk_level}</p>
              <p className="text-xs text-muted-foreground">Assessed {formatDate(risk.assessed_at)}</p>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground" id="risk-score-label">Risk score</span>
                <span className="font-medium tabular-nums">{risk.risk_score} / 100</span>
              </div>
              <Progress value={risk.risk_score} aria-labelledby="risk-score-label" />
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-muted-foreground">Horizon</dt>
                <dd className="font-medium">{risk.horizon_years} years</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Liquidity need</dt>
                <dd className="font-medium">{humanize(risk.liquidity_need)}</dd>
              </div>
            </dl>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
