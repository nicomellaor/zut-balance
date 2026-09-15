export type StatementMetadata = {
  statement_id: string
  bank: string
  product: string
  masked_account_number: string | null
  currency: string | null
  period_start: string
  period_end: string
  statement_number: string | null
  page_number: number | null
  total_pages: number | null
  created_at: string
}

type Classification = { category: string; merchant_name: string | null; rule_id: string | null; ruleset_version: string }
export type Transaction = { date: string; description: string; document_number: string | null; branch_or_channel: string | null; amount: number; movement_type: string; reported_balance: number | null; classification: Classification | null }
export type StatementDetail = { statement_id: string; metadata: Omit<StatementMetadata, 'statement_id' | 'created_at'>; summary: Record<string, number | null>; transactions: Transaction[] }
export type Insight = { kind: string; priority: number; title: string; body: string; evidence: { label: string; value: string | number }[]; caveat: string | null }
export type Analysis = {
  scope: { statement_ids: string[]; from: string; to: string; currency: string; ruleset_versions: string[] }
  coverage: { covered_ranges: { from: string; to: string }[]; gaps: { from: string; to: string }[]; partial_months: string[] }
  summary: { spending_amount: number; transaction_count: number; credits_amount: number; credits_count: number; excluded_debits_amount: number; excluded_debits_count: number; uncategorized_amount: number; uncategorized_count: number; merchant_coverage: { identified_amount: number; identified_count: number; unidentified_amount: number; unidentified_count: number }; by_category: { category: string; amount: number; count: number }[] }
  monthly: { month: string; amount: number; count: number; by_category: { category: string; amount: number; count: number }[]; absolute_change: number | null; percentage_change: string | null }[]
  top_merchants: { merchant_name: string | null; amount: number; count: number }[]
  recurrence_candidates: { merchant_name: string | null; cadence: string; dates: string[]; amounts: number[]; count: number; minimum_amount: number; average_amount: number; maximum_amount: number }[]
  insights: Insight[]
}

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, credentials: 'same-origin' })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null
    throw new ApiError(response.status, body?.error?.message ?? 'No se pudo completar la solicitud.')
  }
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>
}

export const api = {
  login: (password: string) => request<void>('/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) }),
  logout: () => request<void>('/v1/auth/logout', { method: 'POST' }),
  listStatements: (limit = 50, offset = 0) => request<{ statements: StatementMetadata[] }>(`/v1/statements?limit=${limit}&offset=${offset}`),
  getStatement: (id: string) => request<StatementDetail>(`/v1/statements/${id}`),
  uploadStatement: (file: File) => { const form = new FormData(); form.append('file', file); return request<StatementDetail>('/v1/statements', { method: 'POST', body: form }) },
  deleteStatement: (id: string) => request<void>(`/v1/statements/${id}`, { method: 'DELETE' }),
  getAnalysis: (ids: string[], from: string, to: string) => request<Analysis>(`/v1/analysis?${new URLSearchParams([...ids.map((id) => ['statement_id', id]), ['from', from], ['to', to]]).toString()}`),
}
