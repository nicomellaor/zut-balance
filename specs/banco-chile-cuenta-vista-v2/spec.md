# Layout v2 de Cuenta Vista Banco de Chile

## Objetivo

Extender la ingesta de Cuenta Vista Banco de Chile para reconocer y normalizar
de forma confiable la variante digital anonimizada
`media/cartola_v2_ejemplo_banco_chile.pdf`, sin debilitar el rechazo de layouts
ambiguos ni alterar resultados de las variantes ya aprobadas.

## Contexto

Las fases 1 y 2 soportan la muestra original y variantes sintéticas aprobadas.
La nueva muestra es una cartola digital de una página del mismo banco y
producto, pero muestra un encabezado de tabla en dos líneas (`FECHA` y
`DIA/MES`, `MONTO CARGOS`, `MONTO DEPOSITOS O ABONOS`) y una disposición de
filas distinta. Incluye información personal anonimizada que no debe formar
parte del resultado normalizado ni de errores.

## Alcance

- Aceptar automáticamente la variante v2 y las variantes de Cuenta Vista ya
  aprobadas, sin un parámetro de formato en la API.
- Reconocer v2 por un conjunto de marcadores estructurales inequívocos.
- Extraer sus metadatos, resumen y seis movimientos en orden documental.
- Normalizar fechas, montos, débitos, créditos y saldo informado conforme al
  modelo público actual.
- Mantener enmascarado el número de cuenta y excluir nombre, correo, ejecutivo,
  sucursal, teléfono y texto legal de los resultados.
- Mantener la conciliación general y rechazar una estructura v2 incompleta o
  ambigua.
- Probar la muestra v2 y la ausencia de regresiones de todas las muestras ya
  aprobadas.

## Fuera de alcance

- Otros bancos, productos, monedas, OCR o PDFs sin texto extraíble.
- Soporte genérico para todo layout de Cuenta Vista no definido por la muestra
  v2 o por la matriz existente.
- Nuevas rutas HTTP, selección de formato declarada por cliente o un registro
  extensible de bancos.
- Persistencia de campos personales, PDF original o texto extraído.
- Categorización, análisis, interfaz, IA o corrección automática de cartolas.

## Requisitos funcionales

### RF-01: Reconocimiento automático seguro

El parser público debe aceptar la muestra original, las variantes sintéticas ya
aprobadas y v2. Debe seleccionar v2 solo cuando sus marcadores de producto,
período, tabla dividida y columnas de cargo/abono permitan identificarla sin
ambigüedad. Un documento que no coincida inequívocamente con una variante
aprobada debe producir `UnsupportedStatementError` o
`UnreliableExtractionError`, según corresponda.

### RF-02: Metadatos y privacidad

Para v2 se deben devolver `Banco de Chile`, `CUENTA VISTA`, moneda `PESOS`,
cartola `5`, página `1` de `1`, período desde `30/06/2026` hasta `31/07/2026`
y una cuenta enmascarada con como máximo cuatro dígitos visibles.

No se deben devolver ni registrar nombre, correo, ejecutivo, sucursal,
teléfono, número completo de cuenta ni texto legal.

### RF-03: Resumen financiero

Para v2 se deben extraer saldo inicial `48.210`, saldo final `61.891`,
retención a un día `0`, retención a más de un día `0` y saldo disponible
`61.891`.

### RF-04: Movimientos v2

Se deben extraer exactamente seis movimientos, en este orden documental:

| Fecha | Descripción | Canal | Monto | Tipo | Saldo informado |
| --- | --- | --- | ---: | --- | ---: |
| 27/07/2026 | `TRASPASO A:Sociedad Procesadora De` | `INTERNET` | 5.000 | débito | 0 |
| 27/07/2026 | `TRASPASO DE:ROSALES, PEDRO JUAN` | `INTERNET` | 30.000 | crédito | 73.210 |
| 28/07/2026 | `TRASPASO DE:ROSALES, PEDRO JUAN` | `INTERNET` | 50.000 | crédito | 0 |
| 28/07/2026 | `TRASPASO DE:ROSALES, PEDRO JUAN` | `INTERNET` | 50.000 | crédito | 173.210 |
| 29/07/2026 | `PAGO:SERVICIOS MEDICOS` | `CENTRAL` | 91.519 | débito | 81.691 |
| 30/07/2026 | `PAGO:CINEPLANET WEBPAY` | `CENTRAL` | 19.800 | débito | 0 |

