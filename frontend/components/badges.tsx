import { CheckCircle2Icon, ClockIcon, SearchIcon, Undo2Icon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import type { KycStatus, TransactionStatus } from "@/lib/types"

// Status is always icon + label, never colour alone.

export function KycBadge({ status }: { status: KycStatus }) {
  if (status === "VERIFIED")
    return <Badge variant="secondary"><CheckCircle2Icon />KYC verified</Badge>
  if (status === "PENDING")
    return <Badge variant="outline"><ClockIcon />KYC pending</Badge>
  return <Badge variant="destructive"><SearchIcon />KYC in review</Badge>
}

export function TransactionStatusBadge({ status }: { status: TransactionStatus }) {
  if (status === "PENDING") return <Badge variant="outline"><ClockIcon />Pending</Badge>
  if (status === "REVERSED") return <Badge variant="destructive"><Undo2Icon />Reversed</Badge>
  return <Badge variant="secondary">Settled</Badge>
}
