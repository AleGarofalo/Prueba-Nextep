import { BookOpen, Pencil, Zap } from 'lucide-react'
import type { ApiError } from '../../api/apiClient'
import { useBook, useReportError } from '../../hooks/useInventory'
import type { Book } from '../../types'
import { countryName, money, utcDate } from '../../lib/format'
import { Dialog } from '../ui/Dialog'
import { Button } from '../ui/Button'
import { CountryFlag } from '../ui/CountryFlag'
import { Badge, StockBadge } from '../ui/Badge'
import { ErrorBanner } from '../ui/ErrorBanner'
import { ISBNLabel } from '../books/BookTable'
import { ModalSkeleton } from './BookFormModal'
import s from './modals.module.css'
import ui from '../../styles/ui.module.css'

export function BookDetailModal({ book, localCurrency, onClose, onEdit, onCalculate, onError }: { book: Book; localCurrency: string; onClose: () => void; onEdit: (book: Book) => void; onCalculate: (book: Book) => void; onError: (error: ApiError) => void }) {
  const query = useBook(book.id)
  useReportError(query.error, onError)
  const data = query.data
  return <Dialog title="Book details" subtitle={`Inventory / Book #${book.id}`} onClose={onClose} footer={<><Button disabled={!data} onClick={() => data && onEdit(data)}><Pencil size={15} aria-hidden="true" />Edit book</Button><Button variant="primary" disabled={!data} onClick={() => data && onCalculate(data)}><Zap size={15} aria-hidden="true" />Calculate price</Button></>}>
    {query.error ? <ErrorBanner error={query.error} onRetry={() => void query.refetch()} /> : !data ? <ModalSkeleton label="Loading book details…" /> : <>
      <div className={s.detailHero}><span className={s.bookSymbol}><BookOpen size={26} aria-hidden="true" /></span><div><h3>{data.title}</h3><p>by {data.author}</p><Badge>{data.category || 'Uncategorized'}</Badge></div></div>
      <dl className={s.detailGrid}>
        <div><dt>ISBN</dt><dd><ISBNLabel isbn={data.isbn} /></dd></div>
        <div><dt>Supplier origin</dt><dd><CountryFlag code={data.supplier_country} /> {countryName(data.supplier_country)} {data.supplier_country && `(${data.supplier_country})`}</dd></div>
        <div><dt>Current stock</dt><dd><StockBadge quantity={data.stock_quantity} /></dd></div>
        <div><dt>Import cost · USD</dt><dd className={ui.mono}>{money(data.cost_usd)}</dd></div>
        <div><dt>Suggested selling price · {localCurrency}</dt><dd className={ui.mono}>{data.selling_price_local === null ? <span className={ui.muted}>Not calculated</span> : money(data.selling_price_local, localCurrency)}</dd></div>
      </dl><div className={s.detailFooter}><span>Created {utcDate(data.created_at)}</span><span>Updated {utcDate(data.updated_at)}</span></div>
    </>}
  </Dialog>
}
