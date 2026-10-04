"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { ArrowLeftIcon } from "lucide-react"
import { AccountCards } from "@/components/dashboard/accountCards"
import { AllocationChart } from "@/components/dashboard/allocationChart"
import { CustomerHeader } from "@/components/dashboard/customerHeader"
import { GoalsSummary } from "@/components/dashboard/goalsSummary"
import { PortfolioSummary } from "@/components/dashboard/portfolioSummary"
import { PositionsTable } from "@/components/dashboard/positionsTable"
import { RecentTransactions } from "@/components/dashboard/recentTransactions"
import { RiskSummary } from "@/components/dashboard/riskSummary"
import { EmptyState, ErrorState, LoadingRows } from "@/components/states"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ApiError } from "@/lib/api"
import { useCustomer, useGoals, usePortfolio } from "@/lib/queries"

export default function CustomerDashboardPage() {
  const { id } = useParams<{ id: string }>()
  const customer = useCustomer(id)
  const portfolio = usePortfolio(id)
  const goals = useGoals(id)

  if (customer.error instanceof ApiError && customer.error.status === 404) {
    return (
      <div className="space-y-4">
        <BackLink />
        <EmptyState title={`Customer ${id} not found`} description="Check the ID or search again." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <BackLink />

      {/* Each section loads and fails independently, so one slow query never blanks the page. */}
      {customer.isPending ? (
        <Skeleton className="h-14 w-96" />
      ) : customer.isError ? (
        <ErrorState error={customer.error} onRetry={customer.refetch} />
      ) : (
        <CustomerHeader customer={customer.data} />
      )}

      {portfolio.isPending ? (
        <Skeleton className="h-36 w-full" />
      ) : portfolio.isError ? (
        <ErrorState error={portfolio.error} onRetry={portfolio.refetch} />
      ) : (
        <PortfolioSummary portfolio={portfolio.data} />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Asset allocation</CardTitle>
          </CardHeader>
          <CardContent>
            {portfolio.isPending ? (
              <LoadingRows rows={4} />
            ) : portfolio.isError ? null : portfolio.data.allocation.length === 0 ? (
              <EmptyState title="Nothing to allocate" description="This customer has no positions in the latest snapshot." />
            ) : (
              <AllocationChart allocation={portfolio.data.allocation} />
            )}
          </CardContent>
        </Card>
        {customer.isPending ? (
          <Skeleton className="h-64 w-full" />
        ) : customer.isError ? null : (
          <RiskSummary risk={customer.data.latest_risk_profile} />
        )}
      </div>

      <section aria-labelledby="accounts-heading" className="space-y-3">
        <h2 id="accounts-heading" className="text-lg font-semibold">Accounts</h2>
        {portfolio.isPending ? <LoadingRows rows={2} /> : portfolio.isError ? null : <AccountCards accounts={portfolio.data.accounts} />}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {goals.isPending ? (
          <LoadingRows rows={4} />
        ) : goals.isError ? (
          <ErrorState error={goals.error} onRetry={goals.refetch} />
        ) : (
          <GoalsSummary goals={goals.data} />
        )}
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentTransactions customerId={id} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          {portfolio.isPending ? <LoadingRows rows={6} /> : portfolio.isError ? null : <PositionsTable positions={portfolio.data.positions} />}
        </CardContent>
      </Card>
    </div>
  )
}

function BackLink() {
  return (
    <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
      <ArrowLeftIcon className="size-4" /> All customers
    </Link>
  )
}
