import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => vi.unstubAllGlobals())

describe('web session access', () => {
  it('starts a server session and clears the view on logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Response(JSON.stringify({ statements: [] }), { status: 200 })))
    render(<App />)

    fireEvent.change(screen.getByLabelText('Contraseña', { exact: false }), { target: { value: 'admin-password' } })
    fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    await screen.findByText('Carga una cartola')
    expect(localStorage.length).toBe(0)
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    await waitFor(() => expect(screen.getByText('Tu balance, bajo control.')).toBeInTheDocument())
  })
})
