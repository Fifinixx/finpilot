import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState } from "@/components/states"
import { formatMoney, formatMoneyPrecise, formatNumber, humanize } from "@/lib/format"
import type { Position } from "@/lib/types"
import { ASSET_CLASS_COLOR } from "./allocationChart"
import { Gain } from "./gain"

export function PositionsTable({ positions }: { positions: Position[] }) {
  if (positions.length === 0) return <EmptyState title="No positions in the latest snapshot" />
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Instrument</TableHead>
          <TableHead>Asset class</TableHead>
          <TableHead>Account</TableHead>
          <TableHead className="text-right">Quantity</TableHead>
          <TableHead className="text-right">Avg cost</TableHead>
          <TableHead className="text-right">Last price</TableHead>
          <TableHead className="text-right">Market value</TableHead>
          <TableHead className="text-right">Unrealised gain / loss</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((p) => (
          <TableRow key={`${p.account_id}-${p.instrument_id}`}>
            <TableCell>
              <div className="font-medium">{p.symbol}</div>
              <div className="text-xs text-muted-foreground">{p.name}</div>
            </TableCell>
            <TableCell>
              <span className="inline-flex items-center gap-2">
                <span aria-hidden className="size-2.5 rounded-sm" style={{ backgroundColor: ASSET_CLASS_COLOR[p.asset_class] }} />
                {humanize(p.asset_class)}
              </span>
            </TableCell>
            <TableCell className="font-mono text-xs">{p.account_id}</TableCell>
            <TableCell className="text-right tabular-nums">{formatNumber(p.quantity)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatMoneyPrecise(p.avg_cost)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatMoneyPrecise(p.last_price)}</TableCell>
            <TableCell className="text-right font-medium tabular-nums">{formatMoney(p.market_value)}</TableCell>
            <TableCell className="text-right">
              <Gain value={p.unrealised_gain} pct={p.unrealised_gain_pct} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
