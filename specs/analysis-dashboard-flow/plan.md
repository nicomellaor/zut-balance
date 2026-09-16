# Plan técnico: flujo y jerarquía del dashboard de análisis

## Enfoque técnico

La SPA consumirá el catálogo de la fase 12 y reemplazará el estado compartido de
cartola ancla por una consulta de cuenta: `accountId`, `from` y `to`. El análisis
se ejecutará automáticamente mediante un efecto cancelable cuando esa consulta
sea válida. Un identificador estable de solicitud y `AbortController` impedirán
que respuestas antiguas o desmontajes actualicen el dashboard.

El dashboard conservará sus componentes y datos, pero cambiará el orden de
composición. Resumen y gráficos se renderizarán primero; señales y cobertura se
agruparán en una fila compacta; tablas y detalles permanecerán después como
evidencia accesible. No se añadirán dependencias ni se modificarán cálculos.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `frontend/src/api.ts` | Añadir `AccountMetadata`, `listAccounts()`, `scope.account_id`, análisis por `account_id` y soporte de `AbortSignal`. |
| `frontend/src/App.tsx` | Reemplazar estado ancla, selector y submit; implementar catálogo, autoselección, consulta automática, cancelación, estados y nueva jerarquía del dashboard. |
| `frontend/src/App.test.tsx` | Probar selector, autoselección, solicitudes, estados, carreras y orden de secciones. |
| `frontend/src/api.test.ts` | Probar catálogo y query por `account_id`, fechas opcionales y signal. |
| `frontend/e2e/dashboard.spec.ts` | Adaptar flujo a selector de cuenta y análisis automático; comprobar orden y responsive. |
| `specs/frontend-visual-refresh/` | Mantener como historia completada; esta fase documenta explícitamente los requisitos que reemplaza. |
| `README.md` | Actualizar el flujo de uso web cuando la fase quede completa. |
| `docs/roadmap.md` | Actualizar estado de la fase tras verificación. |

## Modelos e interfaces

### Cliente API

```ts
type AccountMetadata = {
  account_id: string
  bank: string
  product: string
  currency: string | null
  masked_account_number: string | null
  identity_status: 'visible_mask' | 'ambiguous'
  statement_count: number
  period_start: string
  period_end: string
}

type AnalysisQuery = {
  accountId: string | null
  from: string
  to: string
}
```

`Analysis.scope` añadirá `account_id`. `api.getAnalysis()` recibirá
`accountId`, fechas opcionales y un `AbortSignal` opcional. `request()` combinará
el signal con el resto de `RequestInit` sin convertir una cancelación en
`ApiError`.

### Estado de aplicación

`App` mantendrá `analysisQuery`, `analysis`, `lastSuccessfulAnalysisKey` y un
`analysisDataVersion` porque la selección y validez del resultado deben
sobrevivir al cambio temporal de tab. La clave combinará cuenta, fechas y versión
de datos. `AnalysisView` mantendrá estados efímeros de catálogo, carga y error.
Así se evita repetir una consulta vigente al remontar sin impedir recálculos tras
cambios de datos.

Una carga o eliminación exitosa incrementará `analysisDataVersion`, limpiará
`analysis` y `lastSuccessfulAnalysisKey`. Cambiar cuenta o fechas también
invalidará ambos antes de consultar. Un `401` limpiará consulta, resultado, clave
y versión junto con la sesión.

Cuando se borra una cartola, el resultado se invalida, pero `accountId` no se
limpia de forma anticipada. Al volver a cargar el catálogo:

- si la cuenta aún existe, se conserva y se recalcula;
- si ya no existe, se limpia selección y resultado;
- si queda una única cuenta distinta, se autoselecciona según la regla general.

## Flujo de catálogo y selección

Al montar `AnalysisView`:

1. Mostrar estado `Cargando cuentas` y deshabilitar controles.
2. Solicitar `GET /v1/accounts` con cancelación al desmontar.
3. Si no hay cuentas, limpiar una selección inexistente y mostrar estado vacío.
4. Si hay una cuenta y no existe selección válida, seleccionarla.
5. Si hay varias, preservar solo una selección previa que continúe en catálogo;
   de otro modo, mantener placeholder sin selección.

Un fallo de catálogo mostrará un mensaje seguro y un botón `Reintentar cuentas`
controlado por un contador independiente del reintento de análisis. Durante ese
estado no se autoselecciona ni se consulta análisis.

El selector será `TextField select` o `FormControl` + `Select` de MUI con label
`Cuenta`. Las opciones usarán dos niveles visuales dentro de `MenuItem`: identidad
principal y período/cantidad como texto secundario. En selección cerrada se usará
una etiqueta compacta que no amplíe el viewport.

