# Esquema de base de datos

Zut Balance usa SQLite local y valida `PRAGMA user_version` al iniciar. El PDF
original, texto extraído, números de cuenta completos y API keys no se guardan.

## Versión 3: vigente

### `accounts`

Un ámbito persistido y opaco de cuenta compatible.

| Columna | Tipo | Restricciones |
| --- | --- | --- |
| `id` | TEXT | PK, UUID opaco |
| `bank`, `product` | TEXT | NOT NULL |
| `currency`, `masked_account_number` | TEXT | Opcional |
| `identity_status` | TEXT | CHECK: `visible_mask` o `ambiguous` |
| `created_at` | TEXT | NOT NULL |

`visible_mask` exige al menos un dígito visible y se agrupa por banco, producto,
moneda y máscara. Dos índices únicos parciales distinguen explícitamente moneda
`NULL` de moneda no nula. `ambiguous` representa una máscara sin dígitos visibles
o ausente y cada cartola recibe su propio ámbito.

### `statements`

Una fila por cartola normalizada, con UUID `id`, `source_sha256` único, metadatos,
período, saldos y el FK obligatorio `account_id REFERENCES accounts(id)`. El
índice `statements_account_period(account_id, period_start, period_end, id)`
resuelve catálogo e historial por ámbito.

### `transactions` y `transaction_classifications`

`transactions` conserva movimientos en orden documental, con FK en cascada a
`statements`. `transaction_classifications` contiene una clasificación
determinista por movimiento y también se elimina en cascada.

## Migración a v3

Las bases v1 y v2 se migran en una única transacción. Desde v1 se crean primero
las clasificaciones lógicas de v2 sin confirmar la versión. Después se crean los
ámbitos, se reconstruyen las cartolas con `account_id` y se validan FKs,
restricciones, índices y cantidades antes de fijar `user_version = 3`.

Un fallo revierte datos, tablas y versión de origen. Los backups consistentes de
SQLite preservan ámbitos, cartolas, movimientos y clasificaciones.
