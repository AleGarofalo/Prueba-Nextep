import { describe, expect, it } from 'vitest'
import { formValues, normalizeISBN, toBookInput, validISBN, validateBook } from '../../src/lib/validation'

const valid = {
  ...formValues(), title: 'A book', author: 'An author', isbn: '978-84-376-0494-7',
  cost_usd: '15.99', stock_quantity: '0', category: 'Fiction', supplier_country: 'ES',
}

describe('Book form validation', () => {
  it.each(['978-84-376-0494-7', '0-8044-2957-x', '0306406152', '9791234567896'])('accepts valid ISBN %s', (isbn) => {
    expect(validISBN(isbn)).toBe(true)
  })
  it.each(['9788437604948', '0306406153', '0804429570', '1234567890128', 'abc', '９７８８４３７６０４９４７'])('rejects invalid ISBN %s', (isbn) => {
    expect(validISBN(isbn)).toBe(false)
  })
  it('normalizes separators and check digits', () => {
    expect(normalizeISBN(' 0-8044-2957-x ')).toBe('080442957X')
  })
  it.each(['0', '-1', 'NaN', 'Infinity', '1.234', '100000000.00', '1e3'])('rejects invalid cost %s', (cost_usd) => {
    expect(validateBook({ ...valid, cost_usd }).cost_usd).toBeTruthy()
  })
  it.each(['-1', '1.5', '1e3', '2147483648', ''])('rejects invalid stock %s', (stock_quantity) => {
    expect(validateBook({ ...valid, stock_quantity }).stock_quantity).toBeTruthy()
  })
  it('accepts a positive cost and zero stock and creates a clean API payload', () => {
    expect(validateBook(valid)).toEqual({})
    expect(toBookInput(valid)).toMatchObject({ isbn: '9788437604947', cost_usd: '15.99', stock_quantity: 0 })
  })
  it('rejects blank or short text and invalid countries', () => {
    expect(validateBook({ ...valid, title: ' ', author: 'A', supplier_country: 'ZZ' })).toMatchObject({
      title: expect.any(String), author: expect.any(String), supplier_country: expect.any(String),
    })
  })
})
