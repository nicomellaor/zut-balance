import { useEffect, useEffectEvent, useState } from 'react'
import { Alert, AppBar, Box, Button, Card, CardContent, Container, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Divider, FormControlLabel, Grid, Paper, Stack, Tab, Tabs, TextField, Toolbar, Typography } from '@mui/material'
import { BarChart, LineChart } from '@mui/x-charts'
import { ApiError, api } from './api'
import type { Analysis, StatementDetail, StatementMetadata } from './api'

const money = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 })
const dates = new Intl.DateTimeFormat('es-CL')
const formatDate = (value: string) => dates.format(new Date(`${value}T12:00:00`))

export default function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [tab, setTab] = useState(0)
  const [statements, setStatements] = useState<StatementMetadata[]>([])
  const [offset, setOffset] = useState(0)
  const [detail, setDetail] = useState<StatementDetail | null>(null)
  const [anchorStatementId, setAnchorStatementId] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)

  const clearSession = () => { setAuthenticated(false); setStatements([]); setDetail(null); setAnchorStatementId(null); setAnalysis(null) }
  const refresh = async (nextOffset = offset) => {
    try {
      const response = await api.listStatements(50, nextOffset)
      setStatements(response.statements)
      setOffset(nextOffset)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) clearSession()
      throw error
    }
  }
  const loadStatements = useEffectEvent(() => { void refresh() })
  // Synchronize the browser session with protected server state.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { if (authenticated) loadStatements() }, [authenticated])

  if (!authenticated) return <Access onAccess={() => setAuthenticated(true)} />
  return <Box sx={{ minHeight: '100vh', bgcolor: '#f6f7f5' }}>
    <AppBar position="sticky" color="inherit" elevation={0}><Toolbar><Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>Zut Balance</Typography><Button onClick={() => { void api.logout().finally(clearSession) }}>Cerrar sesión</Button></Toolbar></AppBar>
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Tabs value={tab} onChange={(_, value) => setTab(value)} aria-label="Secciones principales" sx={{ mb: 3 }}><Tab label="Cartolas" /><Tab label="Análisis" /></Tabs>
      {tab === 0 && <StatementsView statements={statements} offset={offset} detail={detail} refresh={refresh} onUnauthorized={clearSession} onDetail={setDetail} onDeleted={(id) => { setDetail(null); if (anchorStatementId === id) setAnchorStatementId(null); setAnalysis(null); void refresh() }} />}
      {tab === 1 && <AnalysisView anchorStatementId={anchorStatementId} onAnchorStatementId={setAnchorStatementId} onUnauthorized={clearSession} analysis={analysis} onAnalysis={setAnalysis} />}
    </Container>
  </Box>
}

function Access({ onAccess }: { onAccess: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await api.login(password); onAccess() } catch { setError('No fue posible iniciar sesión.') } finally { setBusy(false) }
  }
  return <Container maxWidth="sm" sx={{ pt: { xs: 10, md: 18 } }}><Paper component="form" onSubmit={submit} sx={{ p: 4 }}><Typography variant="overline" color="primary">Acceso privado</Typography><Typography variant="h3" gutterBottom>Tu balance, bajo control.</Typography><Typography color="text.secondary" sx={{ mb: 3 }}>Ingresa la contraseña del administrador para acceder a los datos.</Typography>{error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}<TextField label="Contraseña" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required fullWidth autoFocus /><Button type="submit" variant="contained" disabled={!password || busy} sx={{ mt: 3 }} fullWidth>{busy ? 'Verificando...' : 'Iniciar sesión'}</Button></Paper></Container>
}

