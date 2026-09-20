# Catálogo local de comercios y categorías

## Objetivo

Sustituir las reglas de categorización embebidas en código por un catálogo local,
versionado y auditable distribuido con Zut Balance, manteniendo la clasificación
determinista, la normalización actual, la precedencia y la trazabilidad persistida.

## Contexto

Las reglas actuales viven en `categorization.py`, se aplican al guardar una
cartola y su resultado se materializa en SQLite con `rule_id` y
`ruleset_version`. El análisis y la API consumen esas clasificaciones persistidas;
no las recalculan al leer datos históricos.

La fase 17 amplía la cobertura sin introducir servicios externos, IA, reglas
administrables por HTTP ni reclasificación automática. El catálogo debe permitir
revisar las reglas como datos versionados y garantizar que sea válido antes de
que una inicialización pueda migrar o escribir SQLite.

La decisión confirmada para esta fase reemplaza el límite previo del roadmap:
una glosa que comienza por `PAGO:MERCADOPAGO` se clasifica como `compras` sin
identificar comercio. Una regla más específica puede identificar el comercio
subyacente solo cuando su glosa y categoría estén respaldadas por evidencia.

## Alcance

- Distribuir catálogos de categorías y comercios como recursos locales
  versionados dentro del paquete Python.
- Conservar un catálogo v1 que reproduzca exactamente las reglas actuales y
  activar un catálogo v2 que incorpore las reglas aprobadas en esta fase.
- Validar estrictamente el contenido de un catálogo antes de usarlo para
  clasificar, inicializar o migrar SQLite.
- Conservar la normalización de descripciones existente y añadir coincidencia
  por prefijo de token para indicadores genéricos seguros.
- Incorporar reglas auditables para Cineplanet, Servicios Médicos, transferencias,
  Unimarc, PedidosYa, MercadoPago genérico, cine genérico y café genérico.
- Mantener la persistencia actual de categoría, comercio opcional, regla, versión
  y fecha de clasificación.
- Documentar formato, incorporación de evidencia, versionado e impacto sobre
  cartolas históricas.

## Fuera de alcance

- Añadir categorías, tablas SQLite, endpoints, interfaz administrativa, aliases
  editables por usuario o catálogo configurable desde el entorno.
- Automatizar extracción de reglas desde cartolas, consultar catálogos remotos,
  usar IA, regex configurables, puntuación de confianza o inferencia probabilística.
- Reclasificar cartolas existentes, modificar una carga deduplicada o alterar la
  descripción original del movimiento.
- Inferir el comercio subyacente de una glosa genérica de MercadoPago.
- Cambiar la taxonomía `Category`, contratos HTTP, análisis financiero, puertos,
  red, autenticación o esquema SQLite.

## Requisitos funcionales

### RF-01: Catálogos versionados y auditables

El paquete debe incluir un catálogo v1 y un catálogo v2 de reglas. El v1 debe
producir para las reglas existentes la misma categoría, nombre y clave de
comercio, `rule_id` y versión `1` que la implementación actual. El v2 debe ser
el catálogo activo y declarar versión `2`.

Los catálogos publicados son inmutables: cualquier cambio que pueda alterar una
clasificación, incluida la normalización o una regla, requiere una nueva versión
de ruleset. Las versiones históricas deben permanecer disponibles en el
repositorio para auditoría.

### RF-02: Formato y validación estrictos

Cada catálogo debe declarar una versión de esquema, una versión de ruleset y una
lista de reglas. Cada regla debe declarar identificador, categoría, tipo de
coincidencia, patrón, prioridad, tipo de movimiento opcional y comercio opcional.

Antes de usar un catálogo, el sistema debe rechazar de forma explícita JSON
inválido o con claves duplicadas, campos desconocidos, campos obligatorios
ausentes, versión de esquema no soportada, versión de ruleset vacía, identificador
vacío o duplicado, categoría o tipo de movimiento inválidos, tipo de coincidencia
inválido, patrón vacío o no normalizado, prioridad que no sea entero, y nombre o
clave de comercio presentes por separado. Las claves canónicas de comercio deben
estar normalizadas.

Una regla no puede duplicar el mismo dominio de coincidencia de otra regla con el
mismo tipo de coincidencia, patrón y restricción de tipo de movimiento.

### RF-03: Coincidencia y precedencia deterministas

El catálogo debe soportar:

- `exact`: la clave normalizada completa coincide con el patrón.
- `prefix`: la clave normalizada comienza con el patrón.
- `token_prefix`: algún token normalizado comienza con el patrón, donde el patrón
  es un único token alfanumérico.

La precedencia debe ser, en orden: `exact`, `prefix`, `token_prefix`; dentro del
mismo tipo gana la prioridad mayor y luego el `rule_id` lexicográficamente menor.
El orden de las reglas en el archivo no debe afectar el resultado. Deben
conservarse las reglas actuales y su comportamiento en el catálogo v1.

Una regla aplicable solo a un tipo de movimiento no debe clasificar el tipo
opuesto. Las nuevas reglas de comercios, MercadoPago y palabras clave de esta
fase se aplican únicamente a débitos.

### RF-04: Reglas v2 aprobadas

El catálogo activo debe contener, además de las reglas equivalentes a v1:

- Una regla de prefijo para `PAGO UNIMARC` que clasifique débitos como
  `alimentacion`, comercio `Unimarc` y clave `UNIMARC`.
- Reglas de prefijo para `PAGO PEDIDOSYA` y `PAGO DL PEDIDOSYA` que clasifiquen
  débitos como `alimentacion`, comercio `PedidosYa` y clave `PEDIDOSYA`.
