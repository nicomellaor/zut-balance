# Robustecimiento de ingesta Cuenta Vista Banco de Chile

## Objetivo

Extender la ingesta de cartolas PDF digitales de Cuenta Vista Banco de Chile
para procesar de forma confiable las variantes sintéticas aprobadas de
paginación, disposición de contenido y períodos que cruzan de año, preservando
el contrato normalizado y seguro de la primera versión.

## Contexto

La primera versión procesa exclusivamente el layout de una página representado
por `media/cartola_ejemplo_banco_chile.pdf`. La fase 2 del roadmap requiere
consolidar ese contrato antes de añadir una API, persistencia u otros bancos.

La compatibilidad de esta feature se definirá por un conjunto de fixtures PDF
sintéticos aprobados. No se debe inferir soporte para layouts reales o futuros
que no estén representados por esa matriz. Los requisitos de la primera
especificación continúan vigentes salvo donde esta feature los amplíe.

## Alcance

- Mantener sin regresiones la ingesta de la muestra existente de una página.
- Aceptar cartolas digitales multipágina de las variantes sintéticas aprobadas.
- Validar la coherencia entre la cantidad de páginas extraídas y la paginación
  declarada por el documento.
- Extraer metadatos, resumen y transacciones cuando aparezcan en páginas
  distintas según las variantes aprobadas.
- Normalizar correctamente movimientos de períodos que cruzan de diciembre a
  enero.
- Reconstruir descripciones partidas y excluir encabezados, pies, marcas de
  agua y textos legales de las transacciones.
- Admitir variaciones sintéticas aprobadas de posiciones horizontales de
  columnas y orden de campos de metadatos.
- Rechazar de forma explícita una paginación, estructura de tabla, fecha o fila
  que no pueda determinarse con suficiente certeza.
- Mantener la conciliación general, el enmascaramiento de cuenta y el resultado
  determinista de la interfaz pública actual.

## Matriz de variantes aprobadas

Las variantes que esta feature debe cubrir son las siguientes. Cada una debe
contar con un fixture PDF sintético y un resultado esperado reproducible.

| Variante | Condiciones aprobadas |
| --- | --- |
| Regresión de una página | La muestra actual mantiene el resultado normalizado existente. |
| Multipágina con encabezados repetidos | Las páginas de movimientos repiten el encabezado de tabla; los encabezados no se devuelven como movimientos. |
| Metadatos y resumen separados | Los datos generales aparecen en la primera página y el resumen financiero en la última. |
| Período entre años | El período cruza de diciembre de un año a enero del siguiente. |
| Texto no transaccional intercalado | Marcas de agua, textos legales y pies pueden aparecer entre líneas de movimientos. |
| Descripción partida | Una descripción puede continuar en la línea siguiente sin incluir valores de otras columnas. |
| Columnas desplazadas | Las posiciones horizontales cambian, pero los encabezados y su orden relativo se conservan. |
| Metadatos reordenados | Los campos de encabezado pueden aparecer en un orden distinto sin cambiar sus etiquetas. |

Las columnas reordenadas, etiquetas de tabla ausentes o ambiguas, montos fuera
de columnas identificables y formatos no incluidos en esta matriz no están
soportados y deben rechazarse.

## Fuera de alcance

- OCR y cartolas escaneadas.
- Otros bancos, productos o layouts no incluidos en la matriz aprobada.
- Reconocimiento genérico o automático de formatos desconocidos.
- API, interfaz gráfica, persistencia o retención de documentos.
- Categorización, normalización de comercios, métricas, análisis e IA.
- Corrección automática de datos o de una cartola inconsistente.
- Garantizar detección de filas que el propio PDF omita sin dejar evidencia en
  paginación, totales, conteos u otra estructura del documento.

## Requisitos funcionales

### RF-01: Compatibilidad existente

La interfaz pública existente debe mantener el resultado normalizado de la
muestra original, incluidos sus saldos, movimientos, saldo informado igual a
`0` y enmascaramiento de cuenta.

### RF-02: Paginación multipágina

El sistema debe aceptar la cartola multipágina de cada fixture aprobado cuando
la cantidad de páginas físicas coincida con el total declarado y los números de
página declarados formen una secuencia única, completa y en orden documental.

