import { cn } from "cn"
import { formatMoney, formatPct, formatSigned } from "@/lib/format"

/** Gain/loss: the +/− sign carries the meaning; colour only reinforces it. */
export function Gain({ value, pct, className }: { value: string; pct?: string | null; className?: string }) {
  const n = Number(value)
  return (
    <span className={cn("tabular-nums", n > 0 && "text-[#0ca30c]", n < 0 && "text-destructive", className)}>
      {formatSigned(formatMoney(value), value)}
      {pct != null && <span className="ml-1 text-xs">({formatSigned(formatPct(pct), pct)})</span>}
    </span>
  )
}
