"use client"

import { useState } from "react"
import { useAuth } from "@/components/authProvider"
import { ImportHistory } from "@/components/imports/importHistory"
import { ImportResult } from "@/components/imports/importResult"
import { ImportUploader } from "@/components/imports/importUploader"
import { EmptyState, ErrorState, LoadingRows } from "@/components/states"
import { useImportBatch } from "@/lib/queries"
import type { ImportBatchDetail } from "@/lib/types"

export default function ImportsPage() {
  const { user } = useAuth()
  const [justImported, setJustImported] = useState<ImportBatchDetail | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  // A batch picked from history is fetched; a fresh upload already has its detail.
  const selected = useImportBatch(justImported?.id === selectedId ? null : selectedId)

  // The API enforces this too; hiding the page is only a courtesy.
  if (user?.role !== "ADMIN") {
    return <EmptyState title="Administrator access required" description="Ask an admin if you need to import data." />
  }

  const shown = justImported && justImported.id === selectedId ? justImported : selected.data

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Data imports</h1>
      <ImportUploader
        onImported={(batch) => {
          setJustImported(batch)
          setSelectedId(batch.id)
        }}
        onShowBatch={setSelectedId}
      />
      {selectedId !== null &&
        (shown ? (
          <ImportResult batch={shown} />
        ) : selected.isError ? (
          <ErrorState error={selected.error} onRetry={selected.refetch} />
        ) : (
          <LoadingRows rows={3} />
        ))}
      <ImportHistory selectedId={selectedId} onSelect={setSelectedId} />
    </div>
  )
}