Debe rechazar una página faltante, duplicada, desordenada, fuera de rango o un
total declarado que no coincida con la cantidad de páginas extraídas.

### RF-03: Distribución de secciones

El sistema debe obtener los metadatos desde la primera página y el resumen
financiero desde la última cuando así lo establezca un fixture aprobado.

Si un metadato aparece repetido en varias páginas, sus valores deben ser
consistentes. Una discrepancia debe rechazarse explícitamente.

### RF-04: Tabla de movimientos multipágina

El sistema debe extraer todos los movimientos de las páginas de tabla en orden
documental y devolver cada fila una sola vez. Los encabezados repetidos,
`SALDO INICIAL`, `SALDO FINAL`, pies de página, marcas de agua y textos legales
no deben convertirse en movimientos ni añadirse a sus descripciones.

Una página de movimientos sin una estructura de tabla determinable debe
rechazarse explícitamente.

### RF-05: Variantes de tabla aprobadas

El sistema debe aceptar la variante sintética con columnas desplazadas cuando
las etiquetas y el orden relativo de las columnas requeridas sean
determinables. Debe identificar de forma fiable descripción, documento o canal
opcional, cargo, abono y saldo informado.

No debe asumir posiciones fijas de caracteres entre variantes aprobadas. Una
tabla con columnas reordenadas, superpuestas, ausentes o ambiguas debe
rechazarse explícitamente.

### RF-06: Reconstrucción y completitud de filas

El sistema debe reconstruir una descripción dividida entre líneas usando solo
el espacio de su columna. Todo contenido candidato a movimiento debe poder
asociarse sin ambigüedad a una fila completa con fecha, descripción, monto y
tipo de movimiento; de lo contrario, no debe informarse éxito completo.

### RF-07: Fechas entre años

El sistema debe normalizar cada fecha `DD/MM` contra el período completo de la
cartola. En un período que cruza de diciembre a enero, las filas de diciembre
deben pertenecer al año inicial y las de enero al año final.

Un período invertido, una fecha de período inválida o un día/mes cuyo año no
pueda determinarse de forma única debe producir un error de dominio explícito.

### RF-08: Orden de metadatos

El sistema debe extraer los campos de metadatos de la variante aprobada aunque
sus etiquetas aparezcan en un orden diferente. Los campos opcionales ausentes
deben continuar representándose como ausencia y nunca como valores inventados.

### RF-09: Conciliación y evidencia de completitud

El sistema debe conservar la conciliación general:

```text
saldo inicial - total de débitos + total de créditos = saldo final
```

Cuando el documento incluya totales de movimientos, conteos u otra evidencia de
completitud, el sistema debe comprobarla antes de devolver éxito. Una
inconsistencia debe rechazarse explícitamente y nunca corregirse.

La conciliación neta por sí sola no permite detectar omisiones compensadas si
el documento no aporta evidencia adicional; este límite debe mantenerse
documentado y no debe presentarse como una garantía de detección total.

### RF-10: Rechazo seguro y determinismo

Una variante no aprobada, una estructura incompleta, paginación inconsistente o
extracción ambigua debe producir un error explícito de dominio y no un
resultado parcial exitoso. El mismo PDF debe devolver el mismo resultado
normalizado o el mismo tipo de error.

## Requisitos no funcionales

### RNF-01: Privacidad

- Los fixtures y pruebas deben usar solo datos sintéticos o anonimizados.
- No se deben incorporar cartolas reales al repositorio.
- El número de cuenta debe seguir enmascarado, con como máximo cuatro dígitos
  visibles.
- No se debe incluir contenido sensible innecesario en errores o logs.

### RNF-02: Exactitud

La certeza de la estructura debe prevalecer sobre la cobertura. Las variantes
no determinables deben rechazarse en vez de aproximarse con valores parciales.

### RNF-03: Compatibilidad

La implementación debe preservar la interfaz pública y los modelos normalizados
existentes para los consumidores de la primera versión.

### RNF-04: Testabilidad

Cada variante aprobada debe tener un fixture sintético versionado, resultados
esperados verificables y pruebas negativas para sus límites relevantes.

### RNF-05: Separación de responsabilidades

La feature se limita a extracción, normalización y validación. No debe añadir
dependencias o responsabilidades de OCR, clasificación, persistencia,
presentación, métricas o IA.

## Criterios de aceptación

