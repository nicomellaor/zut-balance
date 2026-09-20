# Plan técnico: catálogo local de comercios y categorías

## Enfoque técnico

La fase convierte las reglas embebidas actuales en recursos JSON instalados con el
paquete. Se mantendrá el módulo `categorization.py` como propietario único de la
normalización, carga, validación y comparación de reglas, evitando una capa de
configuración o una dependencia adicional.

El módulo leerá los recursos con `importlib.resources`, validará el JSON de forma
estricta y construirá un catálogo y reglas inmutables. El catálogo activo se
cargará y validará al importar el clasificador. Como `persistence.py` importa el
clasificador antes de construir `StatementRepository`, un catálogo empaquetado
inválido impide llegar a `initialize()` y, por tanto, evita una migración o
mutación de SQLite. Las funciones de carga también permanecerán invocables de
forma directa para probar catálogos inválidos sin tocar una base.

Se conservará la semántica actual para normalización y fallback. La regla tendrá
un tipo de coincidencia explícito y el comparador usará una clave estable:

```text
exact > prefix > token_prefix > prioridad descendente > rule_id ascendente
```

`token_prefix` dividirá la clave normalizada por espacios y comprobará que algún
token comienza con un único patrón alfanumérico. No se añadirán coincidencias por
substring arbitrario ni regex configurables.

