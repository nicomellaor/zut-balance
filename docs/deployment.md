# Despliegue privado con Docker

El despliegue usa Caddy como único servicio publicado, con TLS emitido por su CA
interna. La API, SQLite y los backups permanecen en volúmenes Docker privados.
SQLite admite una sola instancia de API: no escale el servicio horizontalmente.

## Requisitos

- Docker Engine y Docker Compose v2.
- Un nombre o IP privada alcanzable por los equipos autorizados.
- Docker debe poder publicar el puerto `8443` del host para uso local.
- Python `>=3.12,<3.15` con las dependencias del proyecto, solo para generar
  secretos mediante los scripts incluidos.

## Configuración e inicio

```bash
python -m pip install -e .
cp .env.example .env
chmod 600 .env
python scripts/generate_secrets.py password-hash
python scripts/generate_secrets.py session-secret
python scripts/generate_secrets.py api-key
docker compose up --build -d
```

Pegue cada valor generado en su variable correspondiente de `.env` y configure
`ZUT_BALANCE_HOST`, `ZUT_BALANCE_HTTPS_PORT` y
`ZUT_BALANCE_TRUSTED_ORIGINS`. Nunca incluya `.env` en control de versiones,
imágenes ni mensajes. La contraseña se usa únicamente para el login web;
`ZUT_BALANCE_API_KEY` es exclusiva para integraciones con Bearer.
El generador de hash incluye comillas simples: consérvelas para que Docker Compose
preserve los signos `$` de Argon2.

Compruebe los servicios de larga vida con:

```bash
docker compose ps
```

`caddy` y `api` usan `restart: always`. Si Docker Engine inicia después de un
reinicio del host, o uno de esos contenedores termina inesperadamente, Docker
vuelve a iniciarlo. Esta política no corrige secretos, configuración o esquema
SQLite inválidos: esos fallos requieren intervención del operador. El servicio
`backup` permanece manual y solo se ejecuta mediante `docker compose run`.

Para uso local, el ejemplo configura `localhost` y puerto `8443`: abra
`https://localhost:8443`. No requiere modificar `/etc/hosts`. Caddy genera una
CA interna, por lo que cada equipo autorizado debe confiar su certificado raíz
antes de acceder. Obtenga el certificado desde el volumen `caddy-data` del host
Docker e instálelo mediante el mecanismo de confianza del sistema operativo. No
ignore advertencias TLS.

Para una red privada, use un nombre DNS interno o la IP privada del servidor.
Puede cambiar a puerto estándar `443` configurando, por ejemplo:

```dotenv
ZUT_BALANCE_HOST=balance.intranet
ZUT_BALANCE_HTTPS_PORT=443
ZUT_BALANCE_TRUSTED_ORIGINS=https://balance.intranet
```

La API no publica puertos. Los clientes de integración usan el mismo host HTTPS:

```bash
curl -H "Authorization: Bearer $ZUT_BALANCE_API_KEY" \
  https://localhost:8443/v1/statements
```

## Actualización

Antes de actualizar, ejecute un backup. Luego reconstruya y reinicie sin borrar
los volúmenes:

```bash
docker compose run --rm backup
docker compose up --build -d
```

## Parada intencional

Para detener y eliminar los contenedores del stack:

```bash
docker compose down
```

`down` conserva `zut-data` y `zut-backups`. No ejecute `down -v` salvo que quiera
eliminar permanentemente cartolas, clasificaciones, backups y la CA interna. Una
parada intencional con `down` elimina los contenedores, por lo que debe ejecutar
`docker compose up -d` para levantar el stack nuevamente; la política de reinicio
no recrea contenedores eliminados.

## Backup y restauración

El backup usa la API de copia consistente de SQLite y puede ejecutarse mientras
la API está activa:

```bash
docker compose run --rm backup
docker compose run --rm backup ls -l /var/backups/zut-balance
```

Para restaurar, detenga el stack primero. Identifique el volumen con
`docker volume ls`, copie un archivo backup validado sobre
`/var/lib/zut-balance/zut-balance.sqlite3` usando un contenedor temporal con el
volumen `zut-data`, y reinicie `docker compose up -d`. No reemplace el archivo
mientras la API está activa. Los volúmenes contienen datos financieros sensibles:
restrinja el acceso al host y mantenga copias externas según su política.

## Verificación del stack

El smoke test usa secretos sintéticos y un proyecto Docker aislado; construye el
stack, verifica TLS con la CA de Caddy, inicia sesión, consulta con sesión y
Bearer, ejecuta backup y comprueba que la API no publica puertos:

```bash
bash scripts/smoke-compose.sh
```

El smoke test usa el puerto `18443` por defecto para no interferir con un stack
local en `8443`. Puede cambiarlo mediante `ZUT_BALANCE_SMOKE_HTTPS_PORT` si ese
puerto también está ocupado.
