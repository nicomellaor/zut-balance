# Tareas: layout v2 de Cuenta Vista Banco de Chile

- [x] 1. Registrar la muestra v2 como fixture anonimizada y fijar su resultado esperado.
  - Validación: prueba directa fija metadatos, resumen y seis movimientos de RF-02 a RF-04.

- [x] 2. Añadir reconocimiento automático y extracción determinista del layout v2.
  - Validación: v2 se procesa; marcador o fila ambigua produce error de dominio seguro.

- [x] 3. Reutilizar validaciones comunes y preservar privacidad, saldo cero y conciliación.
  - Validación: se cumplen CA-02, CA-04, CA-05 y CA-06 sin cambiar los modelos públicos.

- [x] 4. Añadir pruebas negativas v2 y regresiones de las variantes existentes.
  - Validación: encabezados o filas ambiguas se rechazan y fase 1/2 conserva resultados.

- [x] 5. Cubrir upload, persistencia y deduplicación de v2 mediante API.
  - Validación: CA-09 compara parser directo, POST autenticado y segunda carga.

- [x] 6. Actualizar documentación, ejecutar suite y verificar criterios.
  - Validación: README declara v2 y `pytest` pasa con 77 pruebas.
