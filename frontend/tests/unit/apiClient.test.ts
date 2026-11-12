import { AxiosError } from 'axios'
import { describe, expect, it } from 'vitest'
import { toApiError } from '../../src/api/apiClient'

function apiFailure(status: number, data: unknown) {
  return new AxiosError('Request failed', 'ERR_BAD_RESPONSE', undefined, undefined, {
    status, data, statusText: 'Error', headers: {}, config: { headers: {} } as never,
  })
}

describe('HTTP error normalization', () => {
  it('preserves field-specific validation messages', () => {
    const error = toApiError(apiFailure(400, { isbn: ['A book with this ISBN already exists.'] }))
    expect(error.status).toBe(400)
    expect(error.fields.isbn).toContain('already exists')
    expect(error.message).toContain('already exists')
  })
  it.each([404, 500, 503])('handles HTTP %i without exposing server HTML', (status) => {
    const error = toApiError(apiFailure(status, '<html>Traceback SECRET</html>'))
    expect(error.status).toBe(status)
    expect(error.message).not.toContain('SECRET')
    expect(error.message).not.toContain('<html>')
  })
  it('distinguishes network failures from HTTP responses', () => {
    expect(toApiError(new AxiosError('Network Error', 'ERR_NETWORK')).status).toBe(0)
  })
})
