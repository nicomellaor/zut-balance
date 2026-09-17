# Tareas: operación local persistente

- [x] 1. Configurar reinicio de servicios de larga vida.
  - Validación: `compose.yaml` declara `restart: always` solo para `caddy` y
    `api`; `backup` conserva perfil `manual` y no declara reinicio automático.

- [x] 2. Extender el smoke test de Compose.
  - Validación: el test comprueba la configuración efectiva, reinicia `api`,
    recupera `/health` por HTTPS y conserva las comprobaciones de backup y puerto
    privado de API.

- [x] 3. Documentar operación persistente.
  - Validación: la guía distingue inicio, estado, reinicio del host,
    actualización, parada intencional y conservación de volúmenes.

- [x] 4. Verificar la fase completa.
  - Validación: `docker compose --env-file tests/compose.env config`, el smoke
    test Compose y `git diff --check` terminan correctamente; se comprueban
    CA-01 a CA-05 de la especificación.
