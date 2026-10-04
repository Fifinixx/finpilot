"use client"

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch, withQuery } from "@/lib/api"
import type {
  CustomerDetail, CustomerListItem, GoalList, ImportBatch, ImportBatchDetail, ImportEntity,
  Paginated, Portfolio, Transaction,
} from "@/lib/types"

export type CustomerFilters = { q?: string; kyc_status?: string; segment?: string; page?: number }

export function useCustomers(filters: CustomerFilters) {
  return useQuery({
    queryKey: ["customers", filters],
    queryFn: () => apiFetch<Paginated<CustomerListItem>>(withQuery("/customers", { ...filters, page_size: 20 })),
    placeholderData: keepPreviousData, // keep the table on screen while the next page loads
  })
}

export function useCustomer(id: string) {
  return useQuery({ queryKey: ["customer", id], queryFn: () => apiFetch<CustomerDetail>(`/customers/${id}`) })
}

export function usePortfolio(id: string) {
  return useQuery({ queryKey: ["portfolio", id], queryFn: () => apiFetch<Portfolio>(`/customers/${id}/portfolio`) })
}

export function useGoals(id: string) {
  return useQuery({ queryKey: ["goals", id], queryFn: () => apiFetch<GoalList>(`/customers/${id}/goals`) })
}

export type TransactionFilters = {
  page?: number
  page_size?: number
  date_from?: string
  date_to?: string
  account?: string
  instrument?: string
  type?: string
  status?: string
}

export function useTransactions(id: string, filters: TransactionFilters) {
  return useQuery({
    queryKey: ["transactions", id, filters],
    queryFn: () => apiFetch<Paginated<Transaction>>(withQuery(`/customers/${id}/transactions`, filters)),
    placeholderData: keepPreviousData,
  })
}

export function useImportBatches(page: number) {
  return useQuery({
    queryKey: ["imports", "list", page],
    queryFn: () => apiFetch<Paginated<ImportBatch>>(withQuery("/admin/imports", { page, page_size: 10 })),
    placeholderData: keepPreviousData,
  })
}

export function useImportBatch(id: number | null) {
  return useQuery({
    queryKey: ["imports", "detail", id],
    queryFn: () => apiFetch<ImportBatchDetail>(`/admin/imports/batches/${id}`),
    enabled: id !== null,
  })
}

export function useUploadImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ entity, file }: { entity: ImportEntity; file: File }) => {
      const body = new FormData()
      body.append("file", file)
      return apiFetch<ImportBatchDetail>(`/admin/imports/${entity}`, { method: "POST", body })
    },
    // New data affects every read view, so drop cached customer data too.
    onSettled: () => queryClient.invalidateQueries(),
  })
}