## Consulta automática

Un efecto observará la tupla normalizada `(accountId, from, to)`:

- sin cuenta no consulta; con rango inválido cancela la solicitud vigente, limpia
  cualquier resultado anterior y no consulta;
- con consulta idéntica a la última respuesta vigente, no repite;
- con consulta nueva, cancela la anterior, limpia resultado obsoleto y marca la
  región ocupada;
- una respuesta vigente actualiza análisis y clave exitosa;
- `AbortError` no muestra alerta;
- otros errores conservan la consulta y habilitan `Reintentar`.

El reintento incrementará un contador local de intento para ejecutar de nuevo la
misma consulta sin alterar sus parámetros. La sesión `401` seguirá limpiando todo
el estado protegido.

Los campos nativos de fecha solo producen cadenas vacías o ISO completas. Un
rango invertido mostrará `error` y `helperText` en ambos campos según corresponda.

## Jerarquía de presentación

`Dashboard` se compondrá en este orden:

1. `SummaryView` con la franja existente.
2. `ChartsView` con Evolución mensual y Categorías.
3. `AnalysisContextView` en grid 1/2 columnas con `SignalsView` y
   `CoverageView` compactos.
4. `AnalysisTablesView` con desglose por categoría y detalle mensual.
5. Grid de `MerchantView` y `RecurrenceView`.

La tabla de categorías saldrá de la tarjeta del gráfico para permitir que ambos
gráficos aparezcan antes de contexto y tablas. El gráfico seguirá relacionado
por nombre con su alternativa visible. Los estados vacíos ocuparán la misma
posición que su visualización.

### Compactación

- Señales y cobertura usarán `p: { xs: 2, sm: 2 }` y títulos `h4` visuales con
  semántica `h2` o `h3` coherente dentro del dashboard.
- Alerts conservarán icono, severidad y texto, con spacing reducido.
- Cobertura evitará repetir como encabezados destacados los KPI del resumen, pero
  mantendrá cantidades de clasificación y comercio como líneas compactas.
- Un estado textual de cobertura incompleta permanecerá visible; no se usarán
  acordeones cerrados.

## Dependencias y decisiones

- No se añaden dependencias.
- No se usa debounce para selección de cuenta; el cambio es discreto.
- Los inputs de fecha disparan al confirmar un valor completo o limpiarlo; no hay
  solicitudes por texto parcial.
- No se autoselecciona entre varias cuentas.
- No se persiste estado fuera de React.
- La cancelación se implementa con APIs web estándar y no requiere una librería
  de fetching.
- No se mantiene el botón `Actualizar análisis`; `Reintentar` aparece solo tras
  error.

## Estrategia de pruebas

- Cliente API:
  - catálogo mismo origen;
  - `account_id` codificado y ausencia de `anchor_statement_id`;
  - omisión de fechas vacías;
  - propagación de `AbortSignal`.
- Componentes:
  - loading y vacío de catálogo;
  - error y reintento independiente de catálogo;
  - autoselección de una cuenta;
  - varias cuentas sin selección automática;
  - cambio de selector dispara análisis;
  - fechas válidas vuelven a consultar;
  - rango invertido no consulta;
  - error muestra reintento;
  - una respuesta tardía no reemplaza la vigente;
  - carga y eliminación incrementan versión de datos, invalidan la clave y
    conservan o limpian selección según catálogo;
  - orden DOM de resumen, gráficos, señales, cobertura y tablas.
- E2E:
  - carga de primera cartola seguida de análisis automático;
  - selector visible y sin radios;
  - resumen y gráficos aparecen antes de contexto;
  - eliminación actualiza catálogo;
  - ausencia de overflow en Chromium y viewport móvil.
- Ejecutar lint, pruebas frontend, build, E2E y suite Python para asegurar la
  integración con el contrato de fase 12.

## Riesgos

- React Strict Mode puede ejecutar efectos dos veces en desarrollo. Cancelación y
  cleanup deben impedir solicitudes simultáneas y resultados duplicados u
  obsoletos; una primera solicitud abortada y reiniciada en desarrollo es
  aceptable.
- Mantener consulta en `App` y estados efímeros en la vista puede desalinearse si
  no se invalida al cambiar el catálogo; las pruebas de eliminación cubrirán esa
  frontera.
- Los menús MUI se renderizan en portal; etiquetas largas requieren límites de
  ancho tanto en trigger como en `MenuItem` para no producir overflow móvil.
- Mover tablas fuera de tarjetas de gráfico no debe romper nombres accesibles ni
  equivalencia de datos.
- Backend y frontend deben desplegarse juntos porque `anchor_statement_id` deja
  de existir antes de esta adaptación.
