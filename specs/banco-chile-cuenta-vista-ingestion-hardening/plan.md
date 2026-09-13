# Plan técnico: Robustecimiento de ingesta Cuenta Vista Banco de Chile

## Enfoque técnico

Se mantendrá la función pública
`parse_banco_chile_cuenta_vista(pdf: bytes | str | Path) -> Statement` y los
modelos públicos existentes. El parser seguirá siendo específico para Cuenta
Vista Banco de Chile, pero reemplazará los supuestos de página única y offsets
fijos por análisis determinista de cada página y sus encabezados.

El procesamiento seguirá estas etapas:

1. Validar el PDF digital y extraer una tupla de textos por página.
2. Clasificar cada página como encabezado, movimientos, resumen o combinación
   de esas secciones mediante marcadores estructurales.
3. Extraer y validar la paginación de todas las páginas antes de construir el
   resultado.
4. Extraer metadatos de las páginas que los informen, verificar consistencia y
   usar los valores de la primera aparición válida.
5. Extraer el resumen de las páginas que lo informen, verificando consistencia
   si aparece repetido y usando el de la última página válida.
6. Resolver los límites de columnas desde los encabezados de cada página de
   movimientos y extraer sus filas en orden documental.
7. Normalizar fechas contra el período completo, incluyendo el cruce de año, y
   rechazar períodos o fechas ambiguas.
8. Validar evidencia documentada de conteos o totales cuando esté presente,
   además de la conciliación general existente.

El resultado nunca se construirá si falta una página declarada, una fila
candidata no puede interpretarse o la evidencia de completitud es inconsistente.

## Componentes a modificar o crear

- `pyproject.toml`: añadir `reportlab` como dependencia exclusiva de desarrollo
  para generar fixtures PDF sintéticos reproducibles. No se añadirá ninguna
  dependencia de producción.
- `tests/fixtures/generate_banco_chile_cuenta_vista.py`: generador determinista
  de los PDFs sintéticos; no se ejecutará durante el parseo ni en producción.
- `tests/fixtures/`: PDFs generados y versionados para las variantes aprobadas:
  multipágina, período entre años, columnas desplazadas y metadatos reordenados.
- `src/zut_balance/banco_chile_cuenta_vista.py`: ampliar las validaciones de
  documento, extracción de secciones, filas, fechas y completitud.
- `tests/test_banco_chile_cuenta_vista.py`: conservar las regresiones actuales
  y añadir pruebas unitarias e integración para la nueva matriz de fixtures.
- `tests/test_fixture_generation.py`: comprobar que el generador produce PDFs
  legibles, con el número de páginas y marcadores acordados.
- `README.md`: actualizar el límite del formato para describir las variantes
  sintéticas soportadas una vez que hayan sido implementadas.
- `docs/roadmap.md`: marcar la fase 2 como completada solo durante la
  verificación final, si todos los criterios se satisfacen.

No se modificarán `models.py`, `errors.py`, `__init__.py` ni la firma pública
salvo que la implementación revele una necesidad que contradiga la
especificación y requiera una revisión explícita.

## Modelos e interfaces relevantes

Los modelos públicos se conservan:

- `Statement` seguirá exponiendo el número de la primera página y el total de
  páginas declaradas, sin añadir procedencia por página.
- `StatementMetadata`, `StatementSummary` y `Transaction` conservarán sus
  campos y tipos actuales.
- `UnreliableExtractionError` seguirá representando inconsistencias de
  paginación, estructura, fechas, evidencia de completitud y conciliación.

Se introducirán estructuras privadas en `banco_chile_cuenta_vista.py` solo si
reducen ambigüedad entre etapas:

- Un descriptor de página con su índice físico, paginación declarada y secciones
  detectadas.
- Un descriptor de columnas con límites obtenidos desde el encabezado de esa
  página.
- Un resumen privado de evidencia documental, como conteos, total de cargos o
  total de abonos, cuando el fixture lo informe.

La validación de paginación comprobará que todas las páginas que declaran
`N° DE PAGINA: n DE total` tengan el mismo total y una secuencia exactamente
igual a `1..total`, en el orden físico del PDF. La falta del marcador en un
fixture que lo requiere será un error no confiable.

Las páginas sin tabla se permitirán solo si su rol se reconoce como encabezado o
resumen. Una página que contenga señales de movimientos pero no permita resolver
su tabla se rechazará.

## Fixtures sintéticos

El generador usará `reportlab` para crear PDFs digitales con texto extraíble y
coordenadas controladas. Los archivos resultantes se versionarán para que las
pruebas no dependan de ejecutar el generador. El script permite regenerarlos de
forma reproducible al cambiar la matriz.