function StatementsView({ statements, offset, detail, refresh, onUnauthorized, onDetail, onDeleted }: { statements: StatementMetadata[]; offset: number; detail: StatementDetail | null; refresh: (offset?: number) => Promise<void>; onUnauthorized: () => void; onDetail: (detail: StatementDetail | null) => void; onDeleted: (id: string) => void }) {
  const [uploading, setUploading] = useState(false); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [confirm, setConfirm] = useState(false)
  const handle = (caught: unknown, fallback: string) => { if (caught instanceof ApiError && caught.status === 401) onUnauthorized(); else setError(caught instanceof ApiError ? caught.message : fallback) }
  const upload = async (file: File | undefined) => { if (!file || uploading) return; setUploading(true); setError(''); try { const stored = await api.uploadStatement(file); await refresh(); onDetail(stored); setMessage('La cartola está disponible para revisión.') } catch (caught) { handle(caught, 'No se pudo cargar la cartola.') } finally { setUploading(false) } }
  const open = async (id: string) => { setError(''); try { onDetail(await api.getStatement(id)) } catch (caught) { handle(caught, 'No se pudo abrir la cartola.') } }
  const remove = async () => { if (!detail) return; try { await api.deleteStatement(detail.statement_id); onDeleted(detail.statement_id); setConfirm(false); setMessage('La cartola se eliminó permanentemente.') } catch (caught) { handle(caught, 'No se pudo eliminar la cartola.') } }
  const dialog = <Dialog open={confirm} onClose={() => setConfirm(false)}><DialogTitle>¿Eliminar cartola?</DialogTitle><DialogContent><DialogContentText>Se eliminarán permanentemente la cartola, sus movimientos y clasificaciones.</DialogContentText></DialogContent><DialogActions><Button onClick={() => setConfirm(false)}>Cancelar</Button><Button color="error" onClick={() => void remove()}>Eliminar</Button></DialogActions></Dialog>
  if (detail) return <><StatementDetailView detail={detail} onBack={() => onDetail(null)} onDelete={() => setConfirm(true)} />{dialog}</>
  return <Stack spacing={3}><Card><CardContent><Typography variant="h5">Carga una cartola</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Un PDF, hasta 10 MiB y 20 páginas.</Typography><Button component="label" variant="contained" disabled={uploading}>{uploading ? 'Procesando...' : 'Seleccionar PDF'}<input hidden type="file" accept="application/pdf" onChange={(event) => upload(event.target.files?.[0])} /></Button></CardContent></Card>{message && <Alert severity="success">{message}</Alert>}{error && <Alert severity="error">{error}</Alert>}<Paper sx={{ p: 2 }}><Typography variant="h5" sx={{ mb: 2 }}>Historial</Typography>{statements.length === 0 ? <Typography color="text.secondary">Aún no hay cartolas cargadas.</Typography> : <Stack divider={<Divider />}>{statements.map((item) => <Grid container key={item.statement_id} sx={{ py: 1, alignItems: 'center' }}><Grid size={{ xs: 6, md: 3 }}>{formatDate(item.period_start)} - {formatDate(item.period_end)}</Grid><Grid size={{ xs: 6, md: 3 }}>{item.bank}<br /><Typography variant="caption">{item.product}</Typography></Grid><Grid size={{ xs: 6, md: 3 }}>{item.masked_account_number ?? 'No informada'}</Grid><Grid size={{ xs: 6, md: 3 }}><Button onClick={() => void open(item.statement_id)}>Ver detalle</Button></Grid></Grid>)}</Stack>}<Stack direction="row" sx={{ mt: 2, justifyContent: 'space-between' }}><Button disabled={offset === 0} onClick={() => void refresh(Math.max(0, offset - 50))}>Anterior</Button><Button disabled={statements.length < 50} onClick={() => void refresh(offset + 50)}>Siguiente</Button></Stack></Paper>{dialog}</Stack>
}

function StatementDetailView({ detail, onBack, onDelete }: { detail: StatementDetail; onBack: () => void; onDelete: () => void }) { return <Stack spacing={3}><Stack direction="row" sx={{ justifyContent: 'space-between' }}><Button onClick={onBack}>Volver al historial</Button><Button color="error" onClick={onDelete}>Eliminar</Button></Stack><Paper sx={{ p: 3 }}><Typography variant="h4">{detail.metadata.bank}</Typography><Typography color="text.secondary">{detail.metadata.product} · {detail.metadata.masked_account_number ?? 'Cuenta no informada'} · {formatDate(detail.metadata.period_start)} a {formatDate(detail.metadata.period_end)}</Typography></Paper><Paper sx={{ p: 2, overflowX: 'auto' }}><Typography variant="h5" sx={{ mb: 2 }}>Movimientos</Typography><Box component="table" className="data-table"><thead><tr><th>Fecha</th><th>Descripción</th><th>Referencia / canal</th><th>Monto</th><th>Tipo</th><th>Categoría</th><th>Comercio</th></tr></thead><tbody>{detail.transactions.map((item, index) => <tr key={`${item.date}-${index}`}><td>{formatDate(item.date)}</td><td>{item.description}</td><td>{item.document_number ?? item.branch_or_channel ?? '—'}</td><td>{money.format(item.amount)}</td><td>{item.movement_type}</td><td>{item.classification?.category ?? 'sin categoría'}</td><td>{item.classification?.merchant_name ?? '—'}</td></tr>)}</tbody></Box></Paper></Stack> }

