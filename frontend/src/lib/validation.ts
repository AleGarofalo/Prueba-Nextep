import type { Book, BookInput, FieldErrors } from '../types'
import { COUNTRY_CODES } from './format'

export interface BookFormValues {
  title: string
  author: string
  isbn: string
  cost_usd: string
  stock_quantity: string
  category: string
  supplier_country: string
}

export const normalizeISBN = (value: string) => value.replace(/[-\s]/g, '').toUpperCase()

export function validISBN(raw: string): boolean {
  const value = normalizeISBN(raw)
  if (/^[0-9]{9}[0-9X]$/.test(value)) {
    return [...value].reduce((sum, digit, index) => sum + (digit === 'X' ? 10 : Number(digit)) * (10 - index), 0) % 11 === 0
  }
  if (/^97[89][0-9]{10}$/.test(value)) {
    return [...value].reduce((sum, digit, index) => sum + Number(digit) * (index % 2 ? 3 : 1), 0) % 10 === 0
  }
  return false
}

export function formValues(book?: Book): BookFormValues {
  return {
    title: book?.title || '', author: book?.author || '', isbn: book?.isbn || '',
    cost_usd: book?.cost_usd || '', stock_quantity: String(book?.stock_quantity ?? 0),
    category: book?.category || '', supplier_country: book?.supplier_country || '',
  }
}

export function validateBook(values: BookFormValues): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of ['title', 'author'] as const) {
    const value = values[field].trim()
    if (value.length < 2) errors[field] = `Enter a ${field} with at least 2 characters.`
    else if (value.length > 255) errors[field] = 'Use no more than 255 characters.'
  }
  if (!validISBN(values.isbn)) errors.isbn = 'ISBN must be a valid 10 or 13-digit code.'
  const cost = values.cost_usd.trim()
  if (!/^\d+(\.\d{1,2})?$/.test(cost) || Number(cost) <= 0) errors.cost_usd = 'Cost must be greater than 0 USD, with up to 2 decimal places.'
  else if (Number(cost) > 99999999.99) errors.cost_usd = 'Cost cannot exceed 99,999,999.99 USD.'
  if (!/^\d+$/.test(values.stock_quantity) || Number(values.stock_quantity) > 2147483647) errors.stock_quantity = 'Stock quantity must be a whole number from 0 to 2,147,483,647.'
  if (!values.category.trim()) errors.category = 'Select a category.'
  else if (values.category.length > 100) errors.category = 'Use no more than 100 characters.'
  if (!COUNTRY_CODES.has(values.supplier_country)) errors.supplier_country = 'Select a valid supplier country.'
  return errors
}

export function toBookInput(values: BookFormValues): BookInput {
  return {
    title: values.title.trim(), author: values.author.trim(), isbn: normalizeISBN(values.isbn),
    cost_usd: Number(values.cost_usd).toFixed(2), stock_quantity: Number(values.stock_quantity),
    category: values.category.trim(), supplier_country: values.supplier_country,
  }
}
