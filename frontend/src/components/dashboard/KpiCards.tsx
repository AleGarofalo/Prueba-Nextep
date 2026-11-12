import type { InventorySummary } from '../../types'
import { money } from '../../lib/format'
import s from './dashboard.module.css'
import ui from '../../styles/ui.module.css'

export function KpiCards({ summary, loading, lowStock, onLowStock }: { summary?: InventorySummary; loading: boolean; lowStock: boolean; onLowStock: () => void }) {
  return <section className={s.kpis} aria-label="Inventory overview" aria-busy={loading}>
    <article className={s.kpi}><div className={s.kpiTop}><span>Total book titles</span></div><div className={s.kpiValue}>{loading ? <span className={ui.skeleton} style={{ width: 90, height: 29 }} /> : summary ? <>{summary.total_titles.toLocaleString()}<span>titles</span></> : '—'}</div><p>Your entire book catalog</p></article>
    <article className={s.kpi}><div className={s.kpiTop}><span>Inventory value</span></div><div className={`${s.kpiValue} ${s.valuation}`}>{loading ? <span className={ui.skeleton} style={{ width: 90, height: 29 }} /> : summary ? money(summary.inventory_value_usd) : '—'}</div><p>Total import cost · USD</p></article>
    <button type="button" className={`${s.kpi} ${s.lowStockCard} ${lowStock ? s.selectedCard : ''}`} onClick={onLowStock} aria-pressed={lowStock} aria-label="Filter low-stock books" title="Show books with 10 units or fewer"><div className={s.kpiTop}><span>Low-stock alerts</span></div><div className={s.kpiValue}>{loading ? <span className={ui.skeleton} style={{ width: 90, height: 29 }} /> : summary ? <>{summary.low_stock_titles.toLocaleString()}<span>titles</span></> : '—'}</div><p className={s.lowStockCaption}>{summary ? `${summary.out_of_stock_titles} out of stock` : 'Stock at 10 units or below'}<span>View books</span></p></button>
    <article className={s.kpi}><div className={s.kpiTop}><span>Target profit margin</span></div><div className={s.kpiValue}>{summary?.margin_percentage ?? 40}<span>%</span><span className={s.marginTag}>STANDARD</span></div><p title="A 40% commercial markup is applied to the unrounded local cost before the final selling price is saved.">Cost × exchange rate × 1.40</p></article>
  </section>
}
