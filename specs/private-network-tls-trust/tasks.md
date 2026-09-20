# Tareas: TLS confiable en red privada

- [x] 1. Documentar exportación e identificación de la CA de Caddy.
  - Validación: la guía exporta `root.crt` mediante `docker compose cp`, muestra
    sujeto, emisor y huella SHA-256 con `openssl`, y explica la persistencia y
    regeneración de la CA sin exponer rutas de volumen del host.

- [x] 2. Documentar confianza y retiro por equipo autorizado.
  - Validación: la guía contiene procedimientos separados para Windows, macOS,
    Debian/Ubuntu, Fedora/RHEL y Firefox, con instalación, retiro y confianza de
    sitios web en el almacén propio de Firefox.

- [x] 3. Documentar verificación y límites de seguridad.
  - Validación: la guía prueba `/health` con `curl --cacert`, exige comprobar el
    navegador sin advertencias ni excepciones TLS, y limita la distribución a
    equipos autorizados.

- [x] 4. Verificar la fase completa.
  - Validación: `bash scripts/smoke-compose.sh` y `git diff --check` terminan
    correctamente; se comprueban CA-01 a CA-07. La validación manual local
    confirmó que Firefox acepta `https://localhost:8443` sin advertencias TLS.
