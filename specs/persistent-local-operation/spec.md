# Operación local persistente

## Objetivo

Hacer que los servicios web de larga vida del despliegue Docker se recuperen
automáticamente después de reinicios del host o fallos del contenedor, sin
convertir el backup manual en un proceso persistente.

## Contexto

El stack Compose tiene los servicios `caddy`, `api` y `backup`. Los dos primeros
sirven la aplicación y la API de forma continua; `backup` se ejecuta bajo un
perfil manual y termina al completar una copia consistente de SQLite.

## Alcance

- Configurar una política Compose de reinicio automático para `caddy` y `api`.
- Mantener `backup` como servicio one-shot bajo perfil manual, sin política de
  reinicio automático.
- Documentar inicio, comportamiento después de reiniciar el host, actualización,
  parada intencional y conservación de volúmenes.
- Verificar la configuración renderizada por Docker Compose y el comportamiento
  de los servicios de larga vida.

## Fuera de alcance

- Programar, automatizar, retener, cifrar o copiar backups fuera del host.
- Añadir orquestadores, alta disponibilidad, múltiples réplicas o reemplazar
  SQLite.
- Cambiar la política de TLS, autenticación, secretos, red o puertos publicados.
- Reiniciar automáticamente un comando `docker compose run` de backup.

## Requisitos funcionales

### RF-01: Servicios persistentes

`caddy` y `api` deben declarar la política `restart: always` en Compose. Tras
un reinicio del daemon Docker o del host, Docker debe volver a iniciar esos
contenedores si el stack se había iniciado previamente y no fue detenido de
forma intencional.

### RF-02: Backup manual

`backup` debe conservar su perfil `manual`, comando one-shot y ausencia de
reinicio automático. La ejecución mediante `docker compose run --rm backup`
debe continuar siendo explícita.

### RF-03: Operación documentada

La guía de despliegue debe explicar cómo iniciar el stack en segundo plano,
comprobar su estado, actualizarlo, detenerlo intencionalmente y volver a
levantarlo. Debe indicar que los volúmenes persisten salvo que se eliminen
explícitamente.

## Requisitos no funcionales

- No se deben publicar puertos adicionales ni modificar las redes privadas.
- La configuración no debe incluir secretos ni cambiar los volúmenes existentes.
- La política debe ser observable mediante la configuración efectiva de Compose.

## Criterios de aceptación

- **CA-01:** `docker compose config` muestra `restart: always` para `caddy` y
  `api`.
- **CA-02:** `docker compose config` no asigna reinicio automático a `backup` y
  conserva su perfil manual.
- **CA-03:** Un reinicio controlado de `caddy` o `api` devuelve el servicio a un
  estado operativo sin intervención manual adicional.
- **CA-04:** La guía de despliegue explica los efectos de inicio, reboot,
  actualización y parada sobre los contenedores y datos persistentes.
- **CA-05:** El smoke test Compose vigente continúa pasando sin exponer puertos
  de API ni alterar el procedimiento de backup.

## Casos límite

- El operador ejecuta `docker compose down` antes de reiniciar el host.
- El host reinicia mientras existen datos en el volumen SQLite.
- El contenedor `api` falla al iniciar por configuración o esquema incompatible.
- El comando de backup termina correctamente o falla: no debe entrar en un bucle
  de reinicios.

## Supuestos

- Docker Engine está configurado para iniciar en el host y Docker Compose v2 está
  disponible.
- La persistencia de datos depende de los volúmenes nombrados existentes, no de
  la política de reinicio.
- El operador conserva control del host y puede detener los servicios de forma
  intencional para mantenimiento.

## Preguntas abiertas

- ¿Se requiere más adelante una política de salud y alerta para fallos repetidos
  de `api` o `caddy`?
