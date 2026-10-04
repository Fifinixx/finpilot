import { KycBadge } from "@/components/badges"
import { Badge } from "@/components/ui/badge"
import { formatDate } from "@/lib/format"
import type { CustomerDetail } from "@/lib/types"

export function CustomerHeader({ customer }: { customer: CustomerDetail }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">{customer.full_name}</h1>
          <span className="font-mono text-sm text-muted-foreground">{customer.id}</span>
        </div>
        <p className="text-sm text-muted-foreground">
          {customer.email} · {customer.phone} · {customer.city}, {customer.state} · Customer since {formatDate(customer.onboarded_at)}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <KycBadge status={customer.kyc_status} />
        <Badge variant="outline">{customer.segment}</Badge>
      </div>
    </div>
  )
}
