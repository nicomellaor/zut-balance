# Catálogo local de comercios

Las reglas de categorización se distribuyen como recursos JSON locales dentro del
paquete. No se consultan servicios externos, no se editan desde la API y no se
derivan automáticamente de cartolas. El catálogo activo clasifica movimientos
nuevos al persistirlos; las clasificaciones históricas se conservan tal como se
guardaron.

## Versiones

`src/zut_balance/catalogs/categorization-v1.json` conserva las reglas iniciales.
`categorization-v2.json` es el catálogo activo. Los archivos publicados son
inmutables: si un cambio puede alterar categoría, comercio, clave canónica,
coincidencia o normalización, se debe crear una nueva versión de catálogo en vez
de editar una existente.

Una cartola nueva recibe la versión activa. Una carga deduplicada conserva la
clasificación que ya estaba persistida. Por ello, un análisis histórico puede
incluir versiones distintas y mostrar el aviso `limited_classification`; no se
reclasifica el historial automáticamente.

## Formato

Cada catálogo contiene una versión de esquema, una versión de ruleset y reglas
planas:

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

Los campos `merchant_name`, `merchant_key` y `movement_type` usan `null` cuando
no aplican. El cargador rechaza estructuras o campos desconocidos, claves JSON
duplicadas, patrones no normalizados, valores inválidos y dominios de coincidencia
duplicados antes de inicializar SQLite.

Los tipos de coincidencia son:

- `exact`: toda la glosa normalizada coincide.
- `prefix`: la glosa normalizada comienza con el patrón.
- `token_prefix`: un token normalizado comienza con el patrón; se limita a un
  único token alfanumérico.

La precedencia no depende del orden del archivo: `exact` precede a `prefix`, que
precede a `token_prefix`; dentro de cada tipo gana prioridad mayor y después el
`rule_id` lexicográficamente menor.

## Incorporar un comercio

1. Reunir glosas anonimizadas y representativas. No incluir cuentas, tarjetas,
   pedidos, personas, documentos, secretos ni datos financieros reales.
2. Confirmar la categoría y si la glosa identifica al comercio de forma
   inequívoca.
3. Normalizar el patrón con la misma regla del producto: mayúsculas, sin acentos,
   puntuación ni espacios repetidos.
4. Preferir una regla `exact`. Un prefijo o `token_prefix` exige evidencia de
   variantes y pruebas negativas que excluyan coincidencias accidentales.
5. Definir un `rule_id` estable en kebab-case y una clave canónica normalizada
   solo cuando exista una identidad de comercio confiable.
6. Añadir pruebas explícitas de resultados positivos, negativos y solapamientos
   de prioridad.
7. Crear una nueva versión de catálogo para cualquier resultado que cambie y
   conservar las versiones anteriores para auditoría.

No se debe usar un nombre genérico como comercio. Cuando solo se conoce una
categoría, `merchant_name` y `merchant_key` permanecen nulos para no fragmentar
el ranking de comercios.

## Reglas vigentes

El catálogo v2 identifica Cineplanet, Servicios Médicos, Unimarc y PedidosYa
cuando sus patrones aprobados coinciden. Indicadores de cine y café clasifican
débitos como `entretenimiento` y `alimentacion`, respectivamente, sin inventar
un comercio.

`PAGO:MERCADOPAGO...` en un débito se clasifica como `compras`, sin comercio
identificado. Esto representa un pago procesado cuya identidad subyacente es
incompleta; una regla futura solo puede superarla con evidencia del comercio y
categoría específicos. Una glosa sin el prefijo `PAGO` sigue sin categoría por
esta regla.
