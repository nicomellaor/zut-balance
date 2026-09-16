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

  it('uses an account, omits empty date filters, and forwards cancellation', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    const controller = new AbortController()
    await api.getAnalysis('account-id', undefined, undefined, controller.signal)

    expect(fetchMock).toHaveBeenCalledWith(
      '/v1/analysis?account_id=account-id',
      expect.objectContaining({ credentials: 'same-origin', signal: controller.signal }),
    )
  })

  it('loads the account catalog', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ accounts: [] }), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    await api.listAccounts()
    expect(fetchMock).toHaveBeenCalledWith('/v1/accounts', expect.objectContaining({ credentials: 'same-origin' }))
  })
})
