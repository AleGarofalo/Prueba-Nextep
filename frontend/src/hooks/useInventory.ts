import { useEffect, useRef, useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { getBookById, getBooks, getDisplayRate, getSummary } from '../api/apiClient'
import type { ApiError } from '../api/apiClient'
import type { BookFilters } from '../types'

export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export const useBooks = (filters: BookFilters) => useQuery({
  queryKey: ['books', 'list', filters], queryFn: ({ signal }) => getBooks(filters, signal),
  placeholderData: keepPreviousData,
})
export const useSummary = () => useQuery({
  queryKey: ['books', 'summary'], queryFn: ({ signal }) => getSummary(signal), refetchInterval: 30_000,
})
export const useDisplayRate = (currency: string, enabled: boolean) => useQuery({
  queryKey: ['display-rate', currency], queryFn: ({ signal }) => getDisplayRate(currency, signal),
  enabled, staleTime: 60_000,
})
export const useBook = (id: number) => useQuery({
  queryKey: ['books', 'detail', id], queryFn: ({ signal }) => getBookById(id, signal), staleTime: 0,
})

export function useReportError(error: Error | null, report: (error: ApiError) => void) {
  const reported = useRef<Error | null>(null)
  useEffect(() => {
    if (error && error !== reported.current) {
      reported.current = error
      report(error as ApiError)
    }
  }, [error, report])
}
