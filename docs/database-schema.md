# Esquema de base de datos

Zut Balance usa SQLite local. La aplicación valida `PRAGMA user_version` y el
esquema esperado al iniciar; una base incompatible se rechaza sin modificarla.
El PDF original, texto extraído, números de cuenta completos, API keys y logs de
procesamiento no forman parte del esquema.

## Versión 1: migrable

La versión 1 fue el esquema utilizado por las fases 4 y 5. La aplicación lo
migra automáticamente a v2 durante la inicialización.

### `statements`

Una fila por cartola normalizada y por huella SHA-256 del PDF.

| Columna | Tipo SQLite | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `TEXT` | PK | UUID textual de la cartola. |
| `source_sha256` | `TEXT` | NOT NULL, UNIQUE | Huella del PDF, solo para deduplicación. |
| `created_at` | `TEXT` | NOT NULL | Marca UTC ISO 8601 de creación. |
| `bank`, `product` | `TEXT` | NOT NULL | Banco y producto normalizados. |
| `masked_account_number`, `currency` | `TEXT` | Opcional | Cuenta enmascarada y moneda. |
| `period_start`, `period_end` | `TEXT` | NOT NULL | Fechas ISO 8601 del período. |
| `statement_number` | `TEXT` | Opcional | Número de cartola. |
| `page_number`, `total_pages` | `INTEGER` | Opcional | Paginación declarada. |
| `opening_balance`, `closing_balance` | `INTEGER` | NOT NULL | Saldos de apertura y cierre en CLP. |
| `one_day_retention`, `multi_day_retention`, `available_balance` | `INTEGER` | Opcional | Retenciones y saldo disponible en CLP. |

### `transactions`

Movimientos en orden documental. Existe un índice por cartola y posición.

| Columna | Tipo SQLite | Restricciones | Descripción |
| --- | --- | --- | --- |
| `id` | `INTEGER` | PK | Identificador interno del movimiento. |
| `statement_id` | `TEXT` | NOT NULL, FK, CASCADE | Referencia a `statements.id`. |
| `position` | `INTEGER` | NOT NULL, UNIQUE con `statement_id` | Orden documental. |
| `transaction_date` | `TEXT` | NOT NULL | Fecha ISO 8601. |
| `description` | `TEXT` | NOT NULL | Descripción original normalizada del documento. |
| `document_number`, `branch_or_channel` | `TEXT` | Opcional | Referencia y canal informados. |
| `amount` | `INTEGER` | NOT NULL | Monto CLP no negativo. |
| `movement_type` | `TEXT` | NOT NULL, CHECK | `debit` o `credit`. |
| `reported_balance` | `INTEGER` | Opcional | Saldo informado en la fila. |

Eliminar una cartola elimina sus movimientos mediante `ON DELETE CASCADE`.

## Versión 2: vigente

`statements` y `transactions`, y agregará `transaction_classifications`.
La fase 6 mantiene sin cambios las tablas `statements` y `transactions`, y
agrega `transaction_classifications`.
`statements` y `transactions`, y agregará `transaction_classifications`.

### `transaction_classifications`

Una clasificación actual, determinista y trazable por movimiento.

| Columna | Tipo SQLite | Restricciones propuestas | Descripción |
| --- | --- | --- | --- |
| `transaction_id` | `INTEGER` | PK, FK, CASCADE | Referencia única a `transactions.id`. |
| `merchant_name` | `TEXT` | Opcional | Nombre canónico del comercio cuando una regla lo determina. |
| `merchant_key` | `TEXT` | Opcional | Clave normalizada para comparación determinista. |
| `category` | `TEXT` | NOT NULL | Categoría oficial, incluida `sin_categoria`. |
| `rule_id` | `TEXT` | Opcional | Regla que produjo el resultado; ausencia para fallback. |
| `ruleset_version` | `TEXT` | NOT NULL | Versión de reglas aplicada. |
| `classified_at` | `TEXT` | NOT NULL | Marca UTC ISO 8601 de clasificación. |

Eliminar un movimiento o su cartola eliminará su clasificación mediante cascada.
No se crearán tablas para reglas, categorías ni comercios en la primera entrega:
la taxonomía y reglas son código versionado. Las correcciones manuales, historial
de clasificaciones y administración de reglas quedan fuera de esta versión.

## Migración v1 a v2

La migración se ejecutará en una transacción:

1. Validar el esquema v1 actual antes de modificarlo.
2. Crear `transaction_classifications` y sus FK/índices.
3. Clasificar los movimientos existentes con el ruleset activo.
4. Establecer `PRAGMA user_version = 2` solo tras completar los pasos previos.

Una base v2 debe validarse de forma repetible. Una versión futura o un esquema
incompleto debe rechazarse sin mutación.
