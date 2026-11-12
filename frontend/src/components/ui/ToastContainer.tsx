import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { Check, CircleAlert, Info, X } from 'lucide-react'
import { Button } from './Button'
import s from './toast.module.css'

type ToastTone = 'success' | 'warning' | 'error' | 'info'
interface Toast { id: number; message: string; tone: ToastTone }
const ToastContext = createContext<(message: string, tone?: ToastTone) => void>(() => {})

function ToastItem({ toast, dismiss }: { toast: Toast; dismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused) return
    const timer = window.setTimeout(() => dismiss(toast.id), 4000)
    return () => window.clearTimeout(timer)
  }, [toast.id, dismiss, paused])
  const Icon = toast.tone === 'success' ? Check : toast.tone === 'info' ? Info : CircleAlert
  return <div className={`${s.toast} ${s[toast.tone]}`} role={toast.tone === 'error' ? 'alert' : 'status'} onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
    <span className={s.symbol}><Icon size={17} aria-hidden="true" /></span><p>{toast.message}</p>
    <Button variant="ghost" iconOnly aria-label="Dismiss notification" onClick={() => dismiss(toast.id)}><X size={15} aria-hidden="true" /></Button>
  </div>
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [portalTarget, setPortalTarget] = useState<HTMLElement>(document.body)
  const counter = useRef(0)
  useEffect(() => {
    // A native modal makes the rest of the page inert. Keep its notifications
    // inside the active dialog so they remain visible and keyboard accessible.
    const syncTarget = () => setPortalTarget(document.querySelector<HTMLDialogElement>('dialog[open]') || document.body)
    const observer = new MutationObserver(syncTarget)
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['open'] })
    return () => observer.disconnect()
  }, [])
  const notify = useCallback((message: string, tone: ToastTone = 'success') => {
    const toast = { id: ++counter.current, message, tone }
    setToasts((current) => [...current.slice(-3), toast])
  }, [])
  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), [])
  return <ToastContext.Provider value={notify}>{children}{createPortal(
    <div className={s.container} role="region" aria-label="Notifications">{toasts.map((toast) => <ToastItem key={toast.id} toast={toast} dismiss={dismiss} />)}</div>, portalTarget,
  )}</ToastContext.Provider>
}

export const useToast = () => useContext(ToastContext)
