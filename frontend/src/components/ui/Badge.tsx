import type { ReactNode } from 'react'
import { CircleAlert, CircleCheck, CircleX } from 'lucide-react'
import s from '../../styles/ui.module.css'

export function Badge({ tone = 'neutral', children }: { tone?: 'neutral' | 'success' | 'warning' | 'dangerBadge' | 'brand'; children: ReactNode }) {
  return <span className={`${s.badge} ${s[tone]}`}>{children}</span>
}

export function StockBadge({ quantity }: { quantity: number }) {
  return quantity === 0
    ? <Badge tone="dangerBadge"><CircleX size={12} aria-hidden="true" />Out of stock</Badge>
    : quantity <= 10
      ? <Badge tone="warning"><CircleAlert size={12} aria-hidden="true" />{quantity} units</Badge>
      : <Badge tone="success"><CircleCheck size={12} aria-hidden="true" />{quantity} in stock</Badge>
}
