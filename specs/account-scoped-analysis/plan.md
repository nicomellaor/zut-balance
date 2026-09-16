# Plan técnico: análisis por ámbito de cuenta

## Enfoque técnico

Se añadirá una entidad persistida `accounts` y una referencia obligatoria desde
`statements`. El identificador público será un UUID aleatorio generado por la
aplicación. La identidad compatible seguirá basándose en la tupla actual de
banco, producto, moneda y cuenta enmascarada visible; el UUID evita exponer esa
tupla como selector y desacopla el análisis de una cartola concreta.

La inicialización migrará SQLite v2 a v3 de forma atómica. La API incorporará un
catálogo autenticado y reemplazará el selector de análisis por `account_id`, sin
compatibilidad con `anchor_statement_id`. El dominio de análisis conservará sus
validaciones y fórmulas; la capa API añadirá `account_id` al objeto `scope` al
serializar el resultado.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/persistence.py` | Definir esquema v3, modelos de cuenta, migración, asignación al guardar, catálogo, historial por cuenta y limpieza de ámbitos vacíos. |
| `src/zut_balance/api.py` | Añadir `GET /v1/accounts`, reemplazar validación de query y resolver análisis por `account_id`. |
| `src/zut_balance/analysis.py` | Mantener reglas actuales; ampliar pruebas de defensa para incompatibilidad si faltan casos explícitos. |
| `tests/test_persistence.py` | Probar migración, asignación, catálogo, historial por rango y eliminación. |
| `tests/test_api.py` | Probar catálogo, nuevo contrato, rechazo del contrato anterior, privacidad y ausencia de escrituras en consultas. |
| `tests/test_analysis.py` | Completar cobertura de banco, producto, moneda e identidad ambigua como defensa de dominio. |
| `tests/test_backup.py` | Verificar que backup y restauración conservan el esquema v3 y sus relaciones. |
| `README.md` | Documentar catálogo y análisis por cuenta. |
| `docs/database-schema.md` | Documentar esquema v3 y migración. |
| `docs/roadmap.md` | Actualizar el estado de la fase cuando su verificación concluya. |

## Modelo e interfaces

### Esquema SQLite v3

```text
accounts
- id TEXT PRIMARY KEY
- bank TEXT NOT NULL
- product TEXT NOT NULL
- currency TEXT
- masked_account_number TEXT
- identity_status TEXT NOT NULL CHECK (identity_status IN ('visible_mask', 'ambiguous'))
- created_at TEXT NOT NULL

