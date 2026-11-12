import { BookOpen } from 'lucide-react'
import type { Book } from '../../types'
import { countryName, money } from '../../lib/format'
import { Badge, StockBadge } from '../ui/Badge'
import { CountryFlag } from '../ui/CountryFlag'
import { BookActionButtons, ISBNLabel, LocalPrice } from './BookTable'
import type { BookActions, PriceView } from './BookTable'
import s from './books.module.css'

export function BookCardGrid({ books, priceView, busy, onCategory, ...actions }: { books: Book[]; priceView: PriceView; busy: boolean; onCategory: (value: string) => void } & BookActions) {
  return <div className={`${s.grid} ${busy ? s.updating : ''}`} aria-busy={busy}>{books.map((book) => <article key={book.id} className={s.card}>
    <div className={s.cardTop}>{book.category ? <button className={s.categoryButton} type="button" onClick={() => onCategory(book.category!)}><Badge>{book.category}</Badge></button> : <Badge>Uncategorized</Badge>}<StockBadge quantity={book.stock_quantity} /></div>
    <div className={s.cardHeading}><span className={s.cardBook}><BookOpen size={23} strokeWidth={1.5} aria-hidden="true" /></span><div><button type="button" className={s.cardTitle} onClick={() => actions.onDetail(book)}>{book.title}</button><p>by {book.author}</p></div></div>
    <div className={s.cardMetadata}><ISBNLabel isbn={book.isbn} /><span title={countryName(book.supplier_country)}><CountryFlag code={book.supplier_country} /> {book.supplier_country || 'Unknown origin'}</span></div>
    <div className={s.cardPrices}><div><span>Import cost <small>USD</small></span><strong>{money(book.cost_usd)}</strong></div><div><span>Selling price <small>{priceView.currency}</small></span><LocalPrice book={book} {...priceView} /></div></div>
    <div className={s.cardActions}><BookActionButtons book={book} {...actions} disabled={busy} fullPrice /></div>
  </article>)}</div>
}
