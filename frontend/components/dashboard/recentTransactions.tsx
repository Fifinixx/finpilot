"use client"

import { cn } from "cn"
import { TransactionStatusBadge } from "@/components/badges"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState, ErrorState, LoadingRows } from "@/components/states"
import { formatDate, formatMoneyPrecise, humanize } from "@/lib/format"
import { useTransactions } from "@/lib/queries"

export function RecentTransactions({ customerId }: { customerId: string }) {
  const { data, isPending, isError, error, refetch } = useTransactions(customerId, { page_size: 8 })

  if (isPending) return <LoadingRows rows={5} />
  if (isError) return <ErrorState error={error} onRetry={refetch} />
  if (data.count === 0) return <EmptyState title="No transactions yet" />

  return (
    <div className="space-y-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Instrument</TableHead>
            <TableHead>Account</TableHead>
            <TableHead className="text-right">Amount</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.results.map((t) => {
            const reversed = t.status === "REVERSED"
            return (
              <TableRow key={t.id} className={cn(reversed && "text-muted-foreground")}>
                <TableCell className="tabular-nums">{formatDate(t.trade_date)}</TableCell>
                <TableCell>{humanize(t.transaction_type)}</TableCell>
                <TableCell>{t.symbol}</TableCell>
                <TableCell className="font-mono text-xs">{t.account_id}</TableCell>
                <TableCell className={cn("text-right tabular-nums", reversed && "line-through")}>
                  {formatMoneyPrecise(t.amount)}
                </TableCell>
                <TableCell><TransactionStatusBadge status={t.status} /></TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      <p className="text-xs text-muted-foreground">
        Latest {data.results.length} of {data.count.toLocaleString("en-IN")} transactions
      </p>
    </div>
  )
}
