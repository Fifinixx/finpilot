"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { EmptyState, ErrorState, LoadingRows, Pagination } from "@/components/states"
import { formatDateTime, humanize } from "@/lib/format"
import { useImportBatches } from "@/lib/queries"

export function ImportHistory({ selectedId, onSelect }: { selectedId: number | null; onSelect: (id: number) => void }) {
  const [page, setPage] = useState(1)
  const { data, isPending, isError, error, refetch } = useImportBatches(page)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import history</CardTitle>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <LoadingRows rows={4} />
        ) : isError ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : data.count === 0 ? (
          <EmptyState title="No imports yet" description="Uploaded files will appear here." />
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Imported</TableHead>
                  <TableHead className="text-right">Duplicates</TableHead>
                  <TableHead className="text-right">Rejected</TableHead>
                  <TableHead>When</TableHead>
                  <TableHead>
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.results.map((b) => (
                  <TableRow key={b.id} data-state={b.id === selectedId ? "selected" : undefined}>
                    <TableCell className="tabular-nums">{b.id}</TableCell>
                    <TableCell>{humanize(b.entity)}</TableCell>
                    <TableCell className="max-w-48 truncate" title={b.file_name}>{b.file_name}</TableCell>
                    <TableCell>
                      <Badge variant={b.status === "COMPLETED" ? "secondary" : "destructive"}>{b.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{b.imported_count.toLocaleString("en-IN")}</TableCell>
                    <TableCell className="text-right tabular-nums">{b.duplicate_count.toLocaleString("en-IN")}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {b.rejected_count > 0 ? (
                        <span className="font-medium text-destructive">{b.rejected_count.toLocaleString("en-IN")}</span>
                      ) : (
                        0
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{formatDateTime(b.created_at)}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" onClick={() => onSelect(b.id)}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination page={data.page} totalPages={data.total_pages} count={data.count} label="imports" onPageChange={setPage} />
          </>
        )}
      </CardContent>
    </Card>
  )
}
