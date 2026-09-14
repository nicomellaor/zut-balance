# Plan técnico: interfaz web local

## Enfoque técnico

Se añadirá una SPA React creada con Vite en `frontend/`, separada del paquete
Python pero versionada en el mismo repositorio. Material UI proveerá estructura,
formularios, tabla, diálogo y estados; MUI X Charts presentará evolución y
desglose sin que la SPA recalcule datos financieros.

La aplicación mantendrá la API key exclusivamente en estado de memoria del árbol
React. Un cliente HTTP central añadirá el encabezado Bearer a la URL base pública
de la API. Al recibir `401`, se limpiará la sesión local y se mostrará el acceso.
La URL base no contiene secretos; se configurará para desarrollo mediante
variables de Vite y se documentará con un archivo de ejemplo sin secretos.

FastAPI añadirá una configuración de CORS por variable de entorno que acepte una
lista explícita de orígenes. Por defecto no se permitirá un origen externo. No
se cambia autenticación, SQLite ni los contratos de cartolas y análisis.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `frontend/` | Crear proyecto React/Vite, scripts propios, configuración TypeScript y archivo de ejemplo de entorno. |
| `frontend/src/app/` | Composición de rutas, tema `es-CL`, sesión en memoria y estados globales mínimos. |
| `frontend/src/api/` | Cliente tipado para rutas existentes, errores seguros y encabezado Bearer. |
| `frontend/src/features/access/` | Pantalla de API key y cierre de sesión. |
| `frontend/src/features/statements/` | Carga, historial paginado, detalle de movimientos y diálogo de borrado. |
| `frontend/src/features/analysis/` | Selector/asistente, métricas, tablas y gráficos accesibles. |
| `frontend/src/**/*.test.tsx` | Pruebas unitarias con Vitest, Testing Library y respuestas API simuladas. |
| `frontend/e2e/` | Flujos Playwright contra backend temporal configurado para pruebas. |
| `src/zut_balance/api.py` | CORS con orígenes configurables y sin wildcard. |
| `tests/test_api.py` | Validar CORS configurado y ausencia de wildcard. |
| `frontend/README.md` y `README.md` | Documentar instalación, ejecución, build, pruebas y arranque coordinado. |

## Modelo e interfaces

### Estado de sesión

- `apiKey: string | null` existe solo en memoria React.
- `setApiKey` permite acceso tras validación por una solicitud autenticada.
- `clearSession` borra la clave y cualquier estado de detalle o análisis al
  recibir `401` o al cerrar sesión de forma explícita.
- No se usa almacenamiento web ni router state para transportar la clave.

### Cliente API

- `listStatements(limit, offset)`, `getStatement(id)`, `uploadStatement(file)`,
  `deleteStatement(id)` y `getAnalysis(statementIds, from, to)` reflejan los
  contratos actuales.
- Errores transportan únicamente `status` y el código/mensaje seguro de la API.
- El cliente no registra cuerpos de respuesta ni encabezados.

### Navegación y vistas

- Acceso local: clave y explicación de uso efímero.
- Cartolas: carga, historial y controles de paginación.
- Detalle: retorno al historial, metadatos, resumen, movimientos y borrado.
- Análisis: selección, rango propuesto, resumen, cobertura, tablas y gráficos.

El estado local se mantiene junto a cada vista. Solo la sesión y la selección de
análisis se comparten; no se introduce un gestor global externo.

### CORS

Se añadirá `ZUT_BALANCE_CORS_ORIGINS` como lista separada por comas de orígenes
completos. El backend normaliza valores no vacíos y configura `CORSMiddleware`
sin comodines ni credenciales. Desarrollo documentará explícitamente el origen
Vite; producción debe proporcionar su origen final.

## Decisiones técnicas

- TypeScript se usará con configuración estricta para representar los contratos
  JSON de la API, sin generar tipos desde OpenAPI en esta fase.
- `Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP" })` y
  `Intl.DateTimeFormat("es-CL")` formatearán valores de presentación.
- Los movimientos se muestran en una tabla MUI con cabeceras semánticas; móvil
  usa contenedor horizontal accesible en vez de ocultar campos financieros.
- El selector deriva compatibilidad y rango unión del metadato de historial para
  orientar al usuario, pero nunca suprime la validación del backend.
- Las respuestas de análisis alimentan directamente KPIs, tablas y MUI X Charts.
  Los datos tabulares equivalentes permanecen visibles para acceso sin gráfico.
- Borrar una cartola invalida detalle, historial, selección y resultado de
  análisis en el estado de la SPA; no se conserva una caché persistente.
- La carga muestra estado indeterminado porque el contrato HTTP actual no ofrece
  progreso de bytes ni indicador de deduplicación.
- Playwright levantará frontend y backend de prueba con SQLite temporal y un
  origen CORS explícito. Los datos E2E serán sintéticos o anonimizados.

## Estrategia de pruebas

- Unitarias: sesión efímera, cliente API, formatters, formularios, paginación,
  selección, rango unión, estados vacío/carga/error y confirmación de borrado.
- Unitarias: presentación de métricas, valores nulos, cobertura parcial,
  recurrencias y alternativa tabular de gráficos.
- Backend: CORS sin variable, con un origen y con valores vacíos; comprobar que
  no se emite wildcard.
- E2E: acceso, carga de fixture permitido, historial, detalle con clasificación,
  selección, consulta de análisis, borrado y retorno a acceso tras `401`.
- E2E responsive y teclado: navegación de controles, diálogo con foco y una
  viewport móvil representativa.
- Ejecutar suite Python, pruebas frontend, build Vite y E2E antes de Verify.

## Riesgos y despliegue

- La clave en memoria es apta solo para el escenario local de confianza. No
  resuelve identidad ni aislamiento multiusuario; una futura sesión de servidor
  será una fase separada.
- Un origen CORS mal configurado impedirá acceso desde la SPA, de forma segura.
  La documentación debe incluir ejemplos de desarrollo y no sugerir wildcard.
- Agregar React, MUI, MUI X Charts y Playwright aumenta superficie de
  dependencias; sus lockfiles se versionarán y `node_modules` se ignorará.
- La API de historial no permite filtrar ni seleccionar por cuenta en servidor;
  la interfaz debe gestionar listas vacías y límites actuales sin inventar datos.
- No se crea repositorio ni sesión nueva. Si se continúa en otra sesión, se debe
  leer `AGENTS.md` y `specs/interface/{spec,plan,tasks}.md` antes de editar.
