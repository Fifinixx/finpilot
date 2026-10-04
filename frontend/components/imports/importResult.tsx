import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatDateTime, humanize } from "@/lib/format"
import type { ImportBatchDetail } from "@/lib/types"

const MAX_ROWS_SHOWN = 200

export function ImportResult({ batch }: { batch: ImportBatchDetail }) {
  const stats = [
    { label: "Rows in file", value: batch.total_rows },
    { label: "Imported", value: batch.imported_count },
    { label: "Duplicates skipped", value: batch.duplicate_count },
    { label: "Rejected", value: batch.rejected_count },
  ]
  const shown = batch.rejections.slice(0, MAX_ROWS_SHOWN)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          Import #{batch.id} · {humanize(batch.entity)}
          <Badge variant={batch.status === "COMPLETED" ? "secondary" : "destructive"}>{batch.status}</Badge>
        </CardTitle>
        <CardDescription>
          {batch.file_name} · {formatDateTime(batch.created_at)}
          {batch.created_by && ` · by ${batch.created_by}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {batch.error && <p className="text-sm text-destructive">{batch.error}</p>}

        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-lg border p-3">
              <dt className="text-xs text-muted-foreground">{s.label}</dt>
              <dd className="text-2xl font-semibold">{s.value.toLocaleString("en-IN")}</dd>
            </div>
          ))}
        </dl>

        {batch.rejections.length > 0 ? (
          <div className="space-y-2">
            <h3 className="text-sm font-medium">Rejected rows</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Line</TableHead>
                  <TableHead>Problems</TableHead>
                  <TableHead>Row data</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((r) => (
                  <TableRow key={r.row_number} className="align-top">
                    <TableCell className="tabular-nums">{r.row_number}</TableCell>
                    <TableCell className="whitespace-normal">
                      <ul className="space-y-1">
                        {r.errors.map((e, i) => (
                          <li key={i}>
                            <span className="font-mono text-xs text-muted-foreground">{e.field}</span>{" "}
                            <span className="text-destructive">{e.message}</span>
                          </li>
                        ))}
                      </ul>
                    </TableCell>
                    <TableCell className="whitespace-normal font-mono text-xs text-muted-foreground">
                      {Object.entries(r.raw)
                        .map(([k, v]) => `${k}=${v}`)
                        .join("  ")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {batch.rejections.length > MAX_ROWS_SHOWN && (
              <p className="text-sm text-muted-foreground">
                Showing the first {MAX_ROWS_SHOWN} of {batch.rejections.length} rejected rows.
              </p>
            )}
          </div>
        ) : (
          batch.status === "COMPLETED" && <p className="text-sm text-muted-foreground">No rows were rejected.</p>
        )}
      </CardContent>
    </Card>
  )
}
