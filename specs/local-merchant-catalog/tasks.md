# Tareas: catálogo local de comercios y categorías

- [x] 1. Crear los catálogos versionados y configurar su empaquetado.
  - Validación: `categorization-v1.json` reproduce las cuatro reglas vigentes,
    `categorization-v2.json` contiene las reglas aprobadas y el paquete instalado
    puede leer ambos recursos mediante `importlib.resources`.

- [x] 2. Implementar carga y validación estricta del catálogo.
  - Validación: pruebas rechazan JSON y estructura inválidos, claves duplicadas,
    dominios repetidos, patrones no normalizados, prioridades booleanas, enums y
    comercios incompletos; un fallo ocurre antes de mutar SQLite temporal.

- [x] 3. Adaptar el clasificador al catálogo activo.
  - Validación: v1 conserva exactamente resultados actuales; v2 aplica Unimarc,
    PedidosYa, MercadoPago, cine y café con coincidencia, tipo de movimiento,
    precedencia y fallback definidos, sin depender del orden del catálogo.

- [x] 4. Verificar persistencia, API y análisis con versiones mixtas.
  - Validación: nuevas cargas persisten versión 2, deduplicación conserva v1,
    contratos HTTP usan expectativas explícitas y análisis/señales reportan las
    dos versiones sin reclasificar datos existentes.

- [x] 5. Documentar mantenimiento y decisión de MercadoPago.
  - Validación: la guía de catálogo explica evidencia, formato, inmutabilidad y
    adición de versiones; arquitectura y roadmap reflejan reglas locales y
    MercadoPago como `compras` sin comercio, sin contradicciones.

- [x] 6. Verificar la fase completa.
  - Validación: `pytest`, instalación o build del paquete, `bash
    scripts/smoke-compose.sh` y `git diff --check` pasan; se comprueban CA-01 a
    CA-10 sin dependencias, endpoints ni migración SQLite nuevos.
