import { describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('API client', () => {
  it('uses same-origin credentials without a bearer key', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ statements: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.listStatements()

    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/statements?limit=50&offset=0',
      expect.objectContaining({ credentials: 'same-origin' }),
    )
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })

  it('uses an anchor and omits empty date filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.getAnalysis('anchor-id')

    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/analysis?anchor_statement_id=anchor-id',
      expect.objectContaining({ credentials: 'same-origin' }),
    )
  })
})
