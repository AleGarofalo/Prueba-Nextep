import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '../ui/Button'
import s from './pagination.module.css'

export function Pagination({ count, page, pageSize, onPage, onPageSize, disabled }: {
  count: number; page: number; pageSize: number; onPage: (page: number) => void
  onPageSize: (size: number) => void; disabled: boolean
}) {
  const total = Math.max(1, Math.ceil(count / pageSize))
  const pages = [...new Set([1, total, page - 1, page, page + 1])].filter((value) => value > 0 && value <= total).sort((a, b) => a - b)
  return <nav className={s.pagination} aria-label="Inventory pagination">
    <p>Showing <strong>{count ? (page - 1) * pageSize + 1 : 0}–{Math.min(page * pageSize, count)}</strong> of <strong>{count.toLocaleString()}</strong> books</p>
    <div className={s.controls}><label className={s.size}><span className={s.sizeLabel}>Results per page</span><select aria-label="Results per page" value={pageSize} onChange={(event) => onPageSize(Number(event.target.value))}>{[10, 25, 50].map((size) => <option value={size} key={size}>{size} per page</option>)}</select></label>
      <div className={s.pages}><Button variant="ghost" small disabled={page <= 1 || disabled} onClick={() => onPage(page - 1)} aria-label="Previous page"><ChevronLeft size={15} aria-hidden="true" /><span className={s.navigationWord}>Previous</span></Button>
        {pages.map((value, index) => <span key={value} className={s.pageSlot}>{index > 0 && value - pages[index - 1] > 1 && <span className={s.ellipsis}>…</span>}<button type="button" className={`${s.page} ${value === page ? s.current : ''}`} disabled={disabled} onClick={() => onPage(value)} aria-label={`Page ${value}`} aria-current={value === page ? 'page' : undefined}>{value}</button></span>)}
        <Button variant="ghost" small disabled={page >= total || disabled} onClick={() => onPage(page + 1)} aria-label="Next page"><span className={s.navigationWord}>Next</span><ChevronRight size={15} aria-hidden="true" /></Button>
      </div>
    </div>
  </nav>
}
