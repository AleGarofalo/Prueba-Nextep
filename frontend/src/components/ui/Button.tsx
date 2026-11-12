import type { ButtonHTMLAttributes } from 'react'
import { LoaderCircle } from 'lucide-react'
import s from '../../styles/ui.module.css'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  loading?: boolean
  small?: boolean
  iconOnly?: boolean
}

export function Button({ variant = 'secondary', loading, small, iconOnly, className = '', children, disabled, ...props }: Props) {
  return <button type="button" className={`${s.button} ${s[variant]} ${small ? s.small : ''} ${iconOnly ? s.iconButton : ''} ${className}`} disabled={disabled || loading} aria-busy={loading || undefined} {...props}>
    {loading && <LoaderCircle size={16} className={s.spinner} aria-hidden="true" />}{children}
  </button>
}
