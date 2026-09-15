import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App, { Dashboard } from './App'
import type { Analysis } from './api'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

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

describe('analysis dashboard', () => {
  const analysis: Analysis = {
    scope: { statement_ids: ['one'], from: '2026-01-01', to: '2026-01-31', currency: 'CLP', ruleset_versions: ['1'] },
    coverage: { covered_ranges: [{ from: '2026-01-01', to: '2026-01-31' }], gaps: [], partial_months: [] },
    summary: { spending_amount: 300, transaction_count: 3, credits_amount: 20, credits_count: 1, excluded_debits_amount: 10, excluded_debits_count: 1, uncategorized_amount: 50, uncategorized_count: 1, merchant_coverage: { identified_amount: 250, identified_count: 2, unidentified_amount: 50, unidentified_count: 1 }, by_category: [{ category: 'alimentacion', amount: 300, count: 3 }] },
    monthly: [{ month: '2026-01', amount: 300, count: 3, by_category: [{ category: 'alimentacion', amount: 300, count: 3 }], absolute_change: null, percentage_change: null }],
    top_merchants: [{ merchant_name: 'Market', amount: 250, count: 2 }],
    recurrence_candidates: [{ merchant_name: 'Video', cadence: 'monthly', dates: ['2026-01-01', '2026-01-15', '2026-01-30'], amounts: [10, 10, 10], count: 3, minimum_amount: 10, average_amount: 10, maximum_amount: 10 }],
    insights: [{ kind: 'data_quality_warning', priority: 1, title: 'Cobertura de clasificación limitada', body: 'El análisis incluye gasto sin categoría.', evidence: [{ label: 'monto_sin_categoria', value: 50 }], caveat: 'Las categorías no representan necesariamente todo el gasto.' }],
  }

  it('renders metrics, limitations, evidence, merchants, and recurrence candidates', () => {
    render(<Dashboard analysis={analysis} />)

    expect(screen.getByText('Hallazgos del período')).toBeInTheDocument()
    expect(screen.getByText(/Cobertura de clasificación limitada/)).toBeInTheDocument()
    expect(screen.getByText('Cobertura temporal')).toBeInTheDocument()
    expect(screen.getByText('Comercios principales')).toBeInTheDocument()
    expect(screen.getByText('Candidatos de recurrencia')).toBeInTheDocument()
    expect(screen.getByText(/no confirma una suscripción/i)).toBeInTheDocument()
  })

  it('renders explicit empty states for optional insights, merchants, and recurrence candidates', () => {
    render(<Dashboard analysis={{ ...analysis, top_merchants: [], recurrence_candidates: [], insights: [] }} />)

    expect(screen.getByText('No hay hallazgos adicionales para este período.')).toBeInTheDocument()
    expect(screen.getByText('No hay comercios identificados para mostrar.')).toBeInTheDocument()
    expect(screen.getByText('No hay candidatos de recurrencia para mostrar.')).toBeInTheDocument()
  })
})
