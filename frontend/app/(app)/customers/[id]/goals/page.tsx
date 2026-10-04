"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { PlusIcon } from "lucide-react"
import { GoalsSummary } from "@/components/dashboard/goalsSummary"
import { GoalFormDialog } from "@/components/goals/goalFormDialog"
import { ErrorState, LoadingRows } from "@/components/states"
import { Button } from "@/components/ui/button"
import { useGoals } from "@/lib/queries"
import type { Goal } from "@/lib/types"

export default function CustomerGoalsPage() {
  const { id } = useParams<{ id: string }>()
  const goals = useGoals(id)
  const [dialog, setDialog] = useState<{ open: boolean; goal: Goal | null; key: number }>({ open: false, goal: null, key: 0 })

  // A fresh key per opening resets the form to the chosen goal (or blank).
  const openDialog = (goal: Goal | null) => setDialog((d) => ({ open: true, goal, key: d.key + 1 }))
  const newGoalButton = (
    <Button size="sm" onClick={() => openDialog(null)}>
      <PlusIcon />
      New goal
    </Button>
  )

  return (
    <div className="max-w-3xl space-y-4">
      {goals.isPending ? (
        <LoadingRows rows={5} />
      ) : goals.isError ? (
        <ErrorState error={goals.error} onRetry={goals.refetch} />
      ) : (
        <GoalsSummary goals={goals.data} action={newGoalButton} onEdit={openDialog} />
      )}
      <GoalFormDialog
        key={dialog.key}
        customerId={id}
        goal={dialog.goal}
        open={dialog.open}
        onOpenChange={(open) => setDialog((d) => ({ ...d, open }))}
      />
    </div>
  )
}