El catálogo v1 será una representación exacta de las cuatro reglas existentes.
El v2, activo, conservará esas reglas y añadirá Unimarc, PedidosYa, MercadoPago,
cine genérico y café genérico con las restricciones de débito indicadas en la
especificación. Las clasificaciones ya materializadas continúan siendo
autoritativas: no cambia el esquema, no se migran filas ni se reclasifican
cartolas. La guía documentará que cambiar un resultado requiere crear una nueva
versión de catálogo, no editar v1 o v2 publicados.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/categorization.py` | Reemplazar `_RULES` embebidas por modelos inmutables, lectura de recursos JSON, validación estricta y comparador con `exact`, `prefix` y `token_prefix`. |
| `src/zut_balance/catalogs/categorization-v1.json` | Añadir la representación exacta y auditable de las reglas existentes de versión 1. |
| `src/zut_balance/catalogs/categorization-v2.json` | Añadir el catálogo activo de versión 2 con las reglas aprobadas. |
| `pyproject.toml` | Declarar los JSON de `catalogs/` como package data de `zut_balance`. |
| `tests/test_categorization.py` | Cubrir carga, validación, compatibilidad v1, reglas v2, prioridad y evidencia negativa. |
| `tests/test_persistence.py` | Verificar que nuevas cartolas guardan v2, filas históricas se preservan y cargas deduplicadas no se reclasifican. |
| `tests/test_api.py` | Añadir expectativas explícitas para clasificaciones v2, sin construirlas con el clasificador de producción. |
| `tests/test_analysis.py` y `tests/test_signals.py` | Comprobar que ámbitos con filas v1 y v2 exponen ambas versiones y mantienen el aviso de calidad. |
| `docs/merchant-catalog.md` | Documentar formato, evidencia requerida, reglas de versionado, límites y proceso de incorporación de comercios. |
| `docs/architecture.md`, `docs/roadmap.md` | Reflejar catálogo local activo y reemplazar explícitamente el fallback previo de MercadoPago por `compras` sin comercio. |
| `specs/local-merchant-catalog/tasks.md` | Registrar implementación y verificación de la fase. |

## Modelo e interfaces

### Recurso de catálogo

Cada catálogo JSON tendrá esta forma lógica:

```json
{
  "schema_version": 1,
  "ruleset_version": "2",
  "rules": [
    {
      "id": "unimarc",
      "category": "alimentacion",
      "match_type": "prefix",
      "pattern": "PAGO UNIMARC",
      "merchant_name": "Unimarc",
      "merchant_key": "UNIMARC",
      "priority": 10,
      "movement_type": "debit"
    }
  ]
}
```

Los campos de comercio y tipo de movimiento serán `null` cuando no apliquen. No
se usarán objetos anidados para que la validación, revisión de diferencias y
auditoría sigan siendo directas.

### Estructuras en memoria

`categorization.py` conservará una regla congelada y añadirá un contenedor
inmutable de catálogo. Una regla contendrá `id`, `category`, `pattern`,
`match_type`, `merchant_name`, `merchant_key`, `priority` y `movement_type`.
El catálogo contendrá `schema_version`, `ruleset_version` y una tupla de reglas.

`classify_transaction(transaction, classified_at)` conserva su firma y toma el
catálogo activo validado. Para pruebas unitarias, el clasificador o un helper
interno aceptará un catálogo explícito sin usar rutas de entorno ni modificar el
catálogo instalado.

No cambian `Classification`, `Transaction`, la tabla
`transaction_classifications`, el `SCHEMA_VERSION`, endpoints ni serialización.

### Validación

El cargador usará un detector de claves JSON duplicadas y verificará conjuntos
exactos de campos de catálogo y regla. Validará tipos antes de construir enums:
en especial, rechazará `bool` como prioridad. Un patrón debe ser idéntico a
`normalize_merchant_key(pattern)` y no quedar vacío. `token_prefix` exige un solo
token normalizado. Nombre y clave de comercio deben aparecer juntos, y la clave
debe ser canónica y normalizada.

El cargador rechazará dominios duplicados definidos por
`(match_type, pattern, movement_type)`. No rechazará todos los solapamientos de
prefijos porque la precedencia actual los resuelve y la validación profunda de
conflictos está reservada para fase 18; cada solapamiento intencional tendrá una
prueba de regresión.

## Reglas del catálogo v2

| ID | Tipo y patrón | Tipo de movimiento | Resultado |
| --- | --- | --- | --- |
| `cineplanet-webpay` | exact `PAGO CINEPLANET WEBPAY` | cualquiera, compatible con v1 | `entretenimiento`, Cineplanet / `CINEPLANET` |
| `servicios-medicos` | exact `PAGO SERVICIOS MEDICOS` | cualquiera, compatible con v1 | `salud`, Servicios Medicos / `SERVICIOS MEDICOS` |
| `transfer-out` | prefix `TRASPASO A` | cualquiera, compatible con v1 | `transferencias`, sin comercio |
| `transfer-in` | prefix `TRASPASO DE` | cualquiera, compatible con v1 | `transferencias`, sin comercio |
| `unimarc` | prefix `PAGO UNIMARC` | debit | `alimentacion`, Unimarc / `UNIMARC` |
| `pedidosya` | prefix `PAGO PEDIDOSYA` | debit | `alimentacion`, PedidosYa / `PEDIDOSYA` |
| `pedidosya-dl` | prefix `PAGO DL PEDIDOSYA` | debit | `alimentacion`, PedidosYa / `PEDIDOSYA` |
| `mercadopago-generic` | prefix `PAGO MERCADOPAGO` | debit | `compras`, sin comercio |
| `generic-cinema` | token_prefix `CINE` | debit | `entretenimiento`, sin comercio |
| `generic-cafe` | token_prefix `CAFE` | debit | `alimentacion`, sin comercio |

Los prefijos de comercio específicos tendrán prioridad superior a
`mercadopago-generic`; esta tendrá prioridad baja para que una regla futura,
basada en evidencia, identifique un comercio subyacente. Las reglas de
transferencia conservan prioridad 10. La prioridad precisa de reglas no
solapadas se mantendrá en cero para no atribuir significado a valores superfluos.

## Dependencias y decisiones

- Se usa JSON de biblioteca estándar, no YAML ni una nueva dependencia, para
  hacer la estructura portable y estrictamente validable.
- `importlib.resources` desacopla los recursos del directorio de trabajo y
  funciona tanto en desarrollo como tras `pip install .` y dentro de Docker.
- `pyproject.toml` declarará explícitamente los recursos porque el descubrimiento
  de paquetes por sí solo no garantiza incluir JSON en una distribución.
- v1 y v2 permanecerán en control de versiones. Solo v2 se carga en tiempo de
  ejecución; v1 se carga explícitamente en pruebas y queda para auditoría.
- No habrá selector de versión por entorno. Elegir o editar catálogos locales sin
  despliegue es responsabilidad futura de fase 18.
- El comportamiento nuevo de MercadoPago se documentará como decisión aprobada;
  `merchant_name` y `merchant_key` nulos preservan la cobertura de comerciantes
  y evitan crear un comercio ficticio.

## Estrategia de pruebas

- Cargar v1 y comprobar, con una tabla de resultados explícitos, equivalencia de
  categoría, comercio, clave, regla y versión con las cuatro reglas actuales.
- Cargar v2 y probar las variantes aprobadas de Unimarc, PedidosYa y MercadoPago,
  más cine, Cinemark, café y cafetería, con resultados explícitos.
- Probar negativos: créditos de las reglas nuevas, MercadoPago sin `PAGO`,
  `DESCAFEINADO`, desconocidos y transferencias que contienen palabras clave.
- Probar matriz de precedencia: exacta sobre prefijo, prefijo sobre token,
  prioridad, desempate por ID, filtrado por tipo de movimiento e independencia
  del orden del arreglo JSON.
- Parametrizar JSON inválidos para claves duplicadas, campos desconocidos,
  enums, prioridad booleana, patrones no normalizados, comercio incompleto,
  `token_prefix` inválido y dominios duplicados. Confirmar que el fallo sucede
  al cargar antes de crear o migrar una base temporal.
- Persistir una cartola nueva y comprobar `ruleset_version = "2"`; reutilizar una
  carga deduplicada v1 y comprobar que conserva `ruleset_version = "1"`.
- Construir un ámbito con datos v1 y v2 para confirmar que análisis y señales
  exponen ambas versiones y conservan `limited_classification`.
- Reemplazar expectativas tautológicas de API relevantes por valores literales.
- Ejecutar `pytest`, construir/instalar el paquete y ejecutar
  `bash scripts/smoke-compose.sh` para comprobar que Docker contiene y carga el
  catálogo activo.

## Riesgos y migración

- Editar v2 tras liberar resultados con versión `2` rompería trazabilidad entre
  reglas persistidas y catálogo; la documentación y revisión deben exigir v3 para
  cualquier cambio de resultado.
- No se migra SQLite. Una base histórica conserva versión 1; por ello un análisis
  que combine ambas versiones reportará la limitación ya prevista.
- Una base de esquema v1 que se abra por primera vez con la nueva aplicación no
  tiene clasificaciones previas y será clasificada con el catálogo activo v2.
- Un fallo de empaquetado puede impedir que la aplicación arranque, lo cual es
  preferible a clasificar con reglas ausentes; pruebas de recurso e imagen cubren
  ese riesgo.
- `token_prefix` mejora cobertura, pero debe mantenerse limitado a indicadores
  aprobados y acompañado de negativos para no ampliar categorías por coincidencia
  accidental.