function AnalysisView({ anchorStatementId, onAnchorStatementId, onUnauthorized, analysis, onAnalysis }: { anchorStatementId: string | null; onAnchorStatementId: (value: string | null) => void; onUnauthorized: () => void; analysis: Analysis | null; onAnalysis: (value: Analysis | null) => void }) {
  const [catalog, setCatalog] = useState<StatementMetadata[]>([]); const [from, setFrom] = useState(''); const [to, setTo] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const loadCatalog = useEffectEvent(() => { void api.listStatements(100, 0).then((response) => setCatalog(response.statements)).catch((caught: unknown) => { if (caught instanceof ApiError && caught.status === 401) onUnauthorized(); else setError('No se pudo cargar el catálogo de cartolas.') }) })
  useEffect(() => { loadCatalog() }, [])
  const rangeValid = (!from || !to) || from <= to
  const submit = async () => { if (!anchorStatementId || !rangeValid) return; setBusy(true); setError(''); try { onAnalysis(await api.getAnalysis(anchorStatementId, from || undefined, to || undefined)) } catch (caught) { if (caught instanceof ApiError && caught.status === 401) onUnauthorized(); else setError(caught instanceof ApiError ? caught.message : 'No se pudo calcular el análisis.') } finally { setBusy(false) } }
  return <Stack spacing={3}><Paper sx={{ p: 3 }}><Typography variant="h4">Explora tu gasto</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Elige una cartola ancla. El análisis incorpora automáticamente su historial compatible.</Typography>{catalog.length === 0 ? <Alert severity="info">Carga una cartola para comenzar el análisis.</Alert> : <Stack spacing={1}>{catalog.map((item) => <FormControlLabel key={item.statement_id} control={<input type="radio" checked={anchorStatementId === item.statement_id} onChange={() => { onAnchorStatementId(item.statement_id); onAnalysis(null) }} />} label={`${item.product} · ${item.masked_account_number ?? 'cuenta no informada'} · ${item.period_start} a ${item.period_end}`} />)}</Stack>}<Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 3 }}><TextField label="Desde" type="date" value={from} onChange={(event) => setFrom(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /><TextField label="Hasta" type="date" value={to} onChange={(event) => setTo(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /><Button variant="contained" onClick={() => void submit()} disabled={!anchorStatementId || !rangeValid || busy}>{busy ? 'Calculando...' : 'Actualizar análisis'}</Button></Stack>{error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}</Paper>{analysis && <Dashboard analysis={analysis} />}</Stack>
}

export function Dashboard({ analysis }: { analysis: Analysis }) {
  const { summary } = analysis
  return <Stack spacing={3}>
    <SignalsView analysis={analysis} />
    <Grid container spacing={2}>{[
      ['Gasto', summary.spending_amount, summary.transaction_count],
      ['Créditos', summary.credits_amount, summary.credits_count],
      ['Débitos excluidos', summary.excluded_debits_amount, summary.excluded_debits_count],
      ['Sin categoría', summary.uncategorized_amount, summary.uncategorized_count],
    ].map(([label, amount, count]) => <Grid key={label as string} size={{ xs: 12, sm: 6, md: 3 }}><Paper sx={{ p: 2 }}><Typography variant="caption">{label}</Typography><Typography variant="h5">{money.format(amount as number)}</Typography><Typography variant="body2" color="text.secondary">{count} movimientos</Typography></Paper></Grid>)}</Grid>
    <CoverageView analysis={analysis} />
    <Paper sx={{ p: 2 }}><Typography variant="h6">Cobertura de clasificación</Typography><Typography>Gasto de consumo: {money.format(summary.spending_amount)} ({summary.transaction_count} movimientos)</Typography><Typography>Sin categoría: {money.format(summary.uncategorized_amount)} ({summary.uncategorized_count} movimientos)</Typography><Typography sx={{ mt: 1 }}>Comercios identificados: {money.format(summary.merchant_coverage.identified_amount)} ({summary.merchant_coverage.identified_count} movimientos)</Typography><Typography>Sin comercio identificado: {money.format(summary.merchant_coverage.unidentified_amount)} ({summary.merchant_coverage.unidentified_count} movimientos)</Typography></Paper>
    <Grid container spacing={3}><Grid size={{ xs: 12, md: 7 }}><Paper sx={{ p: 2 }}><Typography variant="h6">Evolución mensual</Typography><LineChart height={280} xAxis={[{ data: analysis.monthly.map((item) => item.month), scaleType: 'point' }]} series={[{ data: analysis.monthly.map((item) => item.amount), label: 'Gasto CLP' }]} /></Paper></Grid><Grid size={{ xs: 12, md: 5 }}><Paper sx={{ p: 2, overflowX: 'auto' }}><Typography variant="h6">Categorías</Typography>{summary.by_category.length === 0 ? <Typography color="text.secondary">No hay gasto categorizado para mostrar.</Typography> : <><BarChart height={280} xAxis={[{ data: summary.by_category.map((item) => item.category), scaleType: 'band' }]} series={[{ data: summary.by_category.map((item) => item.amount), label: 'CLP' }]} /><Box component="table" className="data-table"><thead><tr><th>Categoría</th><th>Monto</th><th>Movimientos</th></tr></thead><tbody>{summary.by_category.map((category) => <tr key={category.category}><td>{category.category}</td><td>{money.format(category.amount)}</td><td>{category.count}</td></tr>)}</tbody></Box></>}</Paper></Grid></Grid>
    <Paper sx={{ p: 2, overflowX: 'auto' }}><Typography variant="h6">Detalle mensual</Typography><Box component="table" className="data-table"><thead><tr><th>Mes</th><th>Gasto</th><th>Movimientos</th><th>Cambio absoluto</th><th>Variación</th></tr></thead><tbody>{analysis.monthly.map((item) => <tr key={item.month}><td>{item.month}</td><td>{money.format(item.amount)}</td><td>{item.count}</td><td>{item.absolute_change === null ? 'No disponible' : money.format(item.absolute_change)}</td><td>{item.percentage_change === null ? 'No disponible' : `${item.percentage_change}%`}</td></tr>)}</tbody></Box></Paper>
    <Grid container spacing={3}><Grid size={{ xs: 12, md: 6 }}><MerchantView merchants={analysis.top_merchants} /></Grid><Grid size={{ xs: 12, md: 6 }}><RecurrenceView candidates={analysis.recurrence_candidates} /></Grid></Grid>
  </Stack>
}

function SignalsView({ analysis }: { analysis: Analysis }) { const highlight = analysis.highlights.largest_monthly_change; return <Paper sx={{ p: 2 }}><Typography variant="h5" gutterBottom>Avisos y destacados</Typography>{analysis.notices.length === 0 && !highlight && <Typography color="text.secondary">No hay avisos ni variaciones destacadas para este período.</Typography>}<Stack spacing={2}>{analysis.notices.map((notice) => notice.kind === 'incomplete_coverage' ? <Alert key={notice.kind} severity={notice.severity}><Typography variant="subtitle2">Cobertura incompleta</Typography>{notice.gaps.map((gap) => <Typography key={`${gap.from}-${gap.to}`} variant="body2">Hueco: {formatDate(gap.from)} a {formatDate(gap.to)}</Typography>)}{notice.partial_months.length > 0 && <Typography variant="body2">Meses parciales: {notice.partial_months.join(', ')}.</Typography>}</Alert> : <Alert key={notice.kind} severity={notice.severity}><Typography variant="subtitle2">Clasificación limitada</Typography><Typography variant="body2">Sin categoría: {money.format(notice.uncategorized_amount)} ({notice.uncategorized_count} movimientos).</Typography><Typography variant="body2">Sin comercio identificado: {money.format(notice.unidentified_merchant_amount)} ({notice.unidentified_merchant_count} movimientos).</Typography>{notice.ruleset_versions.length > 1 && <Typography variant="body2">Versiones de reglas: {notice.ruleset_versions.join(', ')}.</Typography>}</Alert>)}{highlight && <Alert severity="info"><Typography variant="subtitle2">Mayor variación mensual</Typography><Typography variant="body2">{highlight.previous_month} a {highlight.current_month}: {money.format(highlight.absolute_change)} ({highlight.percentage_change === null ? 'sin porcentaje comparable' : `${highlight.percentage_change}%`}).</Typography></Alert>}</Stack></Paper> }

function CoverageView({ analysis }: { analysis: Analysis }) { const { coverage } = analysis; return <Paper sx={{ p: 2 }}><Typography variant="h6">Cobertura temporal</Typography><Typography variant="subtitle2" sx={{ mt: 1 }}>Rangos cubiertos</Typography>{coverage.covered_ranges.length ? coverage.covered_ranges.map((range) => <Typography key={`${range.from}-${range.to}`}>{formatDate(range.from)} a {formatDate(range.to)}</Typography>) : <Typography color="text.secondary">No hay rangos cubiertos.</Typography>}<Typography variant="subtitle2" sx={{ mt: 1 }}>Huecos</Typography>{coverage.gaps.length ? coverage.gaps.map((range) => <Typography key={`${range.from}-${range.to}`}>{formatDate(range.from)} a {formatDate(range.to)}</Typography>) : <Typography color="text.secondary">No hay huecos informados.</Typography>}{coverage.partial_months.length > 0 && <Alert severity="warning" sx={{ mt: 2 }}>Meses con cobertura parcial: {coverage.partial_months.join(', ')}.</Alert>}</Paper> }

function MerchantView({ merchants }: { merchants: Analysis['top_merchants'] }) { return <Paper sx={{ p: 2, height: '100%' }}><Typography variant="h6">Comercios principales</Typography><Typography variant="body2" color="text.secondary">Solo considera comercios identificados.</Typography>{merchants.length ? <Box component="table" className="data-table"><thead><tr><th>Comercio</th><th>Monto</th><th>Movimientos</th></tr></thead><tbody>{merchants.map((merchant, index) => <tr key={`${merchant.merchant_name}-${index}`}><td>{merchant.merchant_name ?? 'No informado'}</td><td>{money.format(merchant.amount)}</td><td>{merchant.count}</td></tr>)}</tbody></Box> : <Typography color="text.secondary" sx={{ mt: 2 }}>No hay comercios identificados para mostrar.</Typography>}</Paper> }

function RecurrenceView({ candidates }: { candidates: Analysis['recurrence_candidates'] }) { return <Paper sx={{ p: 2, height: '100%' }}><Typography variant="h6">Candidatos de recurrencia</Typography>{candidates.length ? <Stack spacing={2} sx={{ mt: 1 }}>{candidates.map((candidate, index) => <Box key={`${candidate.merchant_name}-${index}`}><Typography sx={{ fontWeight: 700 }}>{candidate.merchant_name ?? 'Comercio no informado'} · {candidate.cadence}</Typography><Typography variant="body2">{candidate.count} ocurrencias entre {formatDate(candidate.dates[0])} y {formatDate(candidate.dates.at(-1) ?? candidate.dates[0])}.</Typography><Typography variant="body2">Mínimo {money.format(candidate.minimum_amount)} · promedio {money.format(candidate.average_amount)} · máximo {money.format(candidate.maximum_amount)}</Typography><Typography variant="caption">Candidato basado en fechas observadas; no confirma una suscripción.</Typography></Box>)}</Stack> : <Typography color="text.secondary" sx={{ mt: 2 }}>No hay candidatos de recurrencia para mostrar.</Typography>}</Paper> }
