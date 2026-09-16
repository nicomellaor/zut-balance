# Flujo y jerarquía del dashboard de análisis

## Objetivo

Reducir la fricción para consultar análisis y priorizar visualmente sus
resultados principales. La vista debe seleccionar cuentas en lugar de cartolas,
cargar automáticamente el análisis cuando el ámbito sea inequívoco y presentar
primero el resumen financiero y los gráficos, dejando avisos y cobertura en una
sección secundaria compacta pero visible.

## Contexto

La interfaz actual muestra una opción de radio por cartola, requiere pulsar
`Actualizar análisis` y coloca avisos y cobertura antes de los gráficos. Al
acumular varias cartolas de una cuenta, el selector repite opciones equivalentes
y ocupa espacio sin aportar una decisión distinta.

La fase `account-scoped-analysis` añade un catálogo deduplicado y reemplaza el
contrato de cartola ancla por `account_id`. Esta fase adapta la SPA después de
que ese contrato esté disponible.

Esta especificación reemplaza los requisitos de grupo de radio y prioridad de
avisos de `specs/frontend-visual-refresh/`, además de la adaptación mínima por
cartola ancla descrita en `specs/analysis-signals/`. Conserva el sistema visual,
responsive, accesibilidad y alternativas tabulares ya aprobados.

## Alcance

- Consumir el catálogo autenticado de ámbitos de cuenta.
- Reemplazar el grupo de radios por un selector MUI compacto y accesible.
- Autoseleccionar una cuenta solo cuando el catálogo contiene exactamente una
  opción.
- Solicitar automáticamente el análisis al seleccionar una cuenta.
- Actualizar automáticamente resultados cuando cambie un filtro de fecha
  completo y válido.
- Evitar que respuestas antiguas reemplacen el resultado de una selección más
  reciente.
- Mostrar estados diferenciados de carga de catálogo, carga de análisis, vacío,
  error y éxito.
- Reordenar el dashboard para mostrar resumen y gráficos antes que avisos y
  cobertura.
- Compactar avisos y cobertura sin ocultar límites de interpretación ni omitir
  campos recibidos.
- Mantener visibles las alternativas tabulares de los gráficos.
- Actualizar pruebas unitarias y E2E del flujo automático, orden visual y
  responsive.

## Fuera de alcance

- Implementar o conservar selección por cartola ancla.
- Elegir automáticamente una cuenta cuando hay varias opciones.
- Modificar el catálogo, contratos o cálculos definidos por
  `account-scoped-analysis`.
- Persistir la cuenta seleccionada, fechas o resultados en almacenamiento web.
- Añadir rutas, filtros avanzados, búsqueda de movimientos o edición de cuentas.
- Ocultar avisos críticos en un acordeón cerrado o eliminar alternativas
  tabulares accesibles.
- Recalcular métricas, cobertura, señales, comercios o recurrencias en la SPA.
- Cambiar el diseño de carga, historial o detalle de cartolas salvo lo necesario
  para refrescar el catálogo tras cargas y eliminaciones.

## Requisitos funcionales

### RF-01: Catálogo y selector de cuenta

La vista debe solicitar `GET /v1/accounts` al entrar a Análisis y presentar una
opción por ámbito mediante un selector MUI con nombre accesible `Cuenta`.

Cada opción debe mostrar banco, producto, cuenta enmascarada o estado no
informado, cantidad de cartolas y período total. Las etiquetas largas deben ser
legibles sin ensanchar el viewport; el valor completo debe permanecer disponible
para tecnologías asistivas.

Mientras carga el catálogo, el selector permanece deshabilitado y se anuncia
`Cargando cuentas`. Un catálogo vacío muestra una invitación a cargar una
cartola y no solicita análisis.

### RF-02: Selección automática

Si el catálogo contiene exactamente una cuenta, la SPA debe seleccionarla y
solicitar su análisis completo sin intervención adicional. El catálogo no
garantiza que el historial completo supere validaciones de moneda o solapamiento;
si el análisis lo rechaza, la cuenta permanece seleccionada y se muestra el
error seguro con opción de reintento o ajuste de fechas.

Si contiene más de una, ninguna se selecciona automáticamente y el usuario debe
elegir una. No se permite inferir preferencia por orden, fecha de carga, período
reciente, cantidad de cartolas ni posición en el catálogo.

Seleccionar manualmente una cuenta debe solicitar de inmediato su análisis y
retirar de pantalla cualquier resultado perteneciente a una cuenta anterior.

### RF-03: Filtros de fecha automáticos

Las fechas `Desde` y `Hasta` continúan siendo opcionales. Seleccionar una cuenta
sin fechas consulta todo su historial. Al establecer, modificar o limpiar una
fecha con un rango válido, la SPA debe solicitar nuevamente el análisis.

Si ambas fechas existen y `Desde` es posterior a `Hasta`, los campos muestran un
error claro, no se realiza una solicitud y no se presenta un resultado como si
correspondiera al rango inválido.

No debe existir un botón obligatorio `Actualizar análisis`. Después de un error,
la interfaz debe ofrecer `Reintentar` sin perder cuenta ni fechas.

### RF-04: Consistencia de solicitudes

Solo la respuesta de la solicitud vigente puede actualizar el dashboard. Al
cambiar cuenta o fechas, la SPA debe cancelar o invalidar solicitudes anteriores.
Salir de la vista o cerrar sesión también debe impedir actualizaciones tardías.

Mientras se calcula, la región de resultados debe comunicar estado ocupado y no
mostrar como vigente el dashboard de otra cuenta o rango. Al completar, debe
anunciar que el análisis está disponible sin mover el foco inesperadamente.

