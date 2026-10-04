"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ApiError, type FieldErrors } from "@/lib/api"
import { useSaveGoal, type GoalInput } from "@/lib/queries"
import type { Goal } from "@/lib/types"

const GOAL_TYPES = [
  { value: "RETIREMENT", label: "Retirement" },
  { value: "EDUCATION", label: "Education" },
  { value: "HOME_PURCHASE", label: "Home purchase" },
  { value: "EMERGENCY_FUND", label: "Emergency fund" },
  { value: "WEALTH_CREATION", label: "Wealth creation" },
  { value: "TRAVEL", label: "Travel" },
]
const PRIORITIES = [
  { value: "LOW", label: "Low" },
  { value: "MEDIUM", label: "Medium" },
  { value: "HIGH", label: "High" },
]

const EMPTY: GoalInput = {
  goal_type: "RETIREMENT", name: "", target_amount: "", current_funded_amount: "0", target_date: "", priority: "MEDIUM",
}

function toInput(goal: Goal): GoalInput {
  return {
    goal_type: goal.goal_type,
    name: goal.name,
    target_amount: goal.target_amount,
    current_funded_amount: goal.current_funded_amount,
    target_date: goal.target_date,
    priority: goal.priority,
  }
}

/** Client-side checks mirror the API's rules for instant feedback; the API stays the authority. */
function validate(v: GoalInput, original: GoalInput | null): FieldErrors {
  const errors: FieldErrors = {}
  const today = new Date().toISOString().slice(0, 10)
  if (!v.name.trim()) errors.name = ["Name is required."]
  if (!(Number(v.target_amount) > 0)) errors.target_amount = ["Target amount must be greater than 0."]
  if (v.current_funded_amount === "" || Number(v.current_funded_amount) < 0)
    errors.current_funded_amount = ["Funded amount can't be negative."]
  if (!v.target_date) errors.target_date = ["Target date is required."]
  else if (v.target_date !== original?.target_date && v.target_date <= today)
    errors.target_date = ["Target date must be in the future."]
  return errors
}

export function GoalFormDialog({ customerId, goal, open, onOpenChange }: {
  customerId: string
  goal: Goal | null // null = create
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  // Parent remounts this component (via key) for each goal, so initial state is enough.
  const original = goal ? toInput(goal) : null
  const [values, setValues] = useState<GoalInput>(original ?? EMPTY)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const save = useSaveGoal(customerId)

  const set = (field: keyof GoalInput) => (value: string) => setValues((v) => ({ ...v, [field]: value }))

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setFormError(null)
    const clientErrors = validate(values, original)
    setErrors(clientErrors)
    if (Object.keys(clientErrors).length) return

    const data = original
      ? Object.fromEntries(Object.entries(values).filter(([k, v]) => v !== original[k as keyof GoalInput]))
      : { ...values, name: values.name.trim() }
    if (original && Object.keys(data).length === 0) {
      onOpenChange(false)
      return
    }

    save.mutate(
      { goalId: goal?.id, data },
      {
        onSuccess: () => onOpenChange(false),
        onError: (err) => {
          if (err instanceof ApiError && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors)
          else setFormError(err instanceof ApiError ? err.message : "Couldn't save the goal.")
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{goal ? `Edit goal ${goal.id}` : "New goal"}</DialogTitle>
          <DialogDescription>
            {goal ? "Only the fields you change are saved." : "Funded percentage is calculated automatically."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} noValidate className="grid gap-4">
          <Field id="goal-name" label="Name" errors={errors.name}>
            <Input id="goal-name" value={values.name} onChange={(e) => set("name")(e.target.value)} maxLength={120}
              aria-invalid={!!errors.name} aria-describedby={errors.name ? "goal-name-error" : undefined} />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field id="goal-type" label="Type" errors={errors.goal_type}>
              <ChoiceSelect id="goal-type" options={GOAL_TYPES} value={values.goal_type} onChange={set("goal_type")} />
            </Field>
            <Field id="goal-priority" label="Priority" errors={errors.priority}>
              <ChoiceSelect id="goal-priority" options={PRIORITIES} value={values.priority} onChange={set("priority")} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field id="goal-target" label="Target amount (₹)" errors={errors.target_amount}>
              <Input id="goal-target" type="number" inputMode="decimal" min="0.01" step="0.01" value={values.target_amount}
                onChange={(e) => set("target_amount")(e.target.value)}
                aria-invalid={!!errors.target_amount} aria-describedby={errors.target_amount ? "goal-target-error" : undefined} />
            </Field>
            <Field id="goal-funded" label="Funded so far (₹)" errors={errors.current_funded_amount}>
              <Input id="goal-funded" type="number" inputMode="decimal" min="0" step="0.01" value={values.current_funded_amount}
                onChange={(e) => set("current_funded_amount")(e.target.value)}
                aria-invalid={!!errors.current_funded_amount} aria-describedby={errors.current_funded_amount ? "goal-funded-error" : undefined} />
            </Field>
          </div>
          <Field id="goal-date" label="Target date" errors={errors.target_date}>
            <Input id="goal-date" type="date" value={values.target_date} onChange={(e) => set("target_date")(e.target.value)}
              aria-invalid={!!errors.target_date} aria-describedby={errors.target_date ? "goal-date-error" : undefined} />
          </Field>
          {formError && <p role="alert" className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : goal ? "Save changes" : "Create goal"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function Field({ id, label, errors, children }: { id: string; label: string; errors?: string[]; children: React.ReactNode }) {
  return (
    <div className="grid content-start gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {errors?.length ? (
        <p id={`${id}-error`} className="text-sm text-destructive">{errors.join(" ")}</p>
      ) : null}
    </div>
  )
}

function ChoiceSelect({ id, options, value, onChange }: {
  id: string
  options: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <Select items={options} value={value} onValueChange={(v) => v && onChange(v as string)}>
      <SelectTrigger id={id} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
