import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { BookOpen, Check, CircleAlert, Clock, Info, RotateCcw, X } from 'lucide-react'
import { ApiError } from './api/apiClient'
import { readPreference, savePreference, SUGGESTED_CATEGORIES } from './lib/format'
import { useBooks, useDebouncedValue, useDisplayRate, useReportError, useSummary } from './hooks/useInventory'
import type { ApiHealth, Book, ModalState, ViewMode } from './types'
import { Header } from './components/layout/Header'
import { KpiCards } from './components/dashboard/KpiCards'
import { FilterToolbar, ViewModeControl } from './components/dashboard/FilterToolbar'
import { BookTable } from './components/books/BookTable'
import { BookCardGrid } from './components/books/BookCardGrid'
import { Pagination } from './components/books/Pagination'
import { EmptyInventory, InventorySkeleton } from './components/books/InventoryState'
import { BookFormModal } from './components/modals/BookFormModal'
import { BookDetailModal } from './components/modals/BookDetailModal'
import { ConfirmDeleteModal } from './components/modals/ConfirmDeleteModal'
import { PriceBreakdownModal } from './components/modals/PriceBreakdownModal'
import { Button } from './components/ui/Button'
import { ErrorBanner } from './components/ui/ErrorBanner'
import { useToast } from './components/ui/ToastContainer'
import s from './App.module.css'
import ui from './styles/ui.module.css'