- Una regla de prefijo de baja prioridad para `PAGO MERCADOPAGO` que clasifique
  débitos como `compras`, sin `merchant_name` ni `merchant_key`.
- Una regla `token_prefix` para `CINE` que clasifique débitos como
  `entretenimiento`, sin comercio identificado.
- Una regla `token_prefix` para `CAFE` que clasifique débitos como
  `alimentacion`, sin comercio identificado.

Las reglas específicas existentes, como Cineplanet, deben mantener su comercio
canónico. Las reglas de transferencia deben conservar su prioridad y aplicarse
antes que indicadores genéricos de cine o café.

### RF-05: Fallback y evidencia negativa

Un movimiento sin regla aplicable debe seguir como `sin_categoria`, sin comercio
ni `rule_id`. Un crédito desconocido no se debe inferir como ingreso.

`MERCADOPAGO` sin el prefijo `PAGO` no debe coincidir. Una palabra que solo
contenga las letras de un indicador, como `DESCAFEINADO`, no debe coincidir con
`CAFE`. Una transferencia que mencione cine o café debe conservar la categoría
`transferencias`.

### RF-06: Inicio, empaquetado y persistencia

El catálogo activo debe cargarse desde los recursos instalados del paquete, no
desde una ruta relativa de ejecución. Debe estar disponible tras instalar el
paquete y dentro de la imagen Docker.

Un catálogo inválido debe impedir el inicio antes de cualquier inicialización o
migración que pueda mutar SQLite. Las clasificaciones existentes, incluidas las
de versión 1, deben conservarse; una carga nueva usa el catálogo v2 y una carga
deduplicada reutiliza la clasificación previamente persistida.

## Requisitos no funcionales

- La clasificación sigue siendo local, reproducible, determinista e independiente
  de red, reloj, orden de catálogo o servicios externos.
- Los catálogos y pruebas solo contienen glosas sintéticas o anonimizadas, sin
  cuentas, documentos, pedidos, personas, secretos o datos financieros reales.
- Los errores de validación no deben registrar ni exponer descripciones de
  cartolas, secretos o información de SQLite.
- No se añaden dependencias de ejecución para interpretar el catálogo.
- Las expectativas de API para reglas nuevas deben ser independientes del
  clasificador productivo.

## Criterios de aceptación

- **CA-01:** El paquete instalado incluye catálogos v1 y v2; cargar v1 reproduce
  exactamente las reglas actuales y el catálogo activo identifica versión `2`.
- **CA-02:** JSON malformado, claves duplicadas, estructura inválida, reglas
  duplicadas, patrones no normalizados y valores de enum o prioridad inválidos se
  rechazan antes de modificar SQLite.
- **CA-03:** Las coincidencias y desempates cumplen `exact > prefix >
  token_prefix`, prioridad y `rule_id`, independientemente del orden del archivo.
- **CA-04:** Las glosas aprobadas de Unimarc y las dos variantes de PedidosYa se
  clasifican como `alimentacion` con comercio y clave canónicos.
- **CA-05:** `PAGO:MERCADOPAGO...` como débito se clasifica `compras` sin
  comercio; una regla específica respaldada por evidencia puede prevalecer sobre
  esa regla genérica.
- **CA-06:** Débitos con tokens `CINE`, `CINEMARK`, `CAFE` o `CAFETERIA` reciben
  las categorías aprobadas sin comercio; Cineplanet conserva su identidad
  canónica y `DESCAFEINADO` no coincide.
- **CA-07:** Créditos para las reglas nuevas, transferencias que contienen esos
  tokens y descripciones sin regla conservan el comportamiento seguro esperado.
- **CA-08:** Cartolas existentes y cargas deduplicadas no se reclasifican; una
  cartola nueva persiste la versión `2` y análisis mixtos informan ambas versiones.
- **CA-09:** La API conserva su contrato y expone las clasificaciones persistidas
  de reglas nuevas; no se añade endpoint administrativo ni se modifica SQLite.
- **CA-10:** La suite Python, la instalación empaquetada y el smoke test Compose
  completan correctamente sin dependencias ni servicios externos nuevos.

## Casos límite

- Un catálogo se modifica conservando la misma versión de ruleset.
- Una regla `prefix` amplia solapa un prefijo específico o un indicador de token.
- Una glosa de MercadoPago contiene una palabra como `CAFE` o `CINE`.
- Una glosa de transferencia menciona `CAFE`, `CINE`, Unimarc o PedidosYa.
- El catálogo falta en una instalación empaquetada o imagen Docker.
- Una base v1 se abre por primera vez con el catálogo v2 activo.
- El archivo JSON contiene `true` como prioridad, campos con nombre mal escrito o
  claves repetidas.

## Supuestos

- Las glosas aportadas para Unimarc y PedidosYa son representativas de los
  patrones aprobados y no incluyen identificadores reales.
- `alimentacion` es la categoría aceptada para Unimarc, PedidosYa y café, y
  `entretenimiento` para cine.
- `compras` con comercio nulo representa apropiadamente un pago genérico por
  MercadoPago sin reducirlo a `sin_categoria`.
- El aviso actual de versiones mixtas en análisis es el comportamiento esperado
  mientras coexistan cartolas de ruleset 1 y 2.

## Preguntas abiertas

- Ninguna para la primera versión local del catálogo. La curación de más comercios,
  aliases, resolución de conflictos y edición sin despliegue corresponden a la
  fase 18.
