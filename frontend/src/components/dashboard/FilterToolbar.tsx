import { CircleAlert, Grid2X2, List, Plus, Search, X } from 'lucide-react'
import type { ViewMode } from '../../types'
import { Button } from '../ui/Button'
import s from './dashboard.module.css'
import ui from '../../styles/ui.module.css'

export function FilterToolbar({ search, onSearch, category, onCategory, categories, lowStock, onLowStock, onCreate }: {
  search: string; onSearch: (value: string) => void; category: string; onCategory: (value: string) => void
  categories: string[]; lowStock: boolean; onLowStock: () => void; onCreate: () => void
}) {
  return <div className={s.toolbar}>
    <div className={s.search}><label htmlFor="inventory-search" className={ui.srOnly}>Search by title, author, or ISBN</label><Search size={17} aria-hidden="true" /><input id="inventory-search" placeholder="Search by title, author, or ISBN..." value={search} onChange={(event) => onSearch(event.target.value)} maxLength={255} autoComplete="off" />{search && <button type="button" onClick={() => onSearch('')} aria-label="Clear search"><X size={15} aria-hidden="true" /></button>}</div>
    <label className={ui.srOnly} htmlFor="category-filter">Filter by category</label><select id="category-filter" aria-label="Filter by category" className={s.categorySelect} value={category} onChange={(event) => onCategory(event.target.value)}><option value="">All categories</option>{categories.map((value) => <option key={value}>{value}</option>)}</select>
    <button type="button" className={`${s.lowStockToggle} ${lowStock ? s.activeLowStock : ''}`} aria-pressed={lowStock} onClick={onLowStock}><CircleAlert size={15} aria-hidden="true" />Low stock <span>≤10</span></button>
    <Button variant="primary" onClick={onCreate}><Plus size={17} aria-hidden="true" />New book</Button>
  </div>
}

export function ViewModeControl({ value, onChange }: { value: ViewMode; onChange: (value: ViewMode) => void }) {
  return <div className={s.viewModes} role="group" aria-label="Inventory view"><button type="button" aria-label="Table view" aria-pressed={value === 'table'} className={value === 'table' ? s.activeView : ''} onClick={() => onChange('table')} title="Table view"><List size={16} aria-hidden="true" /><span>Table</span></button><button type="button" aria-label="Cards view" aria-pressed={value === 'cards'} className={value === 'cards' ? s.activeView : ''} onClick={() => onChange('cards')} title="Cards view"><Grid2X2 size={15} aria-hidden="true" /><span>Cards</span></button></div>
}
