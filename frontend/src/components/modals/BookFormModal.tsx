import { useId, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Info, Save } from 'lucide-react'
import { ApiError, createBook, updateBook } from '../../api/apiClient'
import type { Book, FieldErrors } from '../../types'
import { COUNTRIES } from '../../lib/format'
import { formValues, toBookInput, validateBook } from '../../lib/validation'
import type { BookFormValues } from '../../lib/validation'
import { useBook, useReportError } from '../../hooks/useInventory'
import { Button } from '../ui/Button'
import { Dialog } from '../ui/Dialog'
import { ErrorBanner } from '../ui/ErrorBanner'
import { useToast } from '../ui/ToastContainer'
import s from './modals.module.css'
import ui from '../../styles/ui.module.css'

interface Props {
  book?: Book; categories: string[]; onClose: () => void
  onSaved: (book: Book, created: boolean) => void; onError: (error: ApiError) => void
}

function FormContent({ book, categories, onClose, onSaved, onError }: Props) {
  const [values, setValues] = useState(() => formValues(book))
  const [errors, setErrors] = useState<FieldErrors>({})
  const formId = useId()
  const ref = useRef<HTMLFormElement>(null)
  const notify = useToast()
  const client = useQueryClient()
  function focusError(fields: FieldErrors) {
    const first = Object.keys(values).find((field) => fields[field])
    const element = first ? ref.current?.elements.namedItem(first) : null
    if (element instanceof HTMLElement) element.focus()
  }
  const mutation = useMutation({
    mutationFn: () => book ? updateBook(book.id, toBookInput(values)) : createBook(toBookInput(values)),
    onSuccess: (saved) => {
      void client.invalidateQueries({ queryKey: ['books'] })
      notify(`“${saved.title}” was ${book ? 'updated' : 'added to your inventory'}.`)
      onSaved(saved, !book)
    },
    onError: (error: ApiError) => { setErrors(error.fields); focusError(error.fields); onError(error) },
  })
  function change(field: keyof BookFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => { const next = { ...current }; delete next[field]; return next })
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    if (mutation.isPending) return
    const fields = validateBook(values)
    setErrors(fields)
    if (Object.keys(fields).length) { focusError(fields); return }
    mutation.mutate()
  }
  function field(name: keyof BookFormValues, label: string, input: ReactNode, full = false) {
    return <div className={`${ui.field} ${full ? s.full : ''}`}><label htmlFor={`${formId}-${name}`}>{label}<span className={ui.required} aria-hidden="true">*</span></label>{input}{errors[name] && <p id={`${formId}-${name}-error`} className={ui.fieldError}>{errors[name]}</p>}</div>
  }
  function props(name: keyof BookFormValues) {
    return {
      id: `${formId}-${name}`, name, value: values[name], required: true,
      className: ui.input, disabled: mutation.isPending,
      'aria-invalid': !!errors[name], 'aria-describedby': errors[name] ? `${formId}-${name}-error` : undefined,
      onBlur: () => {
        const message = validateBook(values)[name]
        if (message) setErrors((current) => ({ ...current, [name]: message }))
      },
    }
  }
  const availableCategories = [...new Set([...categories, ...(book?.category ? [book.category] : [])])].sort()
  return <Dialog title={book ? 'Edit book' : 'Add new book to inventory'} subtitle={book ? `Update the details for “${book.title}”.` : 'A new title starts with its import cost. Calculate its selling price afterward.'} onClose={onClose} wide footer={<><Button onClick={onClose}>Cancel</Button><Button type="submit" form={formId} variant="primary" loading={mutation.isPending}>{!mutation.isPending && <Save size={16} aria-hidden="true" />}{mutation.isPending ? 'Saving…' : book ? 'Save changes' : 'Save book'}</Button></>}>
    {mutation.error && <div className={s.errorSpace}><ErrorBanner error={mutation.error} /></div>}
    <form id={formId} ref={ref} className={s.form} onSubmit={submit} noValidate>
      {field('title', 'Book title', <input {...props('title')} onChange={(event) => change('title', event.target.value)} autoFocus maxLength={255} placeholder="Enter the title of the book" autoComplete="off" />, true)}
      {field('author', 'Author', <input {...props('author')} onChange={(event) => change('author', event.target.value)} maxLength={255} placeholder="Author’s full name" autoComplete="off" />)}
      {field('category', 'Category', <select {...props('category')} onChange={(event) => change('category', event.target.value)}><option value="">Select a category</option>{availableCategories.map((category) => <option key={category}>{category}</option>)}</select>)}
      {field('isbn', 'ISBN code', <input {...props('isbn')} onChange={(event) => change('isbn', event.target.value)} className={`${ui.input} ${ui.mono}`} placeholder="978-84-376-0494-7" maxLength={32} autoComplete="off" />)}
      {field('supplier_country', 'Supplier country', <select {...props('supplier_country')} onChange={(event) => change('supplier_country', event.target.value)}><option value="">Select supplier country</option>{COUNTRIES.map(({ code, name }) => <option key={code} value={code}>{code} — {name}</option>)}</select>)}
      {field('cost_usd', 'Import cost (USD)', <input {...props('cost_usd')} onChange={(event) => change('cost_usd', event.target.value)} inputMode="decimal" className={`${ui.input} ${ui.mono}`} placeholder="15.99" autoComplete="off" />)}
      {field('stock_quantity', 'Stock quantity', <input {...props('stock_quantity')} onChange={(event) => change('stock_quantity', event.target.value)} inputMode="numeric" className={`${ui.input} ${ui.mono}`} placeholder="0" autoComplete="off" />)}
      <p className={`${s.formHint} ${s.full}`}><Info size={15} aria-hidden="true" /><span>All fields are required. ISBN checksums are validated before saving. Local selling prices are generated with the pricing action{book ? '; changing the import cost clears the previous selling price.' : '.'}</span></p>
    </form>
  </Dialog>
}

function EditForm({ book, ...props }: Props & { book: Book }) {
  const query = useBook(book.id)
  useReportError(query.error, props.onError)
  if (!query.data) return <Dialog title="Edit book" onClose={props.onClose}>{query.error ? <ErrorBanner error={query.error} onRetry={() => void query.refetch()} /> : <ModalSkeleton label="Loading book details…" />}</Dialog>
  return <FormContent key={query.data.id} book={query.data} {...props} />
}

export function BookFormModal(props: Props) {
  return props.book ? <EditForm {...props} book={props.book} /> : <FormContent {...props} />
}

export function ModalSkeleton({ label }: { label: string }) {
  return <div className={s.loading} role="status" aria-label={label}><p className={s.loadingTitle}>{label}</p>{[0, 1, 2, 3, 4].map((value) => <div key={value} className={ui.skeleton} style={{ height: 34, width: value % 2 ? '75%' : '100%' }} />)}</div>
}
