"use client"

import { useState } from "react"
import { formatMoney, formatPct, humanize } from "@/lib/format"
import type { AssetClass, Portfolio } from "@/lib/types"

// Categorical slots (dark steps), validated as an adjacent set with the dataviz
// palette checker. Colour belongs to the asset class, never to its rank, and
// segments keep this fixed order so only validated pairs ever touch.
const ASSET_CLASS_ORDER: AssetClass[] = ["EQUITY", "ETF", "MUTUAL_FUND", "BOND", "REIT", "GSEC"]
export const ASSET_CLASS_COLOR: Record<AssetClass, string> = {
  EQUITY: "#3987e5",
  ETF: "#d95926",
  MUTUAL_FUND: "#199e70",
  BOND: "#c98500",
  REIT: "#d55181",
  GSEC: "#008300",
}

export function AllocationChart({ allocation }: { allocation: Portfolio["allocation"] }) {
  const [active, setActive] = useState<AssetClass | null>(null)
  const rows = [...allocation].sort(
    (a, b) => ASSET_CLASS_ORDER.indexOf(a.asset_class) - ASSET_CLASS_ORDER.indexOf(b.asset_class),
  )
  const activeRow = rows.find((r) => r.asset_class === active)
  const summary = rows.map((r) => `${humanize(r.asset_class)} ${formatPct(r.weight_pct)}`).join(", ")

  return (
    <div className="space-y-4">
      {/* Tooltip line: reserved height so hovering never shifts the layout. */}
      <p className="h-5 text-sm" aria-live="polite">
        {activeRow ? (
          <>
            <span className="font-medium">{humanize(activeRow.asset_class)}</span>
            <span className="text-muted-foreground"> · {formatMoney(activeRow.market_value)} · {formatPct(activeRow.weight_pct)}</span>
          </>
        ) : (
          <span className="text-muted-foreground">Hover or focus a segment for details</span>
        )}
      </p>

      <div role="img" aria-label={`Asset allocation: ${summary}`} className="flex h-6 w-full gap-[2px]" onMouseLeave={() => setActive(null)}>
        {rows.map((r, i) => (
          <div
            key={r.asset_class}
            tabIndex={0}
            aria-label={`${humanize(r.asset_class)} ${formatPct(r.weight_pct)}`}
            onMouseEnter={() => setActive(r.asset_class)}
            onFocus={() => setActive(r.asset_class)}
            onBlur={() => setActive(null)}
            className="h-full min-w-[3px] outline-none transition-opacity focus-visible:ring-2 focus-visible:ring-ring"
            style={{
              flexGrow: Number(r.weight_pct),
              flexBasis: 0,
              backgroundColor: ASSET_CLASS_COLOR[r.asset_class],
              opacity: active && active !== r.asset_class ? 0.45 : 1,
              borderTopLeftRadius: i === 0 ? 4 : 0,
              borderBottomLeftRadius: i === 0 ? 4 : 0,
              borderTopRightRadius: i === rows.length - 1 ? 4 : 0,
              borderBottomRightRadius: i === rows.length - 1 ? 4 : 0,
            }}
          />
        ))}
      </div>

      {/* Legend doubles as the accessible table view. */}
      <table className="w-full text-sm">
        <caption className="sr-only">Asset allocation by market value</caption>
        <thead className="sr-only">
          <tr><th>Asset class</th><th>Market value</th><th>Weight</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.asset_class}
              className="border-b last:border-0"
              onMouseEnter={() => setActive(r.asset_class)}
              onMouseLeave={() => setActive(null)}
            >
              <td className="py-1.5">
                <span className="inline-flex items-center gap-2">
                  <span aria-hidden className="size-2.5 rounded-sm" style={{ backgroundColor: ASSET_CLASS_COLOR[r.asset_class] }} />
                  {humanize(r.asset_class)}
                </span>
              </td>
              <td className="py-1.5 text-right tabular-nums text-muted-foreground">{formatMoney(r.market_value)}</td>
              <td className="w-20 py-1.5 text-right font-medium tabular-nums">{formatPct(r.weight_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