- **CA-01:** La muestra original de una página devuelve el mismo resultado
  normalizado que antes de esta feature.
- **CA-02:** Una cartola sintética de tres páginas aprobada se reconoce y se
  procesa completamente.
- **CA-03:** La cartola multipágina devuelve todas las transacciones esperadas
  una sola vez y en orden documental.
- **CA-04:** Los encabezados de tabla repetidos no aparecen como transacciones.
- **CA-05:** Metadatos de primera página y resumen de última página se extraen
  y combinan correctamente.
- **CA-06:** La cantidad física de páginas, el total declarado y la secuencia
  de números de página coinciden para una cartola válida.
- **CA-07:** Páginas faltantes, duplicadas, desordenadas, fuera de rango o un
  total declarado inconsistente producen `UnreliableExtractionError`.
- **CA-08:** Una cartola del `15/12/2026` al `15/01/2027` asigna diciembre a
  2026 y enero a 2027.
- **CA-09:** Un período invertido, inválido o una fecha ambigua produce un
  error de dominio explícito, no una excepción de biblioteca o estándar.
- **CA-10:** Marcas de agua, textos legales y pies de página no forman parte
  de ninguna descripción ni transacción.
- **CA-11:** Una descripción partida de un fixture multipágina se reconstruye
  sin incluir valores de otras columnas.
- **CA-12:** La variante aprobada con columnas desplazadas devuelve el mismo
  modelo normalizado esperado que su variante base.
- **CA-13:** La variante aprobada con metadatos reordenados devuelve los mismos
  metadatos normalizados esperados.
- **CA-14:** Columnas reordenadas, ausentes o ambiguas producen
  `UnreliableExtractionError`.
- **CA-15:** Una fila candidata incompleta o no determinable impide informar un
  resultado exitoso completo.
- **CA-16:** La cartola multipágina válida cumple la conciliación general con
  su saldo final.
- **CA-17:** Cuando el fixture incluya evidencia de conteo o totales, una
  omisión que contradiga esa evidencia produce `UnreliableExtractionError`.
- **CA-18:** El número de cuenta no se devuelve completo en ninguna variante.
- **CA-19:** Dos ejecuciones sobre el mismo fixture devuelven resultados
  normalizados iguales.

## Casos límite

- Página inicial sin tabla de movimientos.
- Página de continuación con encabezado de tabla repetido.
- Página de continuación sin filas de movimientos.
- Resumen financiero presente solo en la última página.
- Metadatos repetidos y consistentes entre páginas.
- Metadatos repetidos con valores discrepantes.
- Última transacción seguida por un pie de página o texto legal.
- Descripción continuada al inicio de una página posterior.
- Saldo informado en fila igual a cero.
- Campos opcionales vacíos.
- Período que cruza de diciembre a enero.
- Fecha `DD/MM` válida en más de un año posible.
- Fecha de período inválida o período con inicio posterior al final.
- Total de páginas declarado distinto del número de páginas físicas.
- Línea de movimiento con monto en una columna no identificable.
- Dos filas distintas que se compensan en la conciliación neta sin otra
  evidencia documental.

## Supuestos

- Los PDFs de la matriz aprobada contienen texto extraíble y no están cifrados.
- Los fixtures sintéticos representan los contratos soportados, no todas las
  variantes reales de Banco de Chile.
- Los montos se expresan como pesos chilenos enteros y un movimiento contiene
  un cargo o un abono, pero no ambos.
- La paginación declarada está disponible en los fixtures multipágina.
- Las etiquetas de columnas requeridas se mantienen, aunque sus posiciones
  horizontales puedan cambiar en la variante aprobada.
- Los modelos públicos actuales son suficientes para expresar el resultado de
  esta feature.

## Preguntas abiertas

- ¿Qué límites de tamaño de archivo y cantidad de páginas debe imponer una API
  futura?
- ¿Qué variantes reales adicionales deben incorporarse una vez existan muestras
  anonimizadas y autorizadas?
- ¿Qué política de orden debe aplicarse si una cartola real enumera movimientos
  en orden cronológico inverso?
- ¿Cómo debe representarse una cartola real que no imprima paginación?
- ¿Qué evidencia de conteos o totales de movimientos ofrecen los layouts reales
  para reforzar la detección de omisiones?
