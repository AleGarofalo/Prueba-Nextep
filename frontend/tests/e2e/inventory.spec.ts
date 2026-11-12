import { test, expect } from '@playwright/test'
import type { APIRequestContext, Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const createdIds = new Set<number>()

function isbn() {
  const body = '978' + String(Math.floor(Math.random() * 1e9)).padStart(9, '0')
  const total = [...body].reduce((sum, value, index) => sum + Number(value) * (index % 2 ? 3 : 1), 0)
  return body + String((-total % 10 + 10) % 10)
}

async function seedBook(request: APIRequestContext) {
  const payload = { title: `UI Test ${Date.now()}`, author: 'Frontend QA', isbn: isbn(), cost_usd: '15.99', stock_quantity: 5, category: 'Fiction', supplier_country: 'ES' }
  const response = await request.post('/api/books', { data: payload })
  expect(response.status()).toBe(201)
  const book = await response.json()
  createdIds.add(book.id)
  return book
}

async function ready(page: Page) {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Book inventory.' })).toBeVisible()
  await expect(page.getByText('API Online', { exact: true })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await page.evaluate(() => document.fonts.ready)
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.clear())
})

test.afterEach(async ({ request }) => {
  for (const id of createdIds) {
    const response = await request.delete(`/api/books/${id}`)
    expect([204, 404]).toContain(response.status())
  }
  createdIds.clear()
})

test('dashboard, real server search, combined filters and pagination', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await ready(page)
  await page.screenshot({ path: 'test-results/inventory-desktop.png', fullPage: true })
  await expect(page.getByRole('row')).toHaveCount(11)
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByRole('button', { name: 'Page 2', exact: true })).toHaveAttribute('aria-current', 'page')
  await page.getByLabel('Search by title, author, or ISBN', { exact: true }).fill('Demo 01')
  await expect(page.getByRole('row')).toHaveCount(2)
  await page.getByLabel('Search by title, author, or ISBN', { exact: true }).fill('nothing-will-match-this-search')
  await expect(page.getByRole('heading', { name: 'No matching books found' })).toBeVisible()
  await page.getByRole('button', { name: 'Reset filters' }).click()
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByLabel('Filter by category', { exact: true }).selectOption('Ciencia')
  await expect(page.getByRole('row')).toHaveCount(6)
  await page.getByRole('button', { name: 'Low stock ≤10', exact: false }).click()
  await expect(page.getByRole('row')).toHaveCount(4)
  await page.getByRole('button', { name: 'Clear all', exact: true }).click()
  await page.getByLabel('Results per page', { exact: true }).selectOption('25')
  await expect(page.getByRole('row')).toHaveCount(26)
  expect(errors).toEqual([])
})

