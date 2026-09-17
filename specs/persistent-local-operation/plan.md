# Plan técnico: operación local persistente

## Enfoque técnico

La fase modifica únicamente la política de reinicio de los servicios Compose de
larga vida. `caddy` y `api` recibirán `restart: always`; `backup` conservará su
perfil `manual`, su comando one-shot y no declarará política de reinicio.

El smoke test existente extenderá su comprobación de configuración para confirmar
las políticas efectivas y reiniciará `api` de forma controlada después de que el
stack esté disponible. El mismo endpoint HTTPS ya usado por el smoke test
confirmará que el proxy y la API vuelven a estar operativos.

La guía de despliegue separará inicio, estado, comportamiento tras un reinicio
del host, actualización y parada intencional. Aclarará que `docker compose down`
detiene y elimina los contenedores, por lo que un operador debe ejecutar `up -d`
para levantarlos de nuevo; los volúmenes se conservan salvo `down -v`.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `compose.yaml` | Añadir `restart: always` a `caddy` y `api`, sin cambiar `backup`, redes, puertos ni volúmenes. |
| `scripts/smoke-compose.sh` | Validar las políticas renderizadas por Compose y comprobar recuperación HTTPS después de `compose restart api`. |
| `docs/deployment.md` | Documentar estado, reinicio automático, actualización, parada y persistencia de volúmenes. |
| `specs/persistent-local-operation/tasks.md` | Registrar implementación y verificación. |

## Interfaces y datos

No cambian modelos, endpoints, variables de entorno, secretos, redes, puertos ni
esquema SQLite. La interfaz operativa conserva `docker compose up --build -d`,
`docker compose ps`, `docker compose restart` y `docker compose down`.

## Dependencias y decisiones

- Requiere Docker Engine configurado para arrancar en el host y Docker Compose
  v2; Compose no puede iniciar contenedores si el daemon no arranca.
- Se usa `always`, como exige la especificación, no `unless-stopped` ni un
  mecanismo de supervisión adicional.
- El reinicio de `api` es suficiente para la prueba de recuperación porque Caddy
  mantiene su certificado y proxy en ejecución; no se modifica el modelo TLS.
- `backup` no se incorpora a la prueba de reinicio: se verifica como servicio
  manual y su ejecución explícita existente se conserva.

## Estrategia de pruebas

- Ejecutar `docker compose --env-file tests/compose.env config` y comprobar que
  `caddy` y `api` declaran `restart: always`, mientras `backup` no lo declara y
  mantiene `profiles: [manual]`.
- Ejecutar `bash scripts/smoke-compose.sh`; tras iniciar el stack, reiniciar
  `api`, esperar su recuperación y volver a consultar `/health` mediante la CA
  interna ya obtenida.
- Confirmar que el smoke test conserva el backup manual y la ausencia de puerto
  publicado para la API.
- Ejecutar `git diff --check` y revisar la guía contra los comandos Compose
  definidos.

## Riesgos y migración

- `restart: always` no corrige fallos de configuración, secretos inválidos o un
  esquema SQLite incompatible; esos contenedores seguirán fallando y requerirán
  intervención del operador.
- Una parada intencional y eliminación con `docker compose down` evita que el
  stack quede activo; la guía debe explicar cómo levantarlo nuevamente.
- No hay migración de datos: los volúmenes nombrados y el procedimiento de
  backup permanecen sin cambios.