### RF-05: Jerarquía del dashboard

Un resultado exitoso debe presentar sus secciones en este orden observable:

1. resumen del período;
2. gráficos de evolución mensual y categorías;
3. avisos/highlight y cobertura en formato compacto;
4. alternativas tabulares y detalle mensual;
5. comercios principales y candidatos de recurrencia.

El resumen y los gráficos deben ocupar la mayor jerarquía y superficie inicial.
El cambio de orden no puede omitir valores, alterar cálculos ni eliminar estados
vacíos.

### RF-06: Avisos y cobertura compactos

Avisos y cobertura deben compartir una fila de dos columnas en escritorio y
apilarse en móvil. Deben usar menor padding y jerarquía tipográfica que el
resumen y los gráficos.

Los avisos conservan severidad y contenido. La cobertura conserva rangos,
huecos, meses parciales y calidad de clasificación, pero puede evitar repetir
como bloques destacados los montos ya visibles en el resumen. Cuando exista
cobertura incompleta, debe permanecer una señal textual visible cerca de la
región principal o dentro de la sección compacta sin depender solo del color.

### RF-07: Actualización tras carga y eliminación

Después de cargar o eliminar una cartola, la próxima entrada a Análisis debe
usar el catálogo actualizado. Si se elimina una cartola y la cuenta seleccionada
continúa existiendo, la selección puede conservarse y su análisis debe
invalidarse. Si desaparece la última cartola de la cuenta, se limpia selección y
resultado.

## Requisitos no funcionales

### RNF-01: Accesibilidad

El selector debe ser operable con teclado y lector de pantalla. Los estados de
carga y actualización deben anunciarse mediante semántica de estado o región
viva sin producir anuncios repetitivos. Gráficos y tablas conservan nombres y
asociación comprensibles.

### RNF-02: Responsive

El selector, fechas, resumen, gráficos y secciones compactas deben funcionar
desde 320 px. Menús y etiquetas no pueden ampliar el documento. Los gráficos y
tablas mantienen `min-width: 0` y desplazamiento contenido cuando corresponda.

### RNF-03: Privacidad y estado

`account_id`, fechas y resultados permanecen en memoria. No se guardan en
`localStorage`, `sessionStorage`, la URL navegable del frontend, logs generados
por la SPA ni telemetría. El `account_id` sí forma parte de la query autenticada
al backend y puede aparecer en sus logs de acceso como identificador opaco. Los
errores muestran únicamente mensajes seguros de la API.

### RNF-04: Rendimiento y solicitudes

La SPA no debe mantener solicitudes duplicadas activas ni confirmar resultados
duplicados por remontaje, Strict Mode o cambios que no alteran cuenta ni fechas.
Una solicitud iniciada y abortada durante la comprobación de desarrollo de
Strict Mode es aceptable. Una interacción rápida cancela solicitudes, y solo el
último ámbito válido produce renderizado.

## Criterios de aceptación

- **CA-01:** Una cuenta única se autoselecciona y renderiza análisis sin pulsar
  un botón; varias cuentas esperan una selección explícita.
- **CA-02:** El selector muestra una opción por cuenta del catálogo, no una por
  cartola, y conserva nombre accesible y operación por teclado.
- **CA-03:** Cambiar cuenta limpia el resultado anterior y solo la respuesta más
  reciente puede poblar el dashboard.
- **CA-04:** Fechas válidas actualizan automáticamente; un rango invertido muestra
  error y no llama a análisis.
- **CA-05:** En el DOM y visualmente, Resumen del período y ambos gráficos
  preceden a Avisos y destacados y Cobertura y clasificación.
- **CA-06:** Avisos y cobertura ocupan dos columnas compactas en escritorio y una
  columna en móvil, sin perder datos ni severidad.
- **CA-07:** Las tablas equivalentes, detalle mensual, comercios y recurrencias
  continúan disponibles después de las secciones compactas.
- **CA-08:** Carga de catálogo, carga de análisis, vacío, error con reintento y
  éxito tienen estados explícitos y accesibles.
- **CA-09:** La vista no genera overflow horizontal en móvil o escritorio y no
  persiste selección ni resultados en almacenamiento web.
- **CA-10:** Pruebas unitarias y E2E cubren catálogo vacío, una cuenta, varias
  cuentas, consulta automática, respuesta obsoleta, rango inválido, orden del
  dashboard y actualización tras eliminación.

## Casos límite

- Catálogo vacío, una cuenta y varias cuentas.
- Cuenta visible y uno o más ámbitos ambiguos aislados.
- Cuenta con más de cien cartolas.
- Etiquetas de cuenta, banco o producto extensas.
- Cambio rápido entre cuentas con respuestas en orden inverso.
- Cambio o limpieza rápida de fechas.
- Error de catálogo, análisis, autenticación o red.
- Cuenta eliminada mientras su análisis está en curso.
- Resultado sin movimientos, categorías, comercios, recurrencias, avisos o
  highlight.
- Montos grandes y gráficos con etiquetas largas en 320 px.

## Supuestos

- `GET /v1/accounts` y el análisis por `account_id` están implementados y
  verificados antes de iniciar esta fase.
- Los controles de fecha nativos entregan valores vacíos o fechas ISO completas;
  no se envían fragmentos intermedios.
- La selección automática se aplica cuando el catálogo tiene exactamente una
  opción; cualquier incompatibilidad del historial se presenta como error
  corregible de análisis.
- El diseño visual y la tipografía de `frontend-visual-refresh` permanecen
  vigentes salvo el orden y densidad reemplazados explícitamente aquí.

## Preguntas abiertas

- No hay preguntas abiertas que bloqueen la planificación.
