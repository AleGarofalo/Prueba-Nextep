export interface Book {
  id: number
  title: string
  author: string
  isbn: string
  cost_usd: string
  selling_price_local: string | null
  stock_quantity: number
  category: string | null
  supplier_country: string
  created_at: string
  updated_at: string
}

export interface BookInput {
  title: string
  author: string
  isbn: string
  cost_usd: string
  stock_quantity: number
  category: string
  supplier_country: string
}

export interface BookPage {
  count: number
  next: string | null
  previous: string | null
  results: Book[]
}

export interface BookFilters {
  page: number
  page_size: number
  search: string
  category: string
  low_stock: boolean
  ordering: 'id' | '-id'
}

export interface InventorySummary {
  total_titles: number
  inventory_value_usd: string
  low_stock_titles: number
  out_of_stock_titles: number
  categories: string[]
  local_currency: string
  margin_percentage: number
  last_updated_at: string | null
}

export type RateSource = 'live' | 'cache' | 'stale_cache' | 'default' | 'identity'

export interface DisplayRate {
  currency: string
  local_currency: string
  conversion_rate: string
  rate_source: RateSource
  rates_fetched_at: string | null
  is_fallback: boolean
}

export interface PriceCalculation {
  book_id: number
  cost_usd: string
  cost_local: string
  exchange_rate: string
  margin_percentage: number
  selling_price_local: string
  currency: string
  calculation_timestamp: string
  rates_fetched_at: string | null
  rate_source: RateSource
  is_fallback: boolean
  provider: string
  provider_url: string
}

export type FieldErrors = Record<string, string>
export type ViewMode = 'table' | 'cards'
export type ApiHealth = 'checking' | 'online' | 'offline' | 'degraded'
export type ModalState =
  | { kind: 'create' }
  | { kind: 'edit' | 'detail' | 'price'; book: Book }
  | { kind: 'delete'; book: Book }
  | null
