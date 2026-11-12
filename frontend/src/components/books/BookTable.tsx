import { ArrowDown, ArrowUp, Copy, Pencil, Trash2, Zap } from 'lucide-react'
import type { Book, DisplayRate } from '../../types'
import { countryName, money } from '../../lib/format'
import { Button } from '../ui/Button'
import { CountryFlag } from '../ui/CountryFlag'
import { Badge, StockBadge } from '../ui/Badge'
import { useToast } from '../ui/ToastContainer'
import s from './books.module.css'
import ui from '../../styles/ui.module.css'

export interface BookActions {
  onDetail: (book: Book) => void
  onEdit: (book: Book) => void
  onDelete: (book: Book) => void
  onCalculate: (book: Book) => void
}
export interface PriceView { currency: string; localCurrency: string; rate?: DisplayRate; rateError: boolean }

export function LocalPrice({ book, currency, localCurrency, rate, rateError }: { book: Book } & PriceView) {
  if (book.selling_price_local === null) return <span className={s.notCalculated}>Not calculated</span>
  if (currency !== localCurrency && (!rate || rate.currency !== currency)) {
    return rateError ? <span className={s.notCalculated}>Unavailable</span> : <span className={`${ui.skeleton} ${s.priceSkeleton}`} aria-label="Converting price" />
  }
  const factor = currency === localCurrency ? 1 : Number(rate?.conversion_rate)
  return <span className={s.localPrice}>{money(Number(book.selling_price_local) * factor, currency)}</span>
}

export function BookActionButtons({ book, onDetail: _onDetail, onEdit, onDelete, onCalculate, disabled, fullPrice = false }: { book: Book; disabled?: boolean; fullPrice?: boolean } & BookActions) {
  return <div className={s.actions}>
    <Button variant="ghost" iconOnly={!fullPrice} small={fullPrice} disabled={disabled} className={s.calculate} onClick={() => onCalculate(book)} title="Calculate selling price" aria-label={`Calculate price for ${book.title}`}><Zap size={15} aria-hidden="true" />{fullPrice && 'Calculate price'}</Button>
    <Button variant="ghost" iconOnly disabled={disabled} onClick={() => onEdit(book)} title="Edit book" aria-label={`Edit ${book.title}`}><Pencil size={15} aria-hidden="true" /></Button>
    <Button variant="ghost" iconOnly disabled={disabled} className={s.delete} onClick={() => onDelete(book)} title="Delete book" aria-label={`Delete ${book.title}`}><Trash2 size={15} aria-hidden="true" /></Button>
  </div>
}

export function ISBNLabel({ isbn }: { isbn: string }) {
  const notify = useToast()
  return <span className={s.isbn}><span>{isbn}</span><button type="button" title="Copy ISBN" aria-label={`Copy ISBN ${isbn}`} onClick={() => {
    if (!navigator.clipboard) { notify('Clipboard unavailable. Select the ISBN to copy it.', 'warning'); return }
    void navigator.clipboard.writeText(isbn).then(() => notify('ISBN copied to clipboard.', 'info')).catch(() => notify('Could not copy the ISBN. Please copy it manually.', 'warning'))
  }}><Copy size={12} aria-hidden="true" /></button></span>
}

export function BookTable({ books, ordering, onSort, onCategory, busy, priceView, ...actions }: {
  books: Book[]; ordering: 'id' | '-id'; onSort: () => void; onCategory: (value: string) => void
  busy: boolean; priceView: PriceView
} & BookActions) {
  return <div className={s.tableScroll} tabIndex={0} role="region" aria-label="Book inventory table" aria-busy={busy}>
    <table className={`${s.table} ${busy ? s.updating : ''}`}><caption className={ui.srOnly}>Book inventory with stock levels, import costs, selling prices and actions</caption>
      <colgroup><col style={{ width: '5%' }} /><col style={{ width: '21%' }} /><col style={{ width: '14%' }} /><col style={{ width: '12%' }} /><col style={{ width: '7%' }} /><col style={{ width: '11%' }} /><col style={{ width: '9%' }} /><col style={{ width: '11%' }} /><col style={{ width: '10%' }} /></colgroup>
      <thead><tr><th scope="col" aria-sort={ordering === 'id' ? 'ascending' : 'descending'}><button className={s.sortButton} type="button" onClick={onSort} aria-label={`Sort ID ${ordering === 'id' ? 'descending' : 'ascending'}`}>ID{ordering === 'id' ? <ArrowUp size={11} aria-hidden="true" /> : <ArrowDown size={11} aria-hidden="true" />}</button></th><th scope="col">Title & author</th><th scope="col">ISBN</th><th scope="col">Category</th><th scope="col" className={s.center}>Origin</th><th scope="col">Stock</th><th scope="col" className={s.right}>Cost <small>USD</small></th><th scope="col" className={s.right}>Local price <small>{priceView.currency}</small></th><th scope="col" className={s.center}>Actions</th></tr></thead>
      <tbody>{books.map((book) => <tr key={book.id}><td className={s.id}>#{String(book.id).padStart(3, '0')}</td><td><button type="button" className={s.title} onClick={() => actions.onDetail(book)} title={book.title}>{book.title}</button><span className={s.author}>{book.author}</span></td><td><ISBNLabel isbn={book.isbn} /></td><td>{book.category ? <button type="button" className={s.categoryButton} onClick={() => onCategory(book.category!)} title={`Filter by ${book.category}`}><Badge>{book.category}</Badge></button> : <span className={s.notCalculated}>Uncategorized</span>}</td><td className={s.center}><span className={s.origin} title={countryName(book.supplier_country)}><CountryFlag code={book.supplier_country} />{book.supplier_country || '—'}</span></td><td><StockBadge quantity={book.stock_quantity} /></td><td className={`${s.right} ${s.cost}`}>{money(book.cost_usd)}</td><td className={s.right}><LocalPrice book={book} {...priceView} /></td><td><BookActionButtons book={book} {...actions} disabled={busy} /></td></tr>)}</tbody>
    </table>
  </div>
}
