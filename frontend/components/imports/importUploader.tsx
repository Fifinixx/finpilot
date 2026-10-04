"use client"

import { useRef, useState } from "react"
import { UploadIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ErrorState } from "@/components/states"
import { ApiError } from "@/lib/api"
import { useUploadImport } from "@/lib/queries"
import type { ImportBatchDetail, ImportEntity } from "@/lib/types"

// Listed in dependency order: parents must be loaded before the files that reference them.
const ENTITIES: { value: ImportEntity; label: string }[] = [
  { value: "transactions", label: "Transactions" },
  { value: "holdings", label: "Holdings snapshot" },
  { value: "goals", label: "Goals" },
  { value: "risk_profiles", label: "Risk profiles" },
  { value: "customers", label: "Customers" },
  { value: "accounts", label: "Accounts" },
  { value: "instruments", label: "Instruments" },
]

const MAX_BYTES = 10 * 1024 * 1024

export function ImportUploader({ onImported, onShowBatch }: {
  onImported: (batch: ImportBatchDetail) => void
  onShowBatch: (id: number) => void
}) {
  const [entity, setEntity] = useState<ImportEntity>("transactions")
  const [file, setFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const upload = useUploadImport()

  function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null
    upload.reset()
    setClientError(null)
    if (selected && !selected.name.toLowerCase().endsWith(".csv")) {
      setClientError("Please choose a .csv file.")
      setFile(null)
    } else if (selected && selected.size > MAX_BYTES) {
      setClientError("File is larger than 10 MB.")
      setFile(null)
    } else {
      setFile(selected)
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!file) return
    upload.mutate(
      { entity, file },
      {
        onSuccess: (batch) => {
          onImported(batch)
          setFile(null)
          if (fileInput.current) fileInput.current.value = ""
        },
      },
    )
  }

  const error = upload.error
  const duplicateOf =
    error instanceof ApiError && error.status === 409
      ? (error.body as { previous_batch_id?: number } | null)?.previous_batch_id
      : undefined

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import CSV</CardTitle>
        <CardDescription>
          Valid rows are saved; invalid rows are rejected with reasons. Existing records are never
          overwritten, and the same file can&apos;t be imported twice.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4">
          <div className="grid gap-2">
            <Label htmlFor="import-entity">Data type</Label>
            <Select
              items={ENTITIES}
              value={entity}
              onValueChange={(value) => {
                if (value) setEntity(value as ImportEntity)
                upload.reset()
              }}
            >
              <SelectTrigger id="import-entity" className="w-52">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ENTITIES.map((e) => (
                  <SelectItem key={e.value} value={e.value}>
                    {e.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="import-file">CSV file</Label>
            <Input
              ref={fileInput}
              id="import-file"
              type="file"
              accept=".csv,text/csv"
              onChange={handleFile}
              className="w-72"
              aria-describedby={clientError ? "import-file-error" : undefined}
            />
          </div>
          <Button type="submit" disabled={!file || upload.isPending}>
            <UploadIcon />
            {upload.isPending ? "Importing…" : "Import"}
          </Button>
        </form>

        <div className="mt-4 space-y-3" aria-live="polite">
          {clientError && (
            <p id="import-file-error" role="alert" className="text-sm text-destructive">
              {clientError}
            </p>
          )}
          {upload.isPending && file && (
            <p className="text-sm text-muted-foreground">
              Validating {file.name} ({(file.size / 1024).toFixed(0)} KB)…
            </p>
          )}
          {error && duplicateOf !== undefined && (
            <ErrorState
              title="Already imported"
              error={error}
              actionLabel="View previous import"
              onRetry={() => onShowBatch(duplicateOf)}
            />
          )}
          {error && duplicateOf === undefined && <ErrorState title="Import failed" error={error} />}
        </div>
      </CardContent>
    </Card>
  )
}