function App() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [lowStock, setLowStock] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [ordering, setOrdering] = useState<'id' | '-id'>('-id')
  const [mode, setMode] = useState<ViewMode>(() => readPreference('bookstore-view') === 'cards' ? 'cards' : 'table')
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || 'light')
  const [currencyPreference, setCurrencyPreference] = useState(() => readPreference('bookstore-currency'))
  const [health, setHealth] = useState<ApiHealth>('checking')
  const [modal, setModal] = useState<ModalState>(null)
  const [systemError, setSystemError] = useState<ApiError | null>(null)
  const client = useQueryClient()
  const notify = useToast()
  const debouncedSearch = useDebouncedValue(search)
  const filters = useMemo(() => ({ page, page_size: pageSize, search: debouncedSearch, category, low_stock: lowStock, ordering }), [page, pageSize, debouncedSearch, category, lowStock, ordering])
  const books = useBooks(filters)
  const summary = useSummary()
  const localCurrency = summary.data?.local_currency || 'EUR'
  const currency = currencyPreference || localCurrency
  const displayRate = useDisplayRate(currency, !!summary.data)
  const filtered = !!(search.trim() || category || lowStock)
  const categories = useMemo(() => [...new Set([...SUGGESTED_CATEGORIES, ...(summary.data?.categories || [])])].sort((a, b) => a.localeCompare(b)), [summary.data?.categories])
  const refresh = useCallback(() => {
    setSystemError(null)
    void client.invalidateQueries({ queryKey: ['books'] })
    void client.invalidateQueries({ queryKey: ['display-rate'] })
  }, [client])
  const closeModal = useCallback(() => setModal(null), [])
  const reportError = useCallback((error: ApiError) => {
    notify(error.message, [400, 404, 503].includes(error.status) ? 'warning' : 'error')
    if (error.status === 404) { setModal(null); void client.invalidateQueries({ queryKey: ['books'] }) }
    if (error.status === 0 || (error.status >= 500 && error.status !== 503)) setSystemError(error)
  }, [client, notify])
  useReportError(displayRate.error, reportError)
  useEffect(() => {
    const handle = (event: Event) => setHealth((event as CustomEvent<ApiHealth>).detail)
    window.addEventListener('inventory:api-health', handle)
    return () => window.removeEventListener('inventory:api-health', handle)
  }, [])
  useEffect(() => { document.documentElement.dataset.theme = theme; savePreference('bookstore-theme', theme) }, [theme])
  useEffect(() => {
    if (books.error instanceof ApiError && books.error.status === 404 && page > 1) setPage((value) => Math.max(1, value - 1))
  }, [books.error, page])
  function resetFilters() { setSearch(''); setCategory(''); setLowStock(false); setPage(1) }
  function changeCurrency(value: string) { setCurrencyPreference(value); savePreference('bookstore-currency', value) }
  function changeCategory(value: string) { setCategory(value); setPage(1) }
  function toggleLowStock() { setLowStock((value) => !value); setPage(1) }
  const actions = {
    onDetail: (book: Book) => setModal({ kind: 'detail', book }),
    onEdit: (book: Book) => setModal({ kind: 'edit', book }),
    onDelete: (book: Book) => setModal({ kind: 'delete', book }),
    onCalculate: (book: Book) => setModal({ kind: 'price', book }),
  }
  const dataError = books.error || summary.error || systemError
  const reportedHealth = dataError instanceof ApiError ? dataError.status === 0 ? 'offline' : 'degraded' : health
  const refreshing = books.isFetching || summary.isFetching
  const priceView = { currency, localCurrency, rate: displayRate.data, rateError: !!displayRate.error }
  const loading = books.isPending || (books.isPlaceholderData && !books.data.results.length)
  const count = books.data?.count || 0
  return <>
    <Header health={reportedHealth} currency={currency} localCurrency={localCurrency} onCurrencyChange={changeCurrency} theme={theme} onToggleTheme={() => setTheme((value) => value === 'dark' ? 'light' : 'dark')} onRefresh={refresh} refreshing={refreshing} />
    <main id="main-content" className={s.main}>
      <div className={s.pageHeading}><div><div className={s.eyebrow}><BookOpen size={12} aria-hidden="true" />WORKSPACE / INVENTORY</div><h1>Book inventory<span className={s.headingDot}>.</span></h1><p>Manage your catalog, monitor stock, and calculate selling prices.</p></div><span className={s.synced}><Clock size={12} aria-hidden="true" />{summary.dataUpdatedAt ? `Last synced ${new Intl.DateTimeFormat('en', { hour: 'numeric', minute: '2-digit' }).format(summary.dataUpdatedAt)}` : 'Connecting to inventory…'}</span></div>
      {dataError && <ErrorBanner error={dataError} onRetry={refresh} actionLabel="Refresh inventory" />}
      <KpiCards summary={summary.data} loading={summary.isPending} lowStock={lowStock} onLowStock={toggleLowStock} />
      <section className={s.catalog} aria-label="Book catalog">
        <div className={s.catalogHeader}><div><h2>Book catalog</h2><span className={s.count}>{books.data ? count.toLocaleString() : '—'} {count === 1 ? 'title' : 'titles'}</span>{books.isFetching && <span className={s.updating} role="status">Updating…</span>}</div><ViewModeControl value={mode} onChange={(value) => { setMode(value); savePreference('bookstore-view', value) }} /></div>
        <FilterToolbar search={search} onSearch={(value) => { setSearch(value); setPage(1) }} category={category} onCategory={changeCategory} categories={categories} lowStock={lowStock} onLowStock={toggleLowStock} onCreate={() => setModal({ kind: 'create' })} />
        {filtered && <div className={s.activeFilters}><span>Filtered by</span>{search.trim() && <span className={s.filterTag}>“{search.trim()}”<button aria-label="Remove search filter" type="button" onClick={() => { setSearch(''); setPage(1) }}><X size={11} aria-hidden="true" /></button></span>}{category && <span className={s.filterTag}>{category}<button aria-label="Remove category filter" type="button" onClick={() => changeCategory('')}><X size={11} aria-hidden="true" /></button></span>}{lowStock && <span className={s.filterTag}>Stock ≤10<button aria-label="Remove low-stock filter" type="button" onClick={toggleLowStock}><X size={11} aria-hidden="true" /></button></span>}<button type="button" className={s.clearFilters} onClick={resetFilters}>Clear all</button></div>}
        {currency !== localCurrency && <div className={s.currencyNote}><Info size={13} aria-hidden="true" /><span>Prices shown in {currency}; selling prices are saved in {localCurrency}.{displayRate.data?.is_fallback && ' Display conversion uses a fallback rate.'}</span><a href="https://www.exchangerate-api.com" target="_blank" rel="noreferrer">Rates by ExchangeRate-API</a></div>}
        {displayRate.error && currency !== localCurrency && <div className={s.fxError}><ErrorBanner error={displayRate.error} onRetry={() => void displayRate.refetch()} /><Button small onClick={() => changeCurrency(localCurrency)}>Use {localCurrency}</Button></div>}
        {loading ? <InventorySkeleton /> : books.error ? <div className={s.loadError}><CircleAlert size={30} aria-hidden="true" /><h3>Inventory could not be loaded</h3><p>Your data will appear when the connection is restored.</p><Button onClick={refresh}><RotateCcw size={15} aria-hidden="true" />Try again</Button></div> : !books.data?.results.length ? <EmptyInventory filtered={filtered} onReset={resetFilters} onCreate={() => setModal({ kind: 'create' })} /> : mode === 'table' ? <BookTable books={books.data.results} ordering={ordering} onSort={() => { setOrdering((value) => value === 'id' ? '-id' : 'id'); setPage(1) }} onCategory={changeCategory} busy={books.isPlaceholderData} priceView={priceView} {...actions} /> : <BookCardGrid books={books.data.results} onCategory={changeCategory} busy={books.isPlaceholderData} priceView={priceView} {...actions} />}
        {books.data && !books.error && <Pagination count={count} page={page} pageSize={pageSize} onPage={setPage} onPageSize={(value) => { setPageSize(value); setPage(1) }} disabled={books.isPlaceholderData} />}
      </section>
      <footer className={s.pageFooter}><span>{dataError ? <CircleAlert size={12} aria-hidden="true" /> : <Check size={12} aria-hidden="true" />}{dataError ? 'Inventory connection needs attention' : refreshing ? 'Syncing inventory…' : 'Your inventory is synced with the database'}</span><span>nextep.bookstore <span className={s.footerDot}>·</span> Built for better shelves</span></footer>
    </main>
    {(modal?.kind === 'create' || modal?.kind === 'edit') && <BookFormModal key={modal.kind === 'edit' ? modal.book.id : 'new'} book={modal.kind === 'edit' ? modal.book : undefined} categories={categories} onClose={closeModal} onError={reportError} onSaved={(_book, created) => { setSystemError(null); if (created) { resetFilters(); setOrdering('-id') } closeModal() }} />}
    {modal?.kind === 'detail' && <BookDetailModal key={modal.book.id} book={modal.book} localCurrency={localCurrency} onClose={closeModal} onEdit={actions.onEdit} onCalculate={actions.onCalculate} onError={reportError} />}
    {modal?.kind === 'price' && <PriceBreakdownModal key={modal.book.id} book={modal.book} localCurrency={localCurrency} onClose={closeModal} onError={reportError} />}
    {modal?.kind === 'delete' && <ConfirmDeleteModal book={modal.book} onClose={closeModal} onError={reportError} onDeleted={() => { setSystemError(null); if (page > 1 && books.data?.results.length === 1) setPage((value) => value - 1); closeModal() }} />}
    <span className={ui.srOnly} aria-live="polite">{!books.isFetching && books.data ? `${count} books found. Page ${page}.` : ''}</span>
  </>
}

export default App
