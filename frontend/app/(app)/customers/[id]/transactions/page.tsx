"use client"

import { Suspense, useEffect, useRef } from "react"
import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation"
import { EMPTY_FILTERS, TransactionFilters, type TxnFilterState } from "@/components/transactions/transactionFilters"
import { TransactionsTable } from "@/components/transactions/transactionsTable"
import { EmptyState, ErrorState, LoadingRows, Pagination } from "@/components/states"
import { Card, CardContent } from "@/components/ui/card"
import { humanize } from "@/lib/format"
import { usePortfolio, useTransactions } from "@/lib/queries"

export default function CustomerTransactionsPage() {
  // useSearchParams needs a Suspense boundary (see Next docs: use-search-params).
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <TransactionsView />
    </Suspense>
  )
}

function TransactionsView() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // Filters live in the URL, so a filtered view can be bookmarked or shared.
  const filters: TxnFilterState = {
    ...EMPTY_FILTERS,
    ...Object.fromEntries(Object.keys(EMPTY_FILTERS).flatMap((k) => {
      const v = searchParams.get(k)
      return v ? [[k, v]] : []
    })),
  }
  const page = Number(searchParams.get("page")) || 1

  // router.replace updates the URL asynchronously, so two quick changes (e.g.
  // From then To) would both start from the same stale query and the first
  // would be lost. Track the latest intended query synchronously instead.
  const latestQuery = useRef(searchParams.toString())
  useEffect(() => {
    latestQuery.current = searchParams.toString()
  }, [searchParams])

  function update(next: Partial<TxnFilterState> & { page?: number }) {
    const params = new URLSearchParams(latestQuery.current)
    for (const [key, value] of Object.entries(next)) {
      if (value === "" || value === undefined || value === EMPTY_FILTERS[key as keyof TxnFilterState]) params.delete(key)
      else params.set(key, String(value))
    }
    if (!("page" in next)) params.delete("page") // any filter change goes back to page 1
    const qs = params.toString()
    latestQuery.current = qs
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const dateError =
    filters.date_from && filters.date_to && filters.date_from > filters.date_to
      ? "The 'From' date must be on or before the 'To' date."
      : null

  // Don't send an invalid range to the API; the inline message explains why.
  const query = dateError ? { ...filters, date_from: "", date_to: "" } : filters
  const { data, isPending, isError, error, refetch, isFetching } = useTransactions(id, { ...query, page, page_size: 25 })
  const accounts = (usePortfolio(id).data?.accounts ?? []).map((a) => ({
    value: a.account_id,
    label: `${a.account_id} · ${humanize(a.account_type)}`,
  }))

  return (
    <div className="space-y-4">
      <TransactionFilters value={filters} accounts={accounts} onChange={update} dateError={dateError} />
      <Card>
        <CardContent>
          {isPending ? (
            <LoadingRows rows={10} />
          ) : isError ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : data.count === 0 ? (
            <EmptyState title="No transactions match" description="Try widening the date range or clearing filters." />
          ) : (
            <div className={isFetching ? "opacity-60 transition-opacity" : "transition-opacity"} aria-busy={isFetching}>
              <TransactionsTable transactions={data.results} />
              <Pagination page={data.page} totalPages={data.total_pages} count={data.count} label="transactions"
                onPageChange={(p) => update({ page: p })} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
