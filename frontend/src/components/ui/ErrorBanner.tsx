import { CircleAlert, RotateCcw } from 'lucide-react'
import { ApiError } from '../../api/apiClient'
import { Button } from './Button'
import s from '../../styles/ui.module.css'

export function ErrorBanner({ error, onRetry, actionLabel = 'Try again' }: { error: Error; onRetry?: () => void; actionLabel?: string }) {
  const warning = error instanceof ApiError && (error.status === 503 || error.status === 400 || error.status === 404)
  return <div role="alert" className={`${s.errorBanner} ${warning ? s.warningBanner : ''}`}>
    <CircleAlert size={20} aria-hidden="true" /><p>{error.message}</p>
    {onRetry && <Button small onClick={onRetry}><RotateCcw size={14} aria-hidden="true" />{actionLabel}</Button>}
  </div>
}