statements
- campos actuales
- account_id TEXT NOT NULL REFERENCES accounts(id)
```

Se añadirá un índice para resolver historia por cuenta y período:

```sql
CREATE INDEX statements_account_period
ON statements(account_id, period_start, period_end, id);
```

Los ámbitos `visible_mask` tendrán unicidad por la tupla compatible mediante dos
índices parciales: uno sobre `(bank, product, currency,
masked_account_number)` cuando `currency IS NOT NULL`, y otro sobre `(bank,
product, masked_account_number)` cuando `currency IS NULL`. Así `NULL` no se
confunde con una cadena vacía. Los ámbitos `ambiguous` no compartirán esas
restricciones y se crearán por cartola. La validación estricta comprobará el SQL
y las columnas de ambos índices.

### Modelos de persistencia

Se añadirá `StoredAccountMetadata` con:

- `id`;
- `bank`, `product`, `currency`, `masked_account_number`;
- `identity_status`;
- `statement_count`;
- `period_start`, `period_end`.

`StoredStatement` no necesita exponer `account_id` al dominio normalizado. Los
métodos de repositorio relevantes serán:

- `list_accounts()`;
- `get_account(account_id)`;
- `history_for_account(account_id, from_date=None, to_date=None)`;
- asignación privada de cuenta dentro de `save()`;
- limpieza privada del ámbito huérfano dentro de `delete()`.

`history_for_anchor()` se eliminará al adaptar todos sus consumidores.

### Contrato HTTP

```text
GET /v1/accounts
GET /v1/analysis?account_id=<uuid>[&from=YYYY-MM-DD][&to=YYYY-MM-DD]
```

Respuesta del catálogo:

```json
{
  "accounts": [
    {
      "account_id": "uuid",
      "bank": "Banco de Chile",
      "product": "CUENTA VISTA",
      "currency": "CLP",
      "masked_account_number": "****1234",
      "identity_status": "visible_mask",
      "statement_count": 8,
      "period_start": "2025-01-01",
      "period_end": "2026-08-31"
    }
  ]
}
```

`scope` de análisis añade `account_id` y conserva los demás campos. En el
catálogo, `PESOS` se presenta como `CLP`; `NULL` o cadena vacía se presentan como
`null`; cualquier otro valor no vacío se conserva para que la UI pueda mostrarlo
y el análisis pueda rechazarlo explícitamente. No se cambia la moneda persistida.

## Migración a v3

La inicialización controlará una única transacción para toda la cadena requerida.
Los helpers de migración no abrirán transacciones ni confirmarán versiones por su
cuenta. Así, una base v1 que falle durante el paso v3 volverá completamente a v1,
incluido `user_version`.

La migración seguirá el patrón de reconstrucción recomendado por SQLite para
incorporar una FK `NOT NULL`:

1. Leer `user_version` y validar exactamente el esquema correspondiente, v1 o
   v2, antes de modificarlo.
2. Deshabilitar temporalmente enforcement de FK antes de abrir la transacción.
3. Abrir la única transacción de migración.
4. Si el origen es v1, crear y poblar clasificaciones como paso interno, sin
   confirmar aún ni cambiar definitivamente la versión.
5. Validar la forma lógica v2 alcanzada antes de continuar.
6. Crear `accounts` y una tabla nueva de cartolas con `account_id` obligatorio.
7. Crear un UUID por cada tupla visible distinta y uno por cada cartola ambigua.
8. Copiar todas las cartolas con su asignación, sin modificar IDs ni valores.
9. Sustituir la tabla de cartolas, recrear índices y mantener las FK de
   transacciones apuntando a `statements`.
10. Validar columnas, índices, restricciones, `foreign_key_check` y cantidades.
11. Establecer `PRAGMA user_version = 3` y confirmar la única transacción.
12. Reactivar FK para toda conexión posterior.

Un fallo debe revertir tablas, datos y versión original. Bases nuevas crearán
directamente v3; bases v1 ejecutarán los cambios lógicos de v2 y v3 dentro de la
misma transacción orquestada.

## Resolución y escritura

Al guardar una cartola visible, el repositorio buscará o creará dentro de la
misma transacción el ámbito por tupla exacta. La operación será segura ante
reintentos y concurrencia mediante la restricción única correspondiente. Una
cartola ambigua siempre crea su propio ámbito.

El catálogo se calculará con agregados SQL sobre `accounts` y `statements`, sin
cargar movimientos. Se ordenará por `period_end DESC`, `period_start DESC`,
`bank`, `product`, `account_id`. La historia aplicará `account_id` y, cuando
existan fechas, la intersección de períodos en SQL antes de reconstruir cartolas
completas. Su orden será `period_start`, `period_end`, `id`.

La API consultará primero `get_account(account_id)`: su ausencia produce `404`.
Después, una tupla vacía de `history_for_account()` representa únicamente un
rango sin cartolas intersectantes y produce `400`.

Al eliminar, se leerá el `account_id`, se borrará la cartola y luego se eliminará
la cuenta solo si no quedan referencias, todo en una transacción.

## Validación de API

La ruta de análisis usará una allowlist exacta de parámetros: `account_id`,
`from` y `to`. Cada parámetro escalar puede aparecer como máximo una vez. El UUID
se validará y normalizará antes de consultar.

- ausencia, duplicados, formato inválido o selectores obsoletos: `400` con
  `invalid_analysis_query`;
- ámbito inexistente: `404` con `account_not_found`;
- rango sin historia: `400` con `history_not_available`;
- incompatibilidad o solapamiento: `409` con `invalid_analysis_scope`.

La consulta del catálogo y el análisis exigirán los mismos mecanismos de acceso
que las cartolas.

## Dependencias y decisiones

- No se añaden dependencias.
- Se usa `uuid4` existente para IDs públicos aleatorios.
- No se añade un fingerprint del número completo.
- No se mantiene compatibilidad con `anchor_statement_id`, según decisión
  aprobada.
- `account_id` se añade durante serialización en API; no contamina las fórmulas
  puras del dominio de análisis.
- El catálogo no pagina en esta fase porque representa ámbitos deduplicados y la
  instalación local no tiene un límite funcional de cuentas definido. Si ese
  volumen aparece, una spec posterior definirá paginación explícita.

## Estrategia de pruebas

- Persistencia:
  - base nueva v3;
  - migración v1 a v3 y v2 a v3;
  - agrupación visible y aislamiento ambiguo;
  - agrupación concurrente con moneda nula;
  - rollback de origen v1 y v2 ante un fallo durante v3;
  - esquema futuro e incompleto;
  - catálogo agregado y orden estable;
  - historia por cuenta y rango sin N+1 fuera del ámbito;
  - eliminación parcial y final.
- Dominio:
  - incompatibilidad explícita de banco, producto, moneda y cuenta;
  - frontera compartida y solapamiento sin cambios.
- API:
  - autenticación del catálogo;
  - catálogo vacío y con múltiples ámbitos;
  - moneda `PESOS`, nula, vacía y no soportada en catálogo;
  - análisis completo y filtrado por `account_id`;
  - UUID inválido, inexistente y duplicado;
  - rechazo de `anchor_statement_id` y `statement_id`;
  - más de cien cartolas;
  - privacidad y consultas sin escritura.
- Backup:
  - copia consistente y restaurable de accounts, statements, transactions y
    classifications.
- Ejecutar suite Python completa y smoke de API antes de marcar la fase completa.

## Riesgos y migración

- La reconstrucción de `statements` tiene FK entrantes desde `transactions`; la
  secuencia debe probarse con `foreign_key_check` y rollback real.
- La máscara visible puede colisionar entre cuentas reales. La documentación
  describirá `account_id` como ámbito compatible, no identidad verificada.
- El cambio HTTP es incompatible. Backend y SPA no deben desplegarse en versiones
  cruzadas; la fase 13 debe completarse antes del siguiente despliegue de UI.
- Un catálogo sin paginación puede crecer, aunque elimina la duplicación por
  cartola. No se añadirá un límite silencioso.
- La limpieza de cuentas huérfanas debe compartir transacción con el borrado para
  evitar opciones vacías.
