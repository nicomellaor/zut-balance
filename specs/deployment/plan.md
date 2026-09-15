# Plan técnico: despliegue Docker seguro

## Enfoque técnico

El despliegue de producción privada se compondrá de una imagen de aplicación
Python, una imagen de frontend construida con Vite y una imagen Caddy final que
sirve los estáticos y hace proxy inverso a la API. Docker Compose conectará Caddy
cliente con URL relativa `/v1`, por lo que producción no requiere API key en
navegador ni CORS.

FastAPI incorporará autenticación alternativa: Bearer para integraciones o
sesión firmada para navegador. `SessionMiddleware` manejará una cookie firmada
con el secreto de entorno, y Argon2 verificará la contraseña única. El validador
común de acceso dará precedencia a Bearer cuando exista; si no, verificará la
sesión. Mutaciones con sesión exigirán Origin configurado. Login/logout serán
las únicas rutas de autenticación nuevas.

El backup será un comando Python que usa `sqlite3.Connection.backup()` contra
la base activa, escribiendo un archivo temporal y renombrándolo solo cuando la
copia termina. Un servicio Compose de perfil manual lo ejecutará con acceso de
solo lectura lógica al volumen de datos y escritura al volumen de backups.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `Dockerfile` | Crear imagen API no root con dependencias Python y comando Uvicorn interno. |
| `frontend/Dockerfile` | Construir SPA Vite con URL relativa para producción. |
| `Caddyfile` | TLS interno, estáticos SPA, fallback de ruta y proxy `/v1/*` a API. |
| `compose.yaml` | Definir Caddy, API, backup, red interna y volúmenes nombrados. |
| `.env.example` | Documentar configuración sin secretos reales. |
| `src/zut_balance/auth.py` | Crear verificación Argon2, estado de sesión y comprobación de Origin. |
| `src/zut_balance/api.py` | Cargar ajustes seguros, rutas login/logout y autorización dual. |
| `src/zut_balance/backup.py` | Ejecutar backup SQLite consistente y restauración asistida si procede. |
| `pyproject.toml` | Añadir dependencia Argon2 justificada. |
| `tests/test_auth.py` y `tests/test_api.py` | Probar login, cookie, expiración, Origin, Bearer y configuración. |
| `tests/test_backup.py` | Probar copia consistente y restaurabilidad con SQLite temporal. |
| `scripts/` | Añadir smoke test Compose y generador seguro de secretos. |
| `README.md`, `docs/deployment.md` | Documentar operación, CA interna, volúmenes, backup y restauración. |

## Modelo e interfaces

### Configuración

`ServiceSettings` incorporará, además de la configuración actual:

- `admin_password_hash`: hash Argon2 obligatorio en modo Compose.
- `session_secret`: secreto de firma obligatorio, con longitud mínima validada.
- `trusted_origins`: origen HTTPS esperado para sesión y mutaciones.
- `session_max_age_seconds`: fijo en `28800` para esta fase.
- `cookie_secure`: verdadero en Compose; desarrollo separado conserva una ruta
  de configuración explícita que no degrada el stack Docker.

La carga de configuración falla con un error de inicio seguro si faltan secretos
o son inválidos. No se imprime su contenido.

### Autenticación HTTP

- `POST /v1/auth/login`: cuerpo JSON con contraseña, respuesta `204` al éxito y
  cookie de sesión; `401` seguro al fallo.
- `POST /v1/auth/logout`: elimina cookie, devuelve `204` y es idempotente.
- Rutas de datos: Bearer válido o sesión válida; Bearer inválido no permite
  fallback a una sesión incidental.
- Rutas mutantes por sesión (`POST`, `DELETE`): exigen `Origin` exacto de
  `trusted_origins`. Bearer no depende de Origin.
- `/health`: permanece público y no entrega detalles de secretos o DB.

### Compose

- `caddy`: publica `443`, monta configuración y contenido SPA de solo lectura.
- `api`: no publica puertos, monta `zut-data`, recibe `.env` y se comunica solo
  por red interna.
- `backup`: perfil manual, monta `zut-data` y `zut-backups`; se invoca con
  `docker compose run --rm backup`.
- Volúmenes nombrados: `zut-data`, `zut-backups` y almacenamiento de CA/Caddy.

## Decisiones técnicas

- Caddy usa `tls internal` para el host privado. No se habilita HTTP de datos ni
  CORS wildcard en Compose.
- La sesión será una cookie firmada sin datos sensibles, limitada a un flag de
  administrador y vencimiento. Logout elimina navegador; revocación de sesiones
  individuales queda fuera de alcance.
- Argon2 se consume mediante `argon2-cffi`; se verifican hashes con
  `PasswordHasher`, sin comparar contraseñas manualmente.
- `ZUT_BALANCE_API_KEY` conserva contratos Bearer para integraciones. La SPA
  elimina input, estado, cliente Bearer y cualquier referencia a esa variable.
- Todas las solicitudes SPA usan rutas relativas y `credentials: "same-origin"`.
- La Caddy CA debe instalarse manualmente en clientes de red privada; la guía no
  debe sugerir ignorar errores de certificado.
- SQLite se opera con una API única. Copias se hacen con la API de backup de
  SQLite, nunca con `cp` sobre una base activa.
- Restaurar requiere detener Compose, verificar la fuente, reemplazar la base y
  reiniciar; no se automatiza en un contenedor activo.

## Estrategia de pruebas

- Unitarias de Argon2 para hash válido, contraseña errónea y hash malformado.
- API: login, sesión, logout, cookie segura, sesión alterada/expirada, Origin
  permitido/no permitido, Bearer válido/inválido y ausencia de secretos.
- Regresión: rutas existentes mantienen contratos cuando se autentican por
  sesión o Bearer; CORS explícito de desarrollo sigue sin wildcard.
- Backup: crear DB temporal activa, guardar cartolas, ejecutar backup,
  abrir copia y comprobar filas/esquema; simular destino inválido.
- Imagen: build reproducible de API y SPA; inspeccionar que `.env` no está en
  contextos ni capas de imagen.
- Compose smoke test: levantar stack aislado, resolver HTTPS con CA confiada,
  login, cargar/consultar datos, usar Bearer, ejecutar backup y comprobar que
  la API no está publicada en puertos host.

## Riesgos y migración

- La fase cambia el mecanismo de acceso web y por tanto actualiza la interfaz de
  fase 8; clientes Bearer existentes permanecen compatibles.
- Cookies `Secure` requieren TLS. La configuración Compose no debe tener un
  bypass HTTP; desarrollo usa el flujo separado existente.
- TLS interno requiere distribuir una CA a cada dispositivo autorizado. Sin esa
  confianza, los navegadores rechazarán correctamente el sitio.
- SQLite con un volumen único no permite réplicas API. La necesidad de alta
  disponibilidad o más escritura concurrente inicia una fase de PostgreSQL.
- Los backups en volumen local no protegen contra pérdida del host; exportación,
  retención y cifrado son operación posterior explícita.
