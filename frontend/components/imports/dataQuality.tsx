"use client"

import { useState } from "react"
import Link from "next/link"
import { cn } from "cn"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState, ErrorState, LoadingRows, Pagination } from "@/components/states"
import { humanize } from "@/lib/format"
import { useDataQuality } from "@/lib/queries"

/** Reads the portfolio_reconciliation_exception SQL view via /admin/data-quality. */
export function DataQuality() {
  const [type, setType] = useState("")
  const [page, setPage] = useState(1)
  const { data, isPending, isError, error, refetch, isFetching } = useDataQuality(type, page)

  const select = (next: string) => {
    setType(next === type ? "" : next) // clicking the active filter clears it
    setPage(1)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data quality</CardTitle>
        <CardDescription>
          Issues found in loaded data and import logs. Accepted rows are kept but listed here for review.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isPending ? (
          <LoadingRows rows={4} />
        ) : isError ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : data.summary.length === 0 ? (
          <EmptyState title="No data-quality issues" />
        ) : (
          <>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by issue type">
              {data.summary.map((s) => (
                <button
                  key={s.exception_type}
                  type="button"
                  aria-pressed={type === s.exception_type}
                  onClick={() => select(s.exception_type)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-left text-sm transition-colors hover:bg-muted",
                    type === s.exception_type && "border-foreground bg-muted",
                  )}
                >
                  <span className="block text-xs text-muted-foreground">{humanize(s.exception_type)}</span>
                  <span className="font-semibold tabular-nums">{s.count.toLocaleString("en-IN")}</span>
                </button>
              ))}
            </div>
            <div className={isFetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Issue</TableHead>
                    <TableHead>Record</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Detail</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.results.map((r) => (
                    <TableRow key={`${r.exception_type}-${r.entity_id}-${r.detail}`}>
                      <TableCell className="whitespace-nowrap">{humanize(r.exception_type)}</TableCell>
                      <TableCell>
                        <span className="text-muted-foreground">{humanize(r.entity)} </span>
                        <span className="font-mono text-xs">{r.entity_id}</span>
                      </TableCell>
                      <TableCell>
                        {r.customer_id ? (
                          <Link href={`/customers/${r.customer_id}`} className="font-mono text-xs hover:underline">
                            {r.customer_id}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="whitespace-normal text-muted-foreground">{r.detail}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination page={data.page} totalPages={data.total_pages} count={data.count} label="issues" onPageChange={setPage} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
