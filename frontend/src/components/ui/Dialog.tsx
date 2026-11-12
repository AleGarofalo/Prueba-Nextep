import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { Button } from './Button'
import s from '../modals/modals.module.css'

export function Dialog({ title, subtitle, onClose, children, footer, wide = false }: {
  title: string; subtitle?: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current!
    const focused = document.activeElement as HTMLElement | null
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.showModal()
    dialog.querySelector<HTMLElement>('input:not([disabled]), select:not([disabled]), textarea:not([disabled])')?.focus()
    return () => {
      dialog.close()
      document.body.style.overflow = previousOverflow
      if (focused?.isConnected) focused.focus()
    }
  }, [])
  return <dialog ref={ref} aria-modal="true" aria-labelledby={titleId} className={`${s.dialog} ${wide ? s.wide : ''}`} onCancel={(event) => { event.preventDefault(); onClose() }} onClick={(event) => {
    if (event.target !== ref.current) return
    const rect = ref.current.getBoundingClientRect()
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose()
  }}>
    <header className={s.header}><div><h2 id={titleId}>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><Button variant="ghost" iconOnly onClick={onClose} aria-label="Close dialog"><X size={19} aria-hidden="true" /></Button></header>
    <div className={s.body}>{children}</div>
    {footer && <footer className={s.footer}>{footer}</footer>}
  </dialog>
}