Los números de documento ausentes deben representarse como ausencia. `SALDO
INICIAL` y `SALDO FINAL` no son movimientos.

### RF-05: Conciliación y completitud

La variante v2 debe cumplir:

```text
48.210 - 116.319 + 130.000 = 61.891
```

Una fila sin fecha, descripción, monto o columna identificable; un saldo o
resumen no extraíble; o una conciliación distinta debe rechazar la cartola. El
saldo informado `0` debe preservarse literalmente.

### RF-06: Compatibilidad de servicio y persistencia

`POST /v1/statements` debe detectar v2 mediante el parser público actual y
preservar la respuesta normalizada, autenticación, límites de entrada y
persistencia de fase 4. La deduplicación sigue basada en los bytes completos
del PDF.

## Requisitos no funcionales

### RNF-01: Exactitud

La detección de estructura y columnas debe prevalecer sobre la cobertura. No se
deben inferir columnas por posiciones rígidas cuando las etiquetas o su relación
espacial no sean determinables.

### RNF-02: Privacidad

La muestra y las pruebas se tratarán como datos anonimizados. Los resultados,
errores y logs no deben exponer sus datos personales ni más de cuatro dígitos de
cuenta consecutivos.

### RNF-03: Compatibilidad y determinismo

La interfaz pública `parse_banco_chile_cuenta_vista`, los modelos y las
respuestas de API se mantienen. El mismo PDF v2 produce el mismo resultado o el
mismo error de dominio.

### RNF-04: Testabilidad

Las pruebas deben usar la muestra v2 versionada y las fixtures existentes. Las
pruebas negativas deben alterar o simular un marcador, columna o fila relevante
para comprobar el rechazo seguro.

## Criterios de aceptación

- **CA-01:** La muestra v2 se procesa sin OCR y devuelve Banco de Chile, Cuenta
  Vista, período, paginación, moneda y cartola definidos en RF-02.
- **CA-02:** La cuenta de v2 se devuelve enmascarada, sin más de cuatro dígitos
  consecutivos; nombre, correo, ejecutivo y teléfono no aparecen en el modelo ni
  en la respuesta API.
- **CA-03:** La muestra v2 devuelve exactamente los seis movimientos de RF-04,
  en orden documental y con números de documento ausentes.
- **CA-04:** Los montos de v2 suman débitos `116.319`, créditos `130.000` y
  concilian con el saldo final `61.891`.
- **CA-05:** Los saldos informados `0` de v2 se preservan como `0`, no como
  ausencia ni como saldo calculado.
- **CA-06:** `SALDO INICIAL`, `SALDO FINAL`, datos personales y texto legal no
  aparecen como movimientos ni en sus descripciones.
- **CA-07:** Una tabla v2 con encabezado, columnas o fila obligatoria ambigua
  produce un error de dominio seguro, sin resultado parcial exitoso.
- **CA-08:** La muestra original y todas las fixtures de fase 2 conservan sus
  resultados normalizados existentes.
- **CA-09:** El upload autenticado de v2 devuelve el mismo resultado que el
  parser directo y un `statement_id`; una segunda carga de los mismos bytes lo
  reutiliza.

## Casos límite

- Encabezado de tabla v2 distribuido en dos líneas.
- Columna `MONTO DEPOSITOS O ABONOS` dividida visualmente.
- Filas sin número de documento.
- Tres abonos consecutivos con descripciones repetidas.
- Saldos informados iguales a cero.
- Datos personales antes de la tabla.
- Pie legal después del resumen.
- Marcador v2 presente sin columnas o filas determinables.
- Layout que combina señales de v2 y una variante no aprobada.

## Supuestos

- `media/cartola_v2_ejemplo_banco_chile.pdf` está autorizada y anonimizada para
  versionarse y probarse.
- v2 es una cartola digital de una página con texto extraíble, sin cifrado.
- Los montos son CLP enteros y cada movimiento ocupa exactamente una columna de
  cargo o abono.
- No existe evidencia adicional de conteos o totales de movimientos en v2; la
  conciliación no detecta omisiones que se compensen entre sí.

## Preguntas abiertas

- ¿Existen versiones v2 multipágina, con paginación distinta o con orden
  cronológico inverso que deban incorporarse tras contar con nuevas muestras?
- ¿La muestra debe complementarse con un generador sintético que reproduzca su
  layout para pruebas negativas más controladas?