| Fixture | Contenido y propósito |
| --- | --- |
| `cartola_ejemplo_banco_chile.pdf` | Fixture existente de regresión de una página. |
| `cartola_banco_chile_multipagina.pdf` | Tres páginas: encabezado sin tabla en la primera; páginas de movimientos con encabezados repetidos; resumen y evidencia de conteos/totales en la última; textos no transaccionales intercalados. |
| `cartola_banco_chile_cruce_anio.pdf` | Período del `15/12/2026` al `15/01/2027` con movimientos en ambos años. |
| `cartola_banco_chile_columnas_desplazadas.pdf` | Mismos datos normalizados que una variante base con columnas desplazadas horizontalmente. |
| `cartola_banco_chile_metadatos_reordenados.pdf` | Mismos metadatos normalizados que una variante base con etiquetas en distinto orden. |

Las pruebas negativas de páginas faltantes, duplicadas, desordenadas, totales
inconsistentes, columnas ambiguas, filas incompletas, metadatos discrepantes y
fechas inválidas se generarán desde textos de fixture o PDFs temporales. No se
versionarán archivos negativos cuando una mutación local comunique mejor el
caso.

## Decisiones técnicas y dependencias

- `pypdf` continúa como la única dependencia de producción para validación y
  extracción de texto con layout.
- `reportlab` se agrega solo a `dev` para producir y mantener fixtures PDF
  sintéticos. Está justificado porque la especificación exige variantes PDF
  versionadas, no solo mutaciones de texto.
- Los límites de columnas se derivarán por página a partir de las posiciones de
  sus etiquetas. El tipo de movimiento se decidirá por la columna que contiene
  el monto, no mediante offsets fijos como `CARGOS - 20`.
- La extracción de metadatos y resumen buscará etiquetas de forma independiente
  en las secciones pertinentes. No dependerá del orden textual de los campos.
- Los errores de fecha de `datetime` se convertirán a
  `UnreliableExtractionError`; también se rechazará `period_start > period_end`.
- Los montos, el enmascaramiento, la conciliación neta y la preservación de
  saldos informados conservan las reglas existentes.
- La evidencia adicional de conteos o totales será opcional por documento, pero
  obligatoria de comprobar cuando esté presente. No se afirmará detectar
  omisiones compensadas si falta dicha evidencia.

## Estrategia de pruebas

- Mantener los 25 tests existentes como regresión de CA-01 y compatibilidad de
  la API.
- Verificar el generador de fixtures y ejecutar cada PDF versionado mediante la
  interfaz pública, comprobando valores normalizados completos.
- Probar paginación válida de tres páginas y los rechazos de páginas faltantes,
  duplicadas, desordenadas, fuera de rango y total declarado inconsistente.
- Probar que encabezados, pies, marcas de agua y textos legales no aparezcan en
  las descripciones ni como movimientos.
- Probar metadatos distribuidos, repetidos consistentes y discrepantes; probar
  resumen solo en la última página.
- Probar descripción partida en una página posterior y que no absorba columnas
  de documento, canal, cargo, abono o saldo.
- Probar que la variante de columnas desplazadas conserva los resultados base y
  que columnas reordenadas, ausentes o ambiguas se rechazan.
- Probar metadatos reordenados y campos opcionales ausentes.
- Probar resolución de fechas diciembre-enero, período invertido, fecha de
  período inválida y fecha de movimiento ambigua.
- Probar conciliación multipágina y la discrepancia de conteos/totales cuando
  los fixtures aporten esa evidencia.
- Ejecutar `pytest`, una llamada manual al parser público sobre cada fixture y
  `git diff --check` durante Verify.

## Riesgos y migraciones

- `pypdf` puede cambiar el orden o el espaciado del texto entre versiones. Los
  fixtures y resultados esperados fijarán los contratos aprobados; un texto no
  determinable se rechazará.
- Los PDFs generados pueden variar entre versiones de `reportlab`. Se fijará un
  rango compatible de dependencia y se probará el texto extraído, no bytes
  idénticos del archivo.
- Un parser demasiado permisivo podría convertir pies o filas mal alineadas en
  movimientos. La clasificación por secciones y el rechazo de líneas candidatas
  ambiguas minimizan este riesgo.
- Una validación demasiado estricta podría rechazar una variante sintética
  aprobada. Cada aceptación se respaldará por un fixture independiente antes de
  generalizar reglas.
- La conciliación neta no evidencia omisiones con débito y crédito compensados.
  Solo los conteos/totales que existan en el documento pueden ampliar esa
  detección; no hay migración de datos ni cambio de contrato público.
