import { BookOpen, Plus, Search, X } from 'lucide-react'
import { Button } from '../ui/Button'
import s from './state.module.css'
import ui from '../../styles/ui.module.css'

export function InventorySkeleton() {
  return <div role="status" aria-label="Loading inventory" className={s.skeletonRows}>{[0, 1, 2, 3, 4].map((row) => <div className={s.skeletonRow} key={row}><div className={ui.skeleton} style={{ width: 32, height: 20 }} /><div className={s.skeletonTitle}><div className={ui.skeleton} style={{ width: '70%', height: 15 }} /><div className={ui.skeleton} style={{ width: '40%', height: 11 }} /></div><div className={ui.skeleton} style={{ width: '14%', height: 18 }} /><div className={ui.skeleton} style={{ width: '11%', height: 22 }} /><div className={ui.skeleton} style={{ width: '8%', height: 18 }} /></div>)}</div>
}

export function EmptyInventory({ filtered, onReset, onCreate }: { filtered: boolean; onReset: () => void; onCreate: () => void }) {
  const Icon = filtered ? Search : BookOpen
  return <div className={s.empty}><div className={s.illustration}><span /><Icon size={38} strokeWidth={1.35} aria-hidden="true" /></div><h3>{filtered ? 'No matching books found' : 'Your inventory is empty'}</h3><p>{filtered ? 'Try a different search or clear your filters to see more titles.' : 'Get started by registering your first imported book title.'}</p><Button variant={filtered ? 'secondary' : 'primary'} onClick={filtered ? onReset : onCreate}>{filtered ? <X size={15} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}{filtered ? 'Reset filters' : 'Register first book'}</Button></div>
}
