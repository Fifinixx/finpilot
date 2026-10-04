import { AlertCircleIcon, InboxIcon } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api"

export function ErrorState({ error, onRetry, title = "Couldn't load this data", actionLabel = "Try again" }: {
  error: unknown
  onRetry?: () => void
  title?: string
  actionLabel?: string
}) {
  const message = error instanceof ApiError ? error.message : "Something went wrong."
  return (
    <Alert variant="destructive">
      <AlertCircleIcon />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center gap-3">
        <span>{message}</span>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            {actionLabel}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed px-6 py-10 text-center">
      <InboxIcon className="mb-2 size-6 text-muted-foreground" aria-hidden />
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
    </div>
  )
}

export function LoadingRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-9 w-full" />
      ))}
    </div>
  )
}

export function Pagination({ page, totalPages, onPageChange, count, label }: {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
  count: number
  label: string
}) {
  if (count === 0) return null
  return (
    <nav aria-label={`${label} pagination`} className="flex items-center justify-between gap-4 pt-3 text-sm">
      <span className="text-muted-foreground">
        {count.toLocaleString("en-IN")} {label} · page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
        </Button>
      </div>
    </nav>
  )
}
