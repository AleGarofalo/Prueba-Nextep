import { useMutation, useQueryClient } from '@tanstack/react-query'
import { TriangleAlert, Trash2 } from 'lucide-react'
import { deleteBook } from '../../api/apiClient'
import type { ApiError } from '../../api/apiClient'
import type { Book } from '../../types'
import { Dialog } from '../ui/Dialog'
import { Button } from '../ui/Button'
import { ErrorBanner } from '../ui/ErrorBanner'
import { useToast } from '../ui/ToastContainer'
import s from './modals.module.css'

export function ConfirmDeleteModal({ book, onClose, onDeleted, onError }: { book: Book; onClose: () => void; onDeleted: () => void; onError: (error: ApiError) => void }) {
  const notify = useToast()
  const client = useQueryClient()
  const mutation = useMutation({
    mutationFn: () => deleteBook(book.id),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['books'] }); notify(`“${book.title}” was removed from inventory.`); onDeleted() },
    onError,
  })
  return <Dialog title="Delete book from inventory?" onClose={onClose} footer={<><Button onClick={onClose}>Cancel</Button><Button variant="danger" loading={mutation.isPending} onClick={() => mutation.mutate()}>{!mutation.isPending && <Trash2 size={15} aria-hidden="true" />}{mutation.isPending ? 'Deleting…' : 'Yes, delete book'}</Button></>}>
    {mutation.error && <div className={s.errorSpace}><ErrorBanner error={mutation.error} /></div>}
    <div className={s.deleteIcon}><TriangleAlert size={25} aria-hidden="true" /></div>
    <p className={s.deleteCopy}>Are you sure you want to permanently delete <strong>“{book.title}”</strong>? This will remove the book and its inventory record. This action cannot be undone.</p>
    <div className={s.deleteIsbn}>ISBN {book.isbn} · Book #{book.id}</div>
  </Dialog>
}
