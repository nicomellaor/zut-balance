import { describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('API client', () => {
  it('sends the key only as a bearer header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ statements: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.listStatements('secret-key')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/statements?limit=50&offset=0',
      expect.objectContaining({ headers: { Authorization: 'Bearer secret-key' } }),
    )
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })
})
