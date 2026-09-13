# Ingesta de cartola Cuenta Vista Banco de Chile

## Objetivo

Procesar una cartola PDF de Cuenta Vista del Banco de Chile con texto extraíble y producir una representación estructurada y normalizada de sus datos generales, saldos y transacciones.

## Contexto

Esta feature constituye la primera etapa del pipeline de procesamiento documental de Zut Balance. Su responsabilidad termina en la extracción y normalización; categorización, análisis e insights pertenecen a etapas posteriores.

El formato inicialmente soportado será el representado por `media/cartola_ejemplo_banco_chile.pdf`. La compatibilidad se limita a este layout hasta validar otras variantes con muestras sintéticas o anonimizadas.

## Alcance

- Aceptar cartolas PDF con texto extraíble.
- Reconocer el formato inicial de Cuenta Vista del Banco de Chile.
- Extraer datos generales de la cuenta y cartola.
- Extraer saldos y retenciones.
- Identificar las filas correspondientes a movimientos.
- Normalizar fechas y montos.
- Clasificar cada movimiento como débito o crédito.
- Preservar los valores informados por el documento.
- Detectar extracciones incompletas o inconsistencias generales.
- Proteger el número de cuenta mediante enmascaramiento.

## Fuera de alcance

- OCR y documentos escaneados.
- Otros bancos o productos.
- Variaciones no documentadas del layout.
- Categorización de gastos.
- Identificación normalizada de comercios.
- Persistencia.
- API o interfaz gráfica.
- Métricas, análisis e insights.
- Corrección automática de datos informados por la cartola.

## Requisitos funcionales

### RF-01: Validación del documento

El sistema debe aceptar únicamente PDFs válidos, no protegidos y con texto extraíble.

Debe rechazar explícitamente archivos corruptos, cifrados, escaneados o cuyo formato no sea reconocido.

### RF-02: Reconocimiento del formato

El sistema debe verificar que el documento corresponde al formato soportado de Cuenta Vista del Banco de Chile.

La presencia aislada del nombre del banco no debe ser suficiente para considerar reconocido el documento.

### RF-03: Datos generales

Cuando estén presentes, se deben extraer:

- Banco.
- Producto.
- Número de cuenta enmascarado.
- Moneda.
- Fecha inicial del período.
- Fecha final del período.
- Número de cartola.
- Página actual.
- Total de páginas.

Los campos ausentes deben representarse como ausentes, sin inventar valores.

### RF-04: Resumen financiero

Se deben extraer:

- Saldo inicial.
- Saldo final.
- Retención a un día.
- Retención a más de un día.
- Saldo disponible.

### RF-05: Transacciones

Cada transacción debe contener:

- Fecha completa.
- Descripción original.
- Número de documento, cuando exista.
- Sucursal o canal, cuando exista.
- Monto.
- Tipo de movimiento: débito o crédito.
- Saldo informado en la fila, cuando exista.

`SALDO INICIAL` y `SALDO FINAL` no deben tratarse como transacciones.

### RF-06: Normalización de fechas

Las fechas de movimientos deben normalizarse a una fecha completa usando el período de la cartola.

No se debe inferir el año cuando el período no permita determinarlo de manera inequívoca.

### RF-07: Normalización de montos

Los montos en pesos chilenos deben normalizarse como enteros, interpretando el punto como separador de miles.

El monto normalizado será no negativo y su efecto estará determinado por el tipo débito o crédito.

### RF-08: Preservación de valores

Los valores informados por el documento deben preservarse aunque parezcan inusuales.

En particular, el saldo `0` informado en el movimiento del `27/08` debe conservarse y no reemplazarse por un saldo calculado.

### RF-09: Conciliación general

Cuando estén disponibles los datos necesarios, se debe comprobar:

```text
saldo inicial - total de débitos + total de créditos = saldo final
```

Una inconsistencia debe reportarse explícitamente. No debe corregirse automáticamente el documento.

Los saldos intermedios no tienen que ser reconciliables para que la conciliación general sea válida.

### RF-10: Extracción segura

Si no es posible determinar todas las filas o columnas obligatorias con suficiente certeza, el procesamiento no debe reportarse como completamente exitoso.

## Requisitos no funcionales

### RNF-01: Privacidad

- Las pruebas automatizadas deben usar exclusivamente datos sintéticos o anonimizados.
- El número de cuenta no debe exponerse completo.
- El contenido sensible no debe incluirse innecesariamente en logs o mensajes de error.
- La cartola real no debe incorporarse al repositorio.

### RNF-02: Exactitud

La extracción debe priorizar exactitud y detección de errores sobre resultados parciales.

### RNF-03: Determinismo

El mismo PDF debe producir el mismo resultado normalizado.

### RNF-04: Testabilidad

El procesamiento debe poder validarse usando fixtures sintéticos y resultados esperados reproducibles.

### RNF-05: Separación de responsabilidades

La extracción y normalización no deben depender de categorización, IA, persistencia, métricas o presentación.

## Criterios de aceptación

- **CA-01:** La muestra se reconoce como una cartola soportada de Cuenta Vista del Banco de Chile.
- **CA-02:** Se extrae el período desde `31/07/2026` hasta `31/08/2026`.
- **CA-03:** Se extrae `PESOS` como moneda.
- **CA-04:** Se extraen exactamente seis transacciones.
- **CA-05:** Se identifican cinco débitos por un total de `23.640`.
- **CA-06:** Se identifica un crédito por `30.000`.
- **CA-07:** El saldo inicial extraído es `61.891`.
- **CA-08:** El saldo final extraído es `68.251`.
- **CA-09:** La conciliación general produce `68.251`.
- **CA-10:** El saldo `0` de la fila del `27/08` se conserva literalmente.
- **CA-11:** `SALDO INICIAL` y `SALDO FINAL` no aparecen como movimientos.
- **CA-12:** La marca de agua y el texto legal no forman parte de las transacciones.
- **CA-13:** Las descripciones partidas visualmente se reconstruyen sin incorporar texto de otras columnas.
- **CA-14:** El número de cuenta nunca se devuelve completo.
- **CA-15:** Un PDF protegido, escaneado, corrupto o no reconocido produce un error explícito.
- **CA-16:** Una extracción incompleta no se reporta como éxito completo.

## Casos límite

- Campos opcionales vacíos.
- Número de cartola ausente.
- Descripciones que ocupan varias líneas.
- Marca de agua superpuesta al contenido.
- Filas sin número de documento.
- Filas sin sucursal.
- Saldo intermedio igual a cero.
- Texto legal después de la tabla.
- Períodos que potencialmente crucen de diciembre a enero.
- Documentos de varias páginas.
- PDFs con texto presente pero orden de extracción irregular.

## Supuestos

- La cartola real permite extracción directa de texto.
- El primer formato soportado es de una sola página.
- Los montos corresponden a pesos chilenos sin decimales.
- Un movimiento tiene un cargo o un abono, pero no ambos.
- El monto se representa como valor positivo acompañado de su tipo.
- El número de cuenta enmascarado puede conservar como máximo sus últimos cuatro dígitos visibles.
- La muestra aproximada es suficiente para definir el primer contrato, pero no para afirmar compatibilidad con todas las cartolas reales.

## Preguntas abiertas

- ¿Qué variaciones presenta el layout real respecto de la muestra?
- ¿Cómo debe procesarse una cartola multipágina?
- ¿Cómo se determina el año cuando el período cruza de diciembre a enero?
- ¿Qué campos exactos aparecen en el número de documento?
- ¿Debe aceptarse una cartola sin número identificador?
- ¿Qué límites de tamaño y cantidad de páginas serán necesarios?
