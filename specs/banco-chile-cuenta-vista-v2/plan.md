# Plan técnico: layout v2 de Cuenta Vista Banco de Chile

## Enfoque técnico

Se conservará `parse_banco_chile_cuenta_vista` como interfaz pública y se
extenderá su reconocimiento interno para distinguir el layout original de v2.
No se añadirá un parámetro de formato ni un dispatcher general: ambos layouts
representan el mismo banco y producto, y el parser debe reconocerlos
automáticamente por sus marcadores estructurales.

La variante v2 tendrá extracción de tabla y resumen específica cuando su
encabezado dividido no pueda resolverse por el extractor actual. Compartirá la
validación de PDF digital, normalización de fechas y montos, enmascaramiento,
validación de filas y conciliación existentes. La selección solo continuará
cuando las etiquetas y la estructura requerida sean inequívocas.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `src/zut_balance/banco_chile_cuenta_vista.py` | Añadir reconocimiento v2 y extracción fiable de metadatos, resumen y tabla v2. |
| `tests/test_banco_chile_cuenta_vista.py` | Añadir resultado esperado exacto para la muestra v2 y regresiones existentes. |
| `tests/test_banco_chile_hardening.py` | Añadir rechazos de marcadores, columnas o filas v2 ambiguas. |
| `tests/test_api.py` | Comprobar que el endpoint autenticado procesa y deduplica v2 con el mismo contrato. |
| `media/cartola_v2_ejemplo_banco_chile.pdf` | Mantener la muestra anonimizada aportada como fixture de referencia. |
| `README.md` | Declarar el layout v2 como formato soportado y sus límites explícitos. |
| `docs/roadmap.md` | Marcar fase 5 completada solo tras Verify `PASS`. |

## Modelo e interfaces

- `Statement`, `StatementSummary` y `Transaction` no cambian.
- El formato se determina internamente a partir de texto extraído y estructura
  de columnas; la API sigue enviando solo el archivo multipart `file`.
- Los seis números de documento de v2 se representan como `None`.
- El repositorio SQLite no requiere cambios: recibe el mismo modelo
  normalizado y mantiene la huella del PDF v2 para deduplicación.

## Decisiones

- Se usa la muestra v2 anonimizada como contrato observable, no como evidencia
  de que todos los layouts reales de Cuenta Vista estén soportados.
- El reconocimiento no se basa solo en `BANCO DE CHILE` o `CUENTA VISTA`; exige
  marcadores de las secciones y de la tabla v2.
- Una tabla donde las columnas partidas no permitan asignar sin ambigüedad cada
  monto a cargo, abono o saldo se rechaza.
- No se introduce una arquitectura de registro de parsers hasta que exista otro
  banco o producto concreto que la justifique.

## Estrategia de pruebas

- Ejecutar el parser sobre v2 y comparar cada campo con RF-02 a RF-04.
- Confirmar conciliación, fechas de 2026, valores cero y enmascaramiento.
- Confirmar que textos personales, cabeceras y pie legal no aparecen en la
  respuesta normalizada.
- Probar manipulación o doubles de texto para encabezado dividido incompleto,
  columna ambigua y fila incompleta.
- Ejecutar las pruebas de la muestra original y la matriz fase 2 para detectar
  regresiones.
- Ejecutar v2 mediante la API y comprobar igualdad con parser directo y
  deduplicación por bytes.
- Ejecutar toda la suite `pytest`.

## Riesgos

- El orden de texto de `pypdf` puede variar con cambios de versión; los tests
  fijarán el resultado sobre la versión declarada y la extracción deberá fallar
  de forma segura ante una estructura no determinable.
- La muestra contiene solo una página y no aporta un conteo total de
  movimientos; la conciliación no permite detectar omisiones compensadas.
- La muestra debe permanecer anonimizada; si se detecta información real, debe
  reemplazarse antes de incluirla en pruebas o documentación.
