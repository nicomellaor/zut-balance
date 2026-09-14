# Servicio de procesamiento de cartolas

## Objetivo

Exponer la ingesta validada de cartolas mediante un servicio HTTP que permita
enviar un PDF y recibir su resultado normalizado o un error seguro, sin
persistir el documento ni sus datos.

## Contexto

Las fases 1 y 2 entregan un parser determinista para las variantes aprobadas de
Cuenta Vista Banco de Chile. La fase 3 del roadmap incorpora el límite de
servicio necesario antes de añadir persistencia o una interfaz. El servicio no
debe ampliar los formatos soportados ni modificar el contrato de ingesta.

## Alcance

- Recibir un PDF en una solicitud de procesamiento.
- Validar el tipo, tamaño y cantidad de páginas de la entrada antes de informar
  éxito.
- Procesar exclusivamente el formato actualmente soportado mediante la API
  pública de ingesta.
- Devolver el resultado normalizado de la cartola en una respuesta estructurada.
- Devolver errores de entrada o de procesamiento con códigos HTTP y cuerpos
  estructurados, sin contenido sensible.
- Exponer una consulta no sensible del estado operativo del servicio.
- Documentar el contrato de solicitudes, respuestas, límites y errores.
- Mantener el procesamiento de cada solicitud aislado y sin persistencia.

## Fuera de alcance

- Persistencia de cartolas, movimientos, resultados, archivos temporales o
  historial de solicitudes.
- Consulta posterior de resultados por identificador.
- Otros bancos, productos o variantes no aprobadas de Cuenta Vista Banco de
  Chile.
- OCR, categorización, normalización de comercios, métricas, análisis e IA.
- Interfaz gráfica, cuentas de usuario, autorización o facturación.
- Procesamiento asíncrono, colas, reintentos o notificaciones.

## Requisitos funcionales

### RF-01: Procesamiento de PDF

El servicio debe ofrecer `POST /v1/statements`, que reciba exactamente un
archivo PDF y devuelva el resultado normalizado producido por la interfaz
pública de ingesta soportada.

### RF-02: Validación de entrada

El servicio debe rechazar una solicitud sin archivo, con más de un archivo, con
un tipo de contenido no PDF, con un archivo vacío o que supere los límites
documentados de tamaño o páginas. La solicitud rechazada no debe alcanzar el
parser de cartolas.

### RF-03: Respuesta exitosa

Una cartola válida y soportada debe devolver una respuesta estructurada que
represente sin pérdida el resultado normalizado público: metadatos, resumen y
movimientos. Los montos, fechas, tipos y ausencias deben conservar su semántica
normalizada.

### RF-04: Errores de procesamiento

Un PDF corrupto, cifrado, escaneado, no soportado o cuya extracción sea poco
fiable debe producir una respuesta de error de cliente estructurada. Un error
interno inesperado debe producir una respuesta de error de servidor
estructurada, sin exponer detalles de implementación.

### RF-05: Estado operativo

El servicio debe ofrecer una operación de consulta que permita comprobar que
está disponible sin requerir, aceptar o revelar datos de una cartola.

### RF-06: No persistencia

Tras finalizar una solicitud, el servicio no debe conservar el PDF recibido ni
el resultado normalizado. No debe existir una operación para recuperar una
cartola o resultado procesado anteriormente.

### RF-07: Contrato documentado

La documentación del servicio debe especificar operaciones, formato de carga,
estructura de respuestas exitosas y de error, códigos HTTP, límites de entrada
y el alcance de formatos soportados.

## Requisitos no funcionales

### RNF-01: Privacidad

- El contenido del PDF, descripciones de movimientos y número de cuenta no
  deben incluirse en logs, trazas ni mensajes de error.
- La respuesta no debe exponer un número de cuenta sin el enmascaramiento que
  entrega el parser.
- Las pruebas deben usar exclusivamente PDFs sintéticos o anonimizados.

### RNF-02: Seguridad de recursos

- Los límites de tamaño y páginas deben documentarse y aplicarse de forma
  determinista.
- Una entrada que exceda un límite debe rechazarse antes de realizar extracción
  completa del documento.

### RNF-03: Compatibilidad

- El servicio debe preservar el resultado de `parse_banco_chile_cuenta_vista`
  para un mismo PDF válido.
- No debe modificar modelos públicos ni comportamiento de la librería de
  ingesta.

### RNF-04: Determinismo y testabilidad

- Un mismo PDF válido debe producir respuestas exitosas equivalentes.
- Las respuestas de error esperables deben ser verificables mediante pruebas
  automatizadas.

## Criterios de aceptación

- **CA-01:** Una solicitud válida con el fixture sintético aprobado devuelve
  éxito y el mismo resultado normalizado que la llamada directa al parser.
- **CA-02:** Una solicitud sin archivo, con varios archivos, vacía o no PDF se
  rechaza con un error de cliente estructurado.
- **CA-03:** Un archivo que excede el límite documentado de tamaño se rechaza
  antes de invocar el parser.
- **CA-04:** Un PDF que excede el límite documentado de páginas se rechaza antes
  de invocar el parser.
- **CA-05:** Un PDF inválido o no soportado produce un error de cliente
  estructurado que no contiene texto extraído, número de cuenta ni detalles de
  biblioteca.
- **CA-06:** Un error interno inesperado produce un error de servidor
  estructurado que no contiene trazas ni datos del PDF.
- **CA-07:** La respuesta exitosa no expone más de cuatro dígitos consecutivos
  del número de cuenta.
- **CA-08:** La operación de estado responde sin aceptar ni revelar información
  de cartolas.
- **CA-09:** Una vez completada la respuesta, no existe un recurso u operación
  del servicio que permita recuperar el PDF o resultado de esa solicitud.
- **CA-10:** La documentación publicada describe el contrato, errores, límites
  y el único formato de cartola soportado.

## Casos límite

- Encabezado que declara PDF pero cuerpo vacío o no válido.
- Archivo cuyo nombre o tipo declarado no coincide con su contenido.
- PDF válido que supera el límite de páginas.
- PDF protegido, escaneado, corrupto o de un banco no soportado.
- Dos solicitudes con el mismo PDF.
- Error inesperado durante la serialización de una respuesta.
- Solicitud de estado con parámetros o cuerpo no relacionados con una cartola.

## Supuestos

- La fase 3 es síncrona y procesa una cartola por solicitud mediante
  `POST /v1/statements`.
- La fase 4 será responsable de cualquier persistencia y consulta histórica.
- El único formato procesable inicialmente es el de Cuenta Vista Banco de Chile
  definido por las fases 1 y 2.
- El servicio inicial no exige autenticación; el entorno de despliegue controla
  su exposición de red.
- El tamaño máximo por archivo es `10 MiB` y el máximo es `20` páginas.

## Preguntas abiertas

- ¿Qué consumidores requieren garantías adicionales de compatibilidad del
  contrato HTTP además de la ruta `POST /v1/statements`?
- ¿La consulta de estado debe ser pública o estar restringida al entorno de
  operación?