test('cards, dark mode, keyboard dialog dismissal and accessibility', async ({ page }) => {
  await ready(page)
  const light = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(light.violations).toEqual([])
  await page.getByRole('button', { name: 'Cards view', exact: true }).click()
  await expect(page.getByRole('table')).toHaveCount(0)
  await page.getByRole('button', { name: 'Toggle dark mode', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.screenshot({ path: 'test-results/inventory-dark.png', fullPage: true })
  const dark = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(dark.violations).toEqual([])
  await page.getByRole('button', { name: 'New book', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await expect(page.getByLabel('Book title', { exact: false })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'New book', exact: true })).toBeFocused()
})

test('create, validate, inspect, edit, calculate, verify persistence and delete', async ({ page, request }) => {
  await ready(page)
  await page.getByRole('button', { name: 'New book', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Save book', exact: true }).click()
  await expect(dialog.getByText('Enter a title with at least 2 characters.', { exact: true })).toBeVisible()
  const title = `UI Book ${Date.now()}`
  await dialog.getByLabel('Book title').fill(title)
  await dialog.getByLabel('Author', { exact: false }).fill('UI Test Author')
  await dialog.getByLabel('Category').selectOption('Fiction')
  await dialog.getByLabel('ISBN code').fill('9788437604948')
  await dialog.getByLabel('Supplier country').selectOption('ES')
  await dialog.getByLabel('Import cost (USD)').fill('0')
  await dialog.getByLabel('Stock quantity').fill('-1')
  await dialog.getByRole('button', { name: 'Save book', exact: true }).click()
  await expect(dialog.getByText('ISBN must be a valid 10 or 13-digit code.', { exact: true })).toBeVisible()
  await expect(dialog.getByText(/Cost must be greater than 0 USD/)).toBeVisible()
  await expect(dialog.getByText(/Stock quantity must be a whole number/)).toBeVisible()
  await dialog.getByLabel('ISBN code').fill(isbn())
  await dialog.getByLabel('Import cost (USD)').fill('15.99')
  await dialog.getByLabel('Stock quantity').fill('5')
  const responsePromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/books' && response.request().method() === 'POST' && response.status() === 201)
  await dialog.getByRole('button', { name: 'Save book', exact: true }).click()
  const book = await (await responsePromise).json()
  createdIds.add(book.id)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: title, exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Book details' })).toBeVisible()
  await page.getByRole('button', { name: 'Edit book', exact: true }).click()
  await expect(page.getByLabel('Book title', { exact: false })).toHaveValue(title)
  await page.getByLabel('Import cost (USD)').fill('20.00')
  await page.getByRole('button', { name: 'Save changes', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.getByRole('button', { name: `Calculate price for ${title}`, exact: true }).click()
  await expect(page.getByText('FINAL SUGGESTED SELLING PRICE', { exact: true })).toBeVisible()
  await expect(page.getByText('Saved to inventory', { exact: true })).toBeVisible()
  const saved = await (await request.get(`/api/books/${book.id}`)).json()
  expect(saved.cost_usd).toBe('20.00')
  expect(saved.selling_price_local).not.toBeNull()
  const modalAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(modalAxe.violations).toEqual([])
  await page.screenshot({ path: 'test-results/pricing-breakdown.png', fullPage: true })
  await page.getByRole('button', { name: 'Done', exact: true }).click()
  await page.getByRole('button', { name: `Delete ${title}`, exact: true }).click()
  await expect(page.getByRole('dialog', { name: 'Delete book from inventory?' })).toBeVisible()
  await page.getByRole('button', { name: 'Cancel', exact: true }).click()
  expect((await request.get(`/api/books/${book.id}`)).status()).toBe(200)
  await page.getByRole('button', { name: `Delete ${title}`, exact: true }).click()
  await page.getByRole('button', { name: 'Yes, delete book', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect((await request.get(`/api/books/${book.id}`)).status()).toBe(404)
})

test('duplicate ISBN errors appear on the form without losing input', async ({ page }) => {
  await ready(page)
  const first = await page.locator('table tbody tr').first().locator('td').nth(2).innerText()
  const existingISBN = first.trim().match(/[0-9X]{10,13}/)![0]
  await page.getByRole('button', { name: 'New book', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Book title').fill('A duplicate example')
  await dialog.getByLabel('Author', { exact: false }).fill('Example Author')
  await dialog.getByLabel('Category').selectOption('Fiction')
  await dialog.getByLabel('ISBN code').fill(existingISBN)
  await dialog.getByLabel('Supplier country').selectOption('ES')
  await dialog.getByLabel('Import cost (USD)').fill('10.00')
  await dialog.getByRole('button', { name: 'Save book', exact: true }).click()
  await expect(dialog.getByLabel('ISBN code')).toHaveAttribute('aria-invalid', 'true')
  await expect(dialog.getByLabel('Book title')).toHaveValue('A duplicate example')
})

test('503 does not claim a fallback succeeded; 200 fallback is clearly labeled', async ({ page, request }) => {
  const book = await seedBook(request)
  await ready(page)
  await page.route('**/api/books/*/calculate-price', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Unavailable' }) }))
  await page.getByRole('button', { name: `Calculate price for ${book.title}`, exact: true }).click()
  await expect(page.getByRole('dialog').getByRole('alert')).toContainText('unavailable')
  await expect(page.getByText('No new selling price was saved. Your previous saved price is unchanged.', { exact: true })).toBeVisible()
  await page.unroute('**/api/books/*/calculate-price')
  await page.route('**/api/books/*/calculate-price', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
    book_id: book.id, cost_usd: '15.99', cost_local: '13.59', exchange_rate: '0.85', margin_percentage: 40,
    selling_price_local: '19.03', currency: 'EUR', calculation_timestamp: new Date().toISOString(),
    rates_fetched_at: null, rate_source: 'default', is_fallback: true, provider: 'ExchangeRate-API', provider_url: 'https://www.exchangerate-api.com',
  }) }))
  await page.getByRole('dialog').getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(page.getByRole('dialog').getByText(/A configured default fallback rate/)).toBeVisible()
  await expect(page.getByText('FINAL SUGGESTED SELLING PRICE', { exact: true })).toBeVisible()
})

test('404 refreshes inventory and 500 has a working retry', async ({ page, request }) => {
  const book = await seedBook(request)
  await ready(page)
  await page.route(`**/api/books/${book.id}`, (route) => route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not found' }) }))
  await page.getByRole('button', { name: book.title, exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByText(/This book or page is no longer available/)).toBeVisible()
  await page.unroute(`**/api/books/${book.id}`)
  await page.route('**/api/books/summary', (route) => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Failure' }) }))
  await page.getByRole('button', { name: 'Refresh data', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('The server could not complete this request')
  await page.unroute('**/api/books/summary')
  await page.getByRole('button', { name: 'Refresh inventory', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('currency display, mobile layout, loading and empty states', async ({ page, request }) => {
  const book = await seedBook(request)
  expect((await request.post(`/api/books/${book.id}/calculate-price`, { data: {} })).status()).toBe(200)
  const saved = await (await request.get(`/api/books/${book.id}`)).json()
  await ready(page)
  for (const currency of ['GBP', 'MXN', 'USD']) {
    const rateResponse = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/books/exchange-rate' && response.url().includes(`currency=${currency}`))
    await page.getByLabel('Display currency', { exact: true }).selectOption(currency)
    const response = await rateResponse
    expect(response.status()).toBe(200)
    const rate = await response.json()
    const amount = new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(Number(saved.selling_price_local) * Number(rate.conversion_rate))
    const row = page.getByRole('row').filter({ has: page.getByRole('button', { name: book.title, exact: true }) })
    await expect(row.locator('td').nth(7)).toContainText(amount)
    await expect(page.getByText(`Prices shown in ${currency}; selling prices are saved in EUR.`, { exact: true })).toBeVisible()
  }
  const afterConversion = await (await request.get(`/api/books/${book.id}`)).json()
  expect(afterConversion.selling_price_local).toBe(saved.selling_price_local)
  expect(afterConversion.updated_at).toBe(saved.updated_at)
  await page.getByRole('button', { name: 'Cards view', exact: true }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/inventory-mobile.png', fullPage: true })
  const mobileAxe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(mobileAxe.violations).toEqual([])
  await page.route((url) => url.pathname === '/api/books', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500))
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, results: [], next: null, previous: null }) })
  })
  await page.route('**/api/books/summary', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ total_titles: 0, inventory_value_usd: '0.00', low_stock_titles: 0, out_of_stock_titles: 0, categories: [], local_currency: 'EUR', margin_percentage: 40, last_updated_at: null }) }))
  await page.reload()
  await expect(page.getByRole('status', { name: 'Loading inventory', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Your inventory is empty', exact: true })).toBeVisible()
})
