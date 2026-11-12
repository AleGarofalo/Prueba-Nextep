import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'
import type {
  ApiHealth, Book, BookFilters, BookInput, BookPage,
  DisplayRate, FieldErrors, InventorySummary, PriceCalculation,
} from '../types'

export class ApiError extends Error {
  status: number
  fields: FieldErrors

  constructor(message: string, status: number, fields: FieldErrors = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
  }
}

function firstMessage(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(firstMessage).filter(Boolean).join(' ')
  return ''
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (!axios.isAxiosError(error)) return new ApiError('Something went wrong. Please try again.', 0)
  const status = error.response?.status ?? 0
  const payload: unknown = error.response?.data
  const fields: FieldErrors = {}
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    for (const [key, value] of Object.entries(payload)) {
      const message = firstMessage(value)
      if (message) fields[key] = message
    }
  }
  const messages: Record<number, string> = {
    0: error.code === 'ECONNABORTED'
      ? 'The request took too long. Please try again.'
      : 'Cannot reach the inventory service. Check your connection and try again.',
    400: fields.isbn || fields.non_field_errors || Object.values(fields)[0] || 'Please check the highlighted fields.',
    404: 'This book or page is no longer available. Your inventory will be refreshed.',
    500: 'The server could not complete this request. Please try again.',
    503: 'The exchange-rate service is unavailable. Please try again shortly.',
  }
  return new ApiError(messages[status] || 'This request could not be completed. Please try again.', status, fields)
}

const http = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, ''),
  timeout: 30_000,
  headers: { Accept: 'application/json' },
})

function health(status: ApiHealth) {
  window.dispatchEvent(new CustomEvent('inventory:api-health', { detail: status }))
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  try {
    const response = await http.request<T>(config)
    health('online')
    return response.data
  } catch (error) {
    if (axios.isCancel(error)) throw error
    const normalized = toApiError(error)
    health(normalized.status === 0 ? 'offline' : normalized.status >= 500 ? 'degraded' : 'online')
    throw normalized
  }
}

export async function getBooks(filters: BookFilters, signal?: AbortSignal): Promise<BookPage> {
  const path = filters.low_stock ? '/books/low-stock' : filters.category ? '/books/search' : '/books'
  const data = await request<BookPage>({
    url: path, signal,
    params: {
      page: filters.page, page_size: filters.page_size, ordering: filters.ordering,
      search: filters.search || undefined, category: filters.category || undefined,
      threshold: filters.low_stock ? 10 : undefined,
    },
  })
  if (!Array.isArray(data.results) || typeof data.count !== 'number') {
    throw new ApiError('The inventory service returned an unexpected response.', 500)
  }
  return data
}

export const getSummary = (signal?: AbortSignal) => request<InventorySummary>({ url: '/books/summary', signal })
export const getBookById = (id: number, signal?: AbortSignal) => request<Book>({ url: `/books/${id}`, signal })
export const createBook = (data: BookInput) => request<Book>({ method: 'POST', url: '/books', data })
export const updateBook = (id: number, data: BookInput) => request<Book>({ method: 'PUT', url: `/books/${id}`, data })
export const deleteBook = (id: number) => request<void>({ method: 'DELETE', url: `/books/${id}` })
export const calculatePrice = (id: number) => request<PriceCalculation>({ method: 'POST', url: `/books/${id}/calculate-price`, data: {} })
export const getDisplayRate = (currency: string, signal?: AbortSignal) => request<DisplayRate>({
  url: '/books/exchange-rate', params: { currency }, signal,
})
