"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { SearchIcon } from "lucide-react"
import { KycBadge } from "@/components/badges"
import { EmptyState, ErrorState, LoadingRows, Pagination } from "@/components/states"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useCustomers } from "@/lib/queries"
import { useDebounced } from "@/lib/useDebounced"

const KYC_OPTIONS = [
  { value: "", label: "All KYC statuses" },
  { value: "VERIFIED", label: "Verified" },
  { value: "PENDING", label: "Pending" },
  { value: "REVIEW", label: "In review" },
]
const SEGMENT_OPTIONS = [
  { value: "", label: "All segments" },
  { value: "Mass", label: "Mass" },
  { value: "Affluent", label: "Affluent" },
  { value: "HNI", label: "HNI" },
]

function FilterSelect({ id, label, options, value, onChange }: {
  id: string
  label: string
  options: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select items={options} value={value} onValueChange={(v) => onChange((v as string | null) ?? "")}>
        <SelectTrigger id={id} className="w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export default function CustomersPage() {
  const router = useRouter()
  const [search, setSearch] = useState("")
  const [kyc, setKyc] = useState("")
  const [segment, setSegment] = useState("")
  const [page, setPage] = useState(1)
  const q = useDebounced(search.trim())

  const { data, isPending, isError, error, refetch, isFetching } = useCustomers({
    q, kyc_status: kyc, segment, page,
  })

  // Any filter change starts again from page 1.
  const update = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v)
    setPage(1)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Customers</h1>
        <p className="text-sm text-muted-foreground">Search by customer ID, name, email or city.</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="grid flex-1 gap-2" style={{ minWidth: "16rem" }}>
          <Label htmlFor="customer-search">Search</Label>
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              id="customer-search"
              type="search"
              placeholder="e.g. C0012, Sharma, Pune"
              value={search}
              onChange={(e) => update(setSearch)(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>
        <FilterSelect id="kyc-filter" label="KYC status" options={KYC_OPTIONS} value={kyc} onChange={update(setKyc)} />
        <FilterSelect id="segment-filter" label="Segment" options={SEGMENT_OPTIONS} value={segment} onChange={update(setSegment)} />
      </div>

      {isPending ? (
        <LoadingRows rows={8} />
      ) : isError ? (
        <ErrorState error={error} onRetry={refetch} />
      ) : data.count === 0 ? (
        <EmptyState title="No customers match" description="Try a different search or clear the filters." />
      ) : (
        <div className={isFetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>City</TableHead>
                <TableHead>Segment</TableHead>
                <TableHead>KYC</TableHead>
                <TableHead className="text-right">Accounts</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.results.map((c) => (
                <TableRow
                  key={c.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/customers/${c.id}`)}
                >
                  <TableCell className="font-mono text-xs">{c.id}</TableCell>
                  <TableCell>
                    <Link href={`/customers/${c.id}`} className="font-medium hover:underline" onClick={(e) => e.stopPropagation()}>
                      {c.full_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{c.email}</TableCell>
                  <TableCell>{c.city}, {c.state}</TableCell>
                  <TableCell>{c.segment}</TableCell>
                  <TableCell><KycBadge status={c.kyc_status} /></TableCell>
                  <TableCell className="text-right tabular-nums">{c.account_count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination page={data.page} totalPages={data.total_pages} count={data.count} label="customers" onPageChange={setPage} />
        </div>
      )}
    </div>
  )
}
