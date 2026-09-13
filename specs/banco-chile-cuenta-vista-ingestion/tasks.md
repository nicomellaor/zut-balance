# Tareas: Ingesta de cartola Cuenta Vista Banco de Chile

- [x] Crear el proyecto Python 3.12 con configuración de paquete, `pypdf` y `pytest`.
  - Validación: instalación editable e importación correctas con Python 3.14.7, `pypdf 6.18.1` y `pytest 9.1.1`. Python 3.12 no está instalado en el entorno de validación.

- [x] Definir los modelos inmutables de cartola, resumen y transacción, junto con los errores de dominio.
  - Validación: 7 pruebas unitarias confirman inmutabilidad, campos opcionales, saldo informado en `0` y errores públicos esperados.

- [x] Implementar validación de PDF legible, no cifrado y con texto extraíble.
  - Validación: 4 pruebas distinguen la muestra válida de entradas corruptas, cifradas y sin texto mediante errores explícitos; suite completa: 11 pruebas aprobadas.

- [x] Implementar reconocimiento determinista del formato Cuenta Vista Banco de Chile.
  - Validación: la muestra se reconoce y un candidato con solo el nombre del banco, sin los demás marcadores, se rechaza como formato no soportado; suite completa: 13 pruebas aprobadas.

- [x] Implementar extracción y normalización de datos generales, período, paginación, resumen y número de cuenta enmascarado.
  - Validación: la muestra satisface CA-02, CA-03, CA-07, CA-08 y CA-14; número de cartola ausente se representa como `None` y la cuenta numérica se enmascara. Suite completa: 15 pruebas aprobadas.

- [x] Implementar extracción de la tabla de movimientos, reconstrucción de descripciones y normalización de fechas y montos.
  - Validación: la muestra satisface CA-04 a CA-06 y CA-10 a CA-13, con cinco débitos, un crédito y sin saldos inicial/final como transacciones; se valida una descripción partida. Suite completa: 17 pruebas aprobadas.

- [x] Implementar validación de completitud y conciliación general.
  - Validación: la muestra satisface CA-09; una tabla sin el abono final y un saldo final inconsistente se rechazan con `UnreliableExtractionError`. Suite completa: 20 pruebas aprobadas.

- [x] Integrar el parser en la interfaz pública del paquete y completar las pruebas de aceptación y regresión.
  - Validación: `pytest` pasa con 25 pruebas, cubre CA-01 a CA-16 y usa solo datos sintéticos o anonimizados; la interfaz pública rechaza una extracción parcial.

- [x] Revisar documentación de uso mínima y límites del formato soportado.
  - Validación: el README explica la interfaz pública, el formato admitido, los errores esperados y la exclusión de OCR, sin exponer datos sensibles; ejemplo ejecutado correctamente.
