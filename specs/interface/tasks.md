# Tareas: interfaz web local

- [x] 1. Inicializar la SPA React/Vite en `frontend/` con TypeScript estricto,
  Material UI, MUI X Charts y scripts de calidad separados.
  - Validación: instalación limpia, servidor de desarrollo y build de producción
    funcionan sin alterar dependencias Python.

- [x] 2. Configurar CORS explícito en FastAPI y documentar configuración de
  origen y URL base sin secretos.
  - Validación: pruebas API prueban origen permitido, origen no permitido y
    ausencia de wildcard; el ejemplo de entorno no contiene claves.

- [x] 3. Implementar sesión local en memoria y cliente tipado de la API.
  - Validación: solicitudes autenticadas usan Bearer, `401` limpia la sesión y
    ninguna prueba encuentra la clave en almacenamiento web, URL o logs.

- [x] 4. Implementar carga, historial paginado y detalle de cartola.
  - Validación: pruebas unitarias cubren carga única, estados, navegación,
    paginación y tabla con movimientos/clasificaciones autenticados.

- [x] 5. Implementar borrado con confirmación e invalidación de estado.
  - Validación: cancelar no llama API; confirmar elimina cartola de historial,
    detalle y selección/análisis.

- [x] 6. Implementar asistente de selección y rango de análisis.
  - Validación: propone unión de períodos, detecta incompatibilidad/solape local,
    respeta límites y comunica errores de ámbito del backend.

- [x] 7. Implementar dashboard accesible de métricas y gráficos.
  - Validación: resumen, cobertura, mensual, categorías, comercios y recurrencias
    representan respuestas válidas, vacías y parciales con alternativa tabular.

- [x] 8. Añadir pruebas E2E y responsive para flujos completos.
  - Validación: Playwright cubre acceso, carga, detalle, análisis, borrado,
    `401`, teclado y viewport móvil contra una API temporal configurada.

- [x] 9. Actualizar documentación y verificar CA-01 a CA-10.
  - Validación: README, `frontend/README.md` y roadmap se actualizan solo tras
    pruebas Python/frontend/E2E y Verify `PASS`.
