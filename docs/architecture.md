# Arquitectura

## Propósito

Zut Balance procesa cartolas digitales de Cuenta Vista Banco de Chile y produce
datos de gasto verificables. Cada capa conserva responsabilidades separadas:

```text
PDF -> parser y validación -> SQLite -> categorización -> análisis -> API y SPA
```

El proyecto es privado e independiente; no representa ni está afiliado a Banco
de Chile.

## Componentes

- El parser valida estructura, extrae movimientos y concilia saldos antes de
  aceptar una cartola.
- SQLite persiste cartolas, movimientos y clasificaciones, pero no el PDF
  original ni el texto extraído.
- La categorización carga un catálogo local, versionado y validado al iniciar
  sobre una clave de glosa normalizada; una glosa sin regla queda
  `sin_categoria`.
- El análisis calcula métricas, evolución, cobertura, comercios y recurrencias
  desde movimientos ya clasificados.
- FastAPI expone rutas autenticadas; React entrega la SPA de carga y análisis.
- En Docker, Caddy sirve SPA y API bajo el mismo origen HTTPS y la API permanece
  en una red interna.

Las especificaciones de ingesta, persistencia, categorización y análisis en
[`specs/`](../specs/) describen los contratos detallados y sus límites.
La política y formato del catálogo están en [Catálogo local de
comercios](merchant-catalog.md).

## Datos y límites

El soporte se limita a los formatos digitales explícitamente validados. El
parser rechaza formatos desconocidos, PDFs escaneados o protegidos y extracciones
que no cumplan sus controles. No hay OCR, inferencia remota ni conclusiones
financieras generadas por IA.

El identificador de cuenta usado por análisis es un ámbito opaco de cartolas
compatibles; no demuestra identidad bancaria ni deriva un número de cuenta.

## API y autenticación

`GET /health` es público. Las rutas de datos requieren una sesión web de
administrador o una API key Bearer para integraciones. La SPA usa sesión firmada
en cookie `HttpOnly`; no almacena ni transmite la API key.

Las rutas principales son:

- `POST /v1/statements`: procesa y guarda una cartola.
- `GET /v1/statements`: lista metadatos de cartolas.
- `GET /v1/statements/{statement_id}`: obtiene una cartola completa.
- `DELETE /v1/statements/{statement_id}`: elimina una cartola y sus datos.
- `GET /v1/accounts`: lista ámbitos de cuenta compatibles.
- `GET /v1/analysis?account_id=<uuid>`: calcula el análisis histórico de una
  cuenta; acepta fechas opcionales inclusivas `from` y `to`.

La referencia completa de despliegue, autenticación y backup está en
[Despliegue Docker](deployment.md).
