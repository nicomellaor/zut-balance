import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => vi.unstubAllGlobals())

describe('local access', () => {
  it('keeps a successful key in memory and clears access on logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Response(JSON.stringify({ statements: [] }), { status: 200 })))
    render(<App />)

    fireEvent.change(screen.getByLabelText('API key', { exact: false }), { target: { value: 'secret-key' } })
    fireEvent.click(screen.getByRole('button', { name: 'Acceder' }))

    await screen.findByText('Carga una cartola')
    expect(localStorage.length).toBe(0)
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    await waitFor(() => expect(screen.getByText('Tu balance, bajo control.')).toBeInTheDocument())
  })
})
