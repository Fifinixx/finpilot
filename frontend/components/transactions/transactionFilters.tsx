"use client"

import { useEffect, useState } from "react"
import { XIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useDebounced } from "@/lib/useDebounced"

export type TxnFilterState = {
  date_from: string
  date_to: string
  account: string
  instrument: string
  type: string
  status: string
  ordering: string
}

export const EMPTY_FILTERS: TxnFilterState = {
  date_from: "", date_to: "", account: "", instrument: "", type: "", status: "", ordering: "-trade_date",
}

const TYPES = [
  { value: "", label: "All types" },
  { value: "BUY", label: "Buy" },
  { value: "SELL", label: "Sell" },
  { value: "DIVIDEND", label: "Dividend" },
  { value: "FEE", label: "Fee" },
]
const STATUSES = [
  { value: "", label: "All statuses" },
  { value: "SETTLED", label: "Settled" },
  { value: "PENDING", label: "Pending" },
  { value: "REVERSED", label: "Reversed" },
]
const ORDERINGS = [
  { value: "-trade_date", label: "Newest first" },
  { value: "trade_date", label: "Oldest first" },
  { value: "-amount", label: "Largest amount" },
  { value: "amount", label: "Smallest amount" },
]

export function TransactionFilters({ value, accounts, onChange, dateError }: {
  value: TxnFilterState
  accounts: { value: string; label: string }[]
  onChange: (next: Partial<TxnFilterState>) => void
  dateError: string | null
}) {
  // The instrument box is typed into, so debounce it before it hits the URL/API.
  const [instrument, setInstrument] = useState(value.instrument)
  const debouncedInstrument = useDebounced(instrument.trim())
  useEffect(() => {
    if (debouncedInstrument !== value.instrument) onChange({ instrument: debouncedInstrument })
  }, [debouncedInstrument]) // eslint-disable-line react-hooks/exhaustive-deps

  const accountOptions = [{ value: "", label: "All accounts" }, ...accounts]
  const isFiltered = Object.entries(value).some(([k, v]) => v !== EMPTY_FILTERS[k as keyof TxnFilterState])

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="grid gap-2">
        <Label htmlFor="txn-from">From</Label>
        <Input id="txn-from" type="date" value={value.date_from} onChange={(e) => onChange({ date_from: e.target.value })}
          className="w-40" aria-invalid={!!dateError} aria-describedby={dateError ? "txn-date-error" : undefined} />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="txn-to">To</Label>
        <Input id="txn-to" type="date" value={value.date_to} onChange={(e) => onChange({ date_to: e.target.value })}
          className="w-40" aria-invalid={!!dateError} aria-describedby={dateError ? "txn-date-error" : undefined} />
      </div>
      <FilterSelect id="txn-account" label="Account" options={accountOptions} value={value.account} onChange={(v) => onChange({ account: v })} />
      <div className="grid gap-2">
        <Label htmlFor="txn-instrument">Instrument</Label>
        <Input id="txn-instrument" placeholder="Symbol or ID, e.g. EQ014" value={instrument}
          onChange={(e) => setInstrument(e.target.value)} className="w-48" />
      </div>
      <FilterSelect id="txn-type" label="Type" options={TYPES} value={value.type} onChange={(v) => onChange({ type: v })} />
      <FilterSelect id="txn-status" label="Status" options={STATUSES} value={value.status} onChange={(v) => onChange({ status: v })} />
      <FilterSelect id="txn-ordering" label="Sort" options={ORDERINGS} value={value.ordering} onChange={(v) => onChange({ ordering: v || "-trade_date" })} />
      {isFiltered && (
        <Button variant="ghost" size="sm" onClick={() => { setInstrument(""); onChange(EMPTY_FILTERS) }}>
          <XIcon />
          Clear filters
        </Button>
      )}
      {dateError && (
        <p id="txn-date-error" role="alert" className="w-full text-sm text-destructive">{dateError}</p>
      )}
    </div>
  )
}

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
        <SelectTrigger id={id} className="w-40">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
