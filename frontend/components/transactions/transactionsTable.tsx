import { cn } from "cn"
import { TransactionStatusBadge } from "@/components/badges"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatDate, formatMoneyPrecise, formatNumber, humanize } from "@/lib/format"
import type { Transaction } from "@/lib/types"

export function TransactionsTable({ transactions }: { transactions: Transaction[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Date</TableHead>
          <TableHead>ID</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Instrument</TableHead>
          <TableHead>Account</TableHead>
          <TableHead className="text-right">Quantity</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {transactions.map((t) => {
          const reversed = t.status === "REVERSED"
          const pending = t.status === "PENDING"
          const cash = t.transaction_type === "DIVIDEND" || t.transaction_type === "FEE"
          return (
            <TableRow
              key={t.id}
              className={cn(reversed && "text-muted-foreground", pending && "bg-muted/30")}
            >
              <TableCell className="tabular-nums">{formatDate(t.trade_date)}</TableCell>
              <TableCell className="font-mono text-xs">{t.id}</TableCell>
              <TableCell>{humanize(t.transaction_type)}</TableCell>
              <TableCell>
                <div className="font-medium">{t.symbol}</div>
                <div className="text-xs text-muted-foreground">{t.instrument_name}</div>
              </TableCell>
              <TableCell className="font-mono text-xs">{t.account_id}</TableCell>
              <TableCell className="text-right tabular-nums">{cash ? "—" : formatNumber(t.quantity)}</TableCell>
              <TableCell className="text-right tabular-nums">{cash ? "—" : formatMoneyPrecise(t.price)}</TableCell>
              <TableCell className={cn("text-right font-medium tabular-nums", reversed && "line-through")}>
                {formatMoneyPrecise(t.amount)}
              </TableCell>
              <TableCell><TransactionStatusBadge status={t.status} /></TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
