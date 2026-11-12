import { BookOpen, Globe, Moon, RefreshCw, Sun } from 'lucide-react'
import type { ApiHealth } from '../../types'
import { Button } from '../ui/Button'
import s from './layout.module.css'

export function Header({ health, currency, localCurrency, onCurrencyChange, theme, onToggleTheme, onRefresh, refreshing }: {
  health: ApiHealth; currency: string; localCurrency: string; onCurrencyChange: (value: string) => void
  theme: string; onToggleTheme: () => void; onRefresh: () => void; refreshing: boolean
}) {
  const currencies = [...new Set([localCurrency, 'EUR', 'USD', 'GBP', 'MXN'])]
  const label = { online: 'API Online', checking: 'Connecting', offline: 'API Offline', degraded: 'API Issue' }[health]
  return <header className={s.header}>
    <div className={s.headerInner}>
      <a href="#main-content" className={s.skip}>Skip to inventory</a>
      <div className={s.brand}><span className={s.brandMark}><BookOpen size={23} strokeWidth={1.8} aria-hidden="true" /></span><span>nextep<span className={s.brandDot}>.</span><span className={s.brandBookstore}>bookstore</span></span><span className={s.version}>v1.0 REST API</span></div>
      <div className={s.controls}>
        <span className={`${s.status} ${s[health]}`} role="status"><span className={s.dot} />{label}</span>
        <div className={s.currency}><Globe size={15} aria-hidden="true" /><label htmlFor="display-currency">View currency</label><select id="display-currency" aria-label="Display currency" value={currency} onChange={(event) => onCurrencyChange(event.target.value)}>{currencies.map((code) => <option key={code}>{code}</option>)}</select></div>
        <div className={s.headerActions}><Button variant="ghost" iconOnly onClick={onRefresh} loading={refreshing} aria-label="Refresh data" title="Refresh inventory">{!refreshing && <RefreshCw size={17} aria-hidden="true" />}</Button><Button variant="ghost" iconOnly onClick={onToggleTheme} aria-label="Toggle dark mode" aria-pressed={theme === 'dark'} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>{theme === 'dark' ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}</Button></div>
      </div>
    </div>
  </header>
}
