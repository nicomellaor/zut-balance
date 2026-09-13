# Plan técnico: Ingesta de cartola Cuenta Vista Banco de Chile

## Enfoque técnico

Implementar una librería Python 3.12 sin API ni interfaz. La librería recibirá el contenido o la ruta de un PDF y devolverá un modelo estructurado de cartola, o un error de dominio explícito cuando no pueda procesarlo de forma segura.

Se usará `pypdf` para validar y extraer texto del PDF. El parser será específico para el layout inicialmente soportado y se organizará en etapas deterministas:

1. Validar que el archivo sea un PDF legible, no cifrado y con texto extraíble.
2. Extraer el texto de todas las páginas en modo que conserve la disposición, cuando esté disponible.
3. Confirmar el formato mediante varios marcadores estructurales, no solo el nombre del banco.
4. Separar encabezado, tabla de movimientos, resumen de retenciones y pie de página.
5. Extraer datos generales, resumen y filas de movimientos.
6. Normalizar fechas, montos y campos opcionales.
7. Enmascarar el número de cuenta antes de construir el resultado público.
8. Comprobar la conciliación general y rechazar una extracción incompleta o inconsistente.

La librería no persistirá documentos ni datos extraídos. El PDF sintético existente será el fixture de aceptación inicial; no se incorporarán cartolas reales.

## Componentes

Se crearán los siguientes componentes en un paquete `src/zut_balance/`:

- `models.py`: modelos inmutables para cartola, resumen y transacción.
- `errors.py`: errores de dominio para PDF inválido, PDF protegido, documento sin texto, formato no soportado y extracción no confiable.
- `banco_chile_cuenta_vista.py`: detección, extracción, normalización, conciliación y función pública del parser.
- `__init__.py`: exportaciones públicas mínimas.

También se crearán:

- `pyproject.toml`: metadatos del proyecto, requerimiento Python 3.12 y dependencias de ejecución y prueba.
- `tests/`: pruebas unitarias y de integración con el PDF sintético y fixtures generados en las pruebas.

No se modificarán el PDF sintético, el código de aplicación inexistente ni documentos fuera de esta feature salvo que una tarea aprobada lo requiera.

## Modelos e interfaces

La interfaz pública será una única función que procese una ruta o contenido binario de PDF y devuelva una cartola normalizada. El nombre y la firma exactos se definirán durante la implementación de la tarea correspondiente, manteniendo estos contratos:

- `Statement`: banco, producto, número de cuenta enmascarado, moneda, período, número de cartola opcional, paginación, resumen y transacciones.
- `StatementSummary`: saldo inicial, saldo final, retenciones y saldo disponible, usando enteros en pesos chilenos.
- `Transaction`: fecha completa, descripción original, número de documento opcional, sucursal o canal opcional, monto entero no negativo, tipo `debit` o `credit` y saldo informado opcional.
- Los campos opcionales ausentes se representarán explícitamente como ausencia, no como valores inventados.
- Un resultado exitoso siempre estará conciliado cuando la cartola tenga los datos necesarios. Los errores de entrada o extracción se comunicarán mediante excepciones de dominio, nunca mediante resultados parciales exitosos.

Los tipos de movimiento usarán identificadores estables en inglés (`debit` y `credit`); las descripciones extraídas conservarán el texto original del documento.

## Dependencias y decisiones técnicas

- Python 3.12: versión base aprobada.
- `pypdf`: única dependencia de producción para inspeccionar estructura y extraer texto de PDFs digitales.
- `pytest`: dependencia de desarrollo para pruebas reproducibles.
- `dataclasses` y módulos estándar: modelos, fechas, expresiones regulares y validaciones sin dependencias adicionales.
- No se añadirá OCR, base de datos, framework web, IA ni librería de logging externo, porque están fuera del alcance.
- Los montos se guardarán como enteros de CLP para evitar ambigüedad decimal.
- El parser extraerá por secciones y columnas reconocidas; no usará un modelo de IA ni heurísticas genéricas para otros layouts.
- La detección requerirá una combinación de marcadores como `Banco de Chile`, `Estado de Cuenta`, `CUENTA VISTA`, período y encabezados de la tabla de movimientos.

## Estrategia de pruebas

- Prueba de integración sobre `media/cartola_ejemplo_banco_chile.pdf` que cubra CA-01 a CA-14, incluidas las seis transacciones, el saldo `0` del 27/08 y la conciliación general.
- Pruebas unitarias para normalización de montos CLP, enmascaramiento de cuenta, determinación de año y reconstrucción de descripciones partidas.
- Pruebas de rechazo usando PDFs mínimos generados temporalmente por las pruebas para documento corrupto, cifrado, sin texto o formato no soportado. No usar información bancaria real.
- Pruebas de extracción no confiable para filas incompletas y conciliación general inconsistente.
- Ejecutar `pytest` y una comprobación de importación del paquete antes de completar cada tarea que cambie comportamiento.

## Riesgos y migraciones

- El orden de texto extraído puede variar por versión de `pypdf` o por el generador del PDF. Las pruebas deben fijar el comportamiento del fixture y el parser debe rechazar datos no determinables.
- La marca de agua puede intercalarse con filas al extraer texto. El parser debe delimitar la tabla y filtrar contenido ajeno antes de normalizar.
- La muestra es de una página y no representa todas las variantes reales. Soporte multipágina, formatos posteriores y cruces de año se tratarán como extensiones con nueva especificación o actualización aprobada.
- Una cartola con saldo intermedio inusual sigue siendo válida si la conciliación general es correcta; el valor informado no se corregirá.
- No hay migraciones de datos: la primera versión no tiene persistencia ni un contrato público desplegado.
