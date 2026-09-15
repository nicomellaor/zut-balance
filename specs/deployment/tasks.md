# Tareas: despliegue Docker seguro

- [x] 1. Añadir configuración validada y utilidades de autenticación Argon2.
  - Validación: secretos faltantes o inválidos fallan sin filtrarse; hashes
    válidos y erróneos se distinguen solo mediante respuestas seguras.

- [x] 2. Implementar login, logout, sesión firmada de 8 horas y autorización
  dual de sesión/Bearer.
  - Validación: pruebas API cubren cookie segura, expiración, logout, Bearer
    válido/inválido y contratos de rutas de datos existentes.

- [x] 3. Proteger mutaciones de sesión mediante Origin confiable y adaptar la
  SPA al mismo origen con cookies.
  - Validación: POST/DELETE por sesión rechazan Origin ausente/ajeno, Bearer de
    integración mantiene acceso y el bundle no contiene ni solicita API key.

- [x] 4. Crear imágenes Docker de API y SPA, Caddyfile y Compose con red interna
  y volúmenes nombrados.
  - Validación: build Compose termina, solo Caddy publica `443`, HTTPS interno
    sirve SPA y proxy `/v1` sin CORS wildcard.

- [x] 5. Implementar backup SQLite consistente y servicio Compose one-shot.
  - Validación: backup durante operación contiene esquema y datos restaurables;
    errores de destino no corrompen la base activa.

- [x] 6. Añadir scripts de generación de hash/secreto/API key y `.env.example`.
  - Validación: no se versionan secretos, los valores generados cumplen los
    validadores y la configuración se puede iniciar sin exports manuales.

- [x] 7. Añadir pruebas de integración y smoke test Compose.
  - Validación: login, sesión, Bearer, HTTPS, proxy, volumen y backup pasan en
    un stack temporal con datos sintéticos.

- [x] 8. Actualizar documentación y verificar CA-01 a CA-10.
  - Validación: README, documentación de despliegue y roadmap se actualizan solo
    después de pruebas Python/frontend/Compose y Verify `PASS`.
