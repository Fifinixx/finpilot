import { AlertTriangleIcon, CalendarX2Icon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { EmptyState } from "@/components/states"
import { formatDate, formatMoney, formatPct, humanize } from "@/lib/format"
import type { GoalList } from "@/lib/types"

export function GoalsSummary({ goals }: { goals: GoalList }) {
  const { summary, results } = goals
  return (
    <Card>
      <CardHeader>
        <CardTitle>Financial goals</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {results.length === 0 ? (
          <EmptyState title="No goals recorded" />
        ) : (
          <>
            <dl className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <dt className="text-muted-foreground">Goals</dt>
                <dd className="text-xl font-semibold">{summary.goal_count}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Overall funded</dt>
                <dd className="text-xl font-semibold">{formatPct(summary.funded_pct)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Need attention</dt>
                <dd className="text-xl font-semibold">{summary.flagged_count}</dd>
              </div>
            </dl>
            <ul className="space-y-4">
              {results.map((g) => (
                <li key={g.id} className="space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <span className="font-medium">
                      {g.name} <span className="font-normal text-muted-foreground">· {humanize(g.goal_type)}</span>
                    </span>
                    <span className="flex flex-wrap gap-1.5">
                      {g.is_overdue && <Badge variant="destructive"><CalendarX2Icon />Overdue</Badge>}
                      {g.is_overfunded && <Badge variant="outline"><AlertTriangleIcon />Over-funded</Badge>}
                      <Badge variant={g.priority === "HIGH" ? "default" : "outline"}>{humanize(g.priority)} priority</Badge>
                    </span>
                  </div>
                  <Progress value={Math.min(g.funded_pct, 100)} aria-label={`${g.name} funded ${g.funded_pct}%`} />
                  <p className="text-xs text-muted-foreground">
                    {formatMoney(g.current_funded_amount)} of {formatMoney(g.target_amount)} ({formatPct(g.funded_pct)}) · target {formatDate(g.target_date)}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  )
}
