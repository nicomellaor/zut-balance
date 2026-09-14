# Plan técnico: servicio de procesamiento de cartolas

## Enfoque técnico

Se añadirá una aplicación HTTP síncrona basada en FastAPI que mantendrá el
transporte separado de la librería `zut_balance`. La aplicación expondrá:

- `POST /v1/statements`, con un único campo multipart llamado `file`.
- `GET /health`, sin entrada documental.

La ruta de procesamiento validará primero la solicitud y el tamaño del archivo
(`10 MiB`). Solo entonces leerá el contenido y contará las páginas con `pypdf`,
con un máximo de `20`. Un PDF que falle estas validaciones no se enviará al
parser. El contenido se mantendrá únicamente en memoria durante la solicitud y
se pasará a `parse_banco_chile_cuenta_vista`.

El resultado `Statement` se convertirá de forma explícita a JSON. Se utilizarán
fechas ISO 8601, montos como enteros y `null` para los campos opcionales
ausentes. No se cambiarán los modelos públicos existentes.

Los errores esperables de validación del PDF y de la extracción se convertirán
en un único cuerpo seguro de error de cliente. Los errores no esperados se
convertirán en un cuerpo seguro de error de servidor, sin trazas ni datos del
documento.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `pyproject.toml` | Añadir FastAPI, Uvicorn y la dependencia multipart requerida para recibir archivos. Añadir el cliente HTTP de pruebas al extra de desarrollo si FastAPI no lo provee transitivamente. |
| `src/zut_balance/api.py` | Crear la aplicación HTTP, constantes de límites, rutas, validación, serialización y manejadores de errores. |
| `src/zut_balance/__init__.py` | Mantener las exportaciones actuales; no hacer que la importación pública de la librería requiera usar la API. |
| `tests/test_api.py` | Cubrir contrato HTTP, límites, privacidad, mapeo de errores y ausencia de regresiones de parser. |
| `README.md` | Documentar instalación, ejecución, rutas, carga multipart, límites, respuestas y formato soportado. |

## Interfaces y contratos

### `POST /v1/statements`

- Entrada: `multipart/form-data`, exactamente un campo de archivo `file`.
- Límite de contenido: `10 * 1024 * 1024` bytes.
- Límite de documento: `20` páginas.
- Éxito: `200` con las secciones `metadata`, `summary` y `transactions` que
  reflejan el modelo `Statement`.
- Solicitud inválida o documento rechazado: `400` con `{"error": {"code":
  "...", "message": "..."}}`.
- Límite excedido: `413` con el mismo formato seguro de error.
- Error inesperado: `500` con el mismo formato seguro de error.

No se incorporarán identificadores, almacenamiento temporal controlado por la
aplicación ni rutas de lectura posteriores.

### `GET /health`

- Éxito: `200` con un estado no sensible que indique disponibilidad.
- No acepta ni procesa PDFs.

## Dependencias y decisiones

- FastAPI y Uvicorn se añaden como dependencias de producción porque el
  resultado de la fase es un servicio HTTP ejecutable y necesita soporte robusto
  de rutas, multipart y pruebas. `python-multipart` habilita la carga multipart
  declarada por el contrato.
- Se reutiliza `pypdf`, ya presente, para contar páginas antes del parser.
- No se añade base de datos, cola, almacenamiento de objetos, autenticación ni
  telemetría, pues pertenecen a fases posteriores o están fuera de alcance.
- La validación del límite de bytes se basará en el cuerpo leído de la solicitud,
  no solo en el encabezado `Content-Length`, que es controlado por el cliente.

## Estrategia de pruebas

- Probar `GET /health` y una carga válida con el fixture sintético ya aprobado.
- Comparar el JSON exitoso con el `Statement` obtenido directamente del parser.
- Probar solicitud sin archivo, varios archivos, archivo vacío, tipo no PDF,
  contenido no PDF, PDFs protegidos o no soportados y límite de tamaño.
- Crear o reutilizar un PDF sintético de más de 20 páginas para verificar el
  límite de páginas sin invocar el parser.
- Simular un error inesperado del parser para comprobar la respuesta `500` sin
  trazas ni contenido sensible.
- Verificar que números de cuenta, mensajes de error y respuestas no exponen
  datos sin enmascarar.
- Ejecutar toda la suite `pytest` para preservar la compatibilidad de fases 1 y
  2.

## Riesgos y migraciones

- El límite de páginas requiere abrir el PDF antes del parser; los documentos
  malformados se devolverán como errores de cliente sin exponer excepciones de
  `pypdf`.
- La carga multipart puede generar archivos temporales dentro de la infraestructura
  del framework durante la solicitud. La aplicación no guardará archivos ni
  expondrá rutas de recuperación; la política operativa del runtime debe cubrir
  la limpieza de temporales si existe almacenamiento efímero.
- El contrato JSON será la primera superficie pública externa. La ruta
  versionada `/v1` permite cambios incompatibles futuros mediante una versión
  nueva en lugar de alterar la respuesta actual.
- No hay migraciones de datos porque no se introduce persistencia.
