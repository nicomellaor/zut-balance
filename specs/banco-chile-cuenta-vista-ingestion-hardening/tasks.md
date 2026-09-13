# Tareas: Robustecimiento de ingesta Cuenta Vista Banco de Chile

- [x] Añadir la dependencia de desarrollo para generar fixtures y crear el
  generador reproducible de PDFs sintéticos.
  - Validación: el generador produce PDFs digitales legibles con `pypdf` y no
    introduce dependencias de producción; `reportlab` quedó solo en `dev`.

- [x] Crear y versionar los fixtures de la matriz aprobada: multipágina, cruce
  de año, columnas desplazadas y metadatos reordenados.
  - Validación: cada fixture tiene texto extraíble, marcadores esperados y la
    estructura de páginas definida en el plan; la prueba del generador pasó.

- [x] Implementar clasificación de páginas y validación de paginación física y
  declarada.
  - Validación: la cartola multipágina válida se acepta; páginas faltantes,
    duplicadas, desordenadas o con total inconsistente se rechazan en pruebas.

- [x] Adaptar la extracción de metadatos y resumen para secciones distribuidas,
  repetidas y reordenadas.
  - Validación: se combinan metadatos de primera página y resumen final; los
    valores repetidos inconsistentes se rechazan en pruebas.

- [x] Reemplazar el parseo de tabla por página basado en offsets fijos por
  límites de columnas resueltos desde cada encabezado.
  - Validación: la variante de columnas desplazadas produce el resultado
    esperado; columnas ausentes o ambiguas se rechazan.

- [x] Implementar extracción multipágina de movimientos y continuación segura
  de descripciones.
  - Validación: los movimientos aparecen una sola vez y en orden; encabezados,
    pies y textos no transaccionales no contaminan las transacciones.

- [x] Validar períodos y normalizar fechas que cruzan de diciembre a enero.
  - Validación: las fechas de diciembre y enero reciben sus años correctos; los
    períodos inválidos o fechas ambiguas producen errores de dominio.

- [x] Añadir validación de evidencia documental de conteos o totales y mantener
  la conciliación general.
  - Validación: la cartola multipágina concilia y una omisión que contradice la
    evidencia declarada se rechaza.

- [x] Completar pruebas de regresión, aceptación y determinismo para CA-01 a
  CA-19.
  - Validación: `pytest` pasa con 48 pruebas y cada fixture se procesa dos veces
    con resultados normalizados iguales.

- [x] Actualizar README y roadmap cuando la verificación confirme la fase 2.
  - Validación: la documentación enumera solo las variantes realmente
    implementadas y conserva las limitaciones fuera de alcance.
