import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, CircleAlert, Clock, ExternalLink, Globe, RefreshCw } from 'lucide-react'
import { ApiError, calculatePrice } from '../../api/apiClient'
import type { Book, PriceCalculation } from '../../types'
import { money, utcDate } from '../../lib/format'
import { Button } from '../ui/Button'
import { Dialog } from '../ui/Dialog'
import { Badge } from '../ui/Badge'
import { ErrorBanner } from '../ui/ErrorBanner'
import { useToast } from '../ui/ToastContainer'
import { ModalSkeleton } from './BookFormModal'
import s from './modals.module.css'
import ui from '../../styles/ui.module.css'

export function PriceBreakdownModal({ book, localCurrency, onClose, onError }: { book: Book; localCurrency: string; onClose: () => void; onError: (error: ApiError) => void }) {
  const started = useRef(false)
  const [quote, setQuote] = useState<PriceCalculation | null>(null)
  const notify = useToast()
  const client = useQueryClient()
  const { mutate, isPending, error } = useMutation({
    mutationFn: () => calculatePrice(book.id),
    onSuccess: (data) => {
      setQuote(data)
      void client.invalidateQueries({ queryKey: ['books'] })
      notify(data.is_fallback ? 'Selling price saved using a fallback rate.' : 'Selling price calculated and saved.', data.is_fallback ? 'warning' : 'success')
    },
    onError,
  })
  useEffect(() => { if (!started.current) { started.current = true; mutate() } }, [mutate])
  const sourceLabel = quote ? { live: 'Live rate', cache: 'Cached rate', stale_cache: 'Last-known rate', default: 'Default fallback', identity: 'USD base rate' }[quote.rate_source] : ''
  return <Dialog title="Suggested selling price calculation" subtitle={`${book.title} · Book #${book.id} · Base currency: USD`} onClose={onClose} footer={<><Button onClick={() => mutate()} loading={isPending}><RefreshCw size={15} aria-hidden="true" />{isPending ? 'Calculating…' : 'Recalculate'}</Button><Button variant="primary" onClick={onClose}>{quote ? 'Done' : 'Close'}</Button></>}>
    {error && <div className={s.errorSpace}><ErrorBanner error={error} onRetry={() => mutate()} />{error instanceof ApiError && error.status === 503 && <p className={ui.hint} style={{ marginTop: 8 }}>No new selling price was saved. Your previous saved price is unchanged.</p>}</div>}
    {quote?.is_fallback && <div className={`${ui.errorBanner} ${ui.warningBanner}`} role="status"><CircleAlert size={20} aria-hidden="true" /><p>{quote.rate_source === 'default' ? 'The external exchange-rate service was unavailable. A configured default fallback rate' : 'The external exchange-rate service was unavailable. A last-known cached rate'} of 1 USD = {quote.exchange_rate} {quote.currency} was applied.</p></div>}
    {!quote && !error ? <ModalSkeleton label="Fetching exchange rates and calculating the selling price…" /> : quote ? <>
      {isPending && <p className={ui.hint} role="status" style={{ marginTop: 12 }}>Updating the calculation…</p>}
      {error && <p className={ui.hint}>Last successful calculation</p>}
      <div className={s.breakdown}>
        <div className={s.step}><span className={s.stepNumber}>01</span><span className={s.stepLabel}>Original import cost<small>Base cost in US dollars</small></span><strong className={s.stepValue}>{money(quote.cost_usd)} USD</strong></div>
        <div className={s.step}><span className={s.stepNumber}>02</span><span className={s.stepLabel}>Exchange rate · USD → {quote.currency}<small><Badge tone={quote.is_fallback ? 'warning' : quote.rate_source === 'live' ? 'success' : 'neutral'}><Globe size={11} aria-hidden="true" />{sourceLabel}</Badge></small></span><strong className={s.stepValue}>1 USD = {quote.exchange_rate} {quote.currency}</strong></div>
        <div className={s.step}><span className={s.stepNumber}>03</span><span className={s.stepLabel}>Converted local cost<small>Import cost × exchange rate</small></span><strong className={s.stepValue}>{money(quote.cost_local, quote.currency)}</strong></div>
        <div className={s.step}><span className={s.stepNumber}>04</span><span className={s.stepLabel}>Commercial markup<small>Applied before rounding the final price</small></span><strong className={s.stepValue}>+{quote.margin_percentage.toFixed(2)}%</strong></div>
      </div>
      <div className={s.total}><span>FINAL SUGGESTED SELLING PRICE</span><strong>{money(quote.selling_price_local, quote.currency)} <small style={{ fontSize: 13, fontWeight: 500 }}>{quote.currency}</small></strong></div>
      <div className={s.calculationMeta}><span><Clock size={11} aria-hidden="true" style={{ verticalAlign: -1 }} /> {utcDate(quote.calculation_timestamp)}</span><span className={s.saved}><Check size={13} aria-hidden="true" />Saved to inventory</span></div>
      {quote.rates_fetched_at && <p className={ui.hint} style={{ marginTop: 6 }}>Rate snapshot retrieved {utcDate(quote.rates_fetched_at)}.</p>}
      <p className={s.provider}>Rates by <a href="https://www.exchangerate-api.com" target="_blank" rel="noreferrer">ExchangeRate-API <ExternalLink size={10} aria-hidden="true" /></a>. Selling prices are saved in {localCurrency}.</p>
    </> : <p className={ui.hint}>A calculation is not available yet. Use “Try again” to request a new price.</p>}
  </Dialog>
}
