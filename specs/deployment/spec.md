# Despliegue Docker seguro para red privada

## Objetivo

Entregar un despliegue reproducible, seguro y operable de Zut Balance para una
red privada: SPA y API bajo un mismo origen HTTPS, autenticación de operador con
sesión de servidor, API key reservada para integraciones y datos SQLite
persistentes con respaldo consistente.

## Contexto

La fase 8 ejecuta Vite y FastAPI como procesos separados, requiere exportar
variables por terminal y pide la API key en la SPA. Ese modelo es válido para
desarrollo local, pero no protege una clave de integración si la interfaz se
usa desde otros equipos ni simplifica el despliegue repetible.

Esta fase reemplaza el inicio de acceso descrito en RF-01 de
`specs/interface/spec.md`: la SPA dejará de solicitar o transmitir la API key.
Los endpoints de datos conservarán sus contratos funcionales, pero aceptarán
una sesión web válida o una API key Bearer de integración.

## Alcance

- Definir un stack Docker Compose con Caddy, API y servicio de backup one-shot.
- Servir la SPA compilada y las rutas `/v1` desde el mismo origen HTTPS mediante
  Caddy con TLS interno para la red privada.
- No publicar el puerto de la API ni el archivo SQLite directamente al host o la
  red; solo Caddy expone HTTPS.
- Reemplazar acceso web con API key por login de un único administrador y cookie
  de sesión `HttpOnly`, `Secure`, `SameSite=Strict`, de duración máxima 8 horas.
- Verificar la contraseña del administrador contra un hash Argon2 definido como
  secreto de entorno.
- Mantener `ZUT_BALANCE_API_KEY` para clientes máquina-a-máquina mediante
  `Authorization: Bearer`, con acceso total inicial a las rutas de datos.
- Validar `Origin` confiable en mutaciones autenticadas por sesión.
- Usar volumen Docker persistente para SQLite y un comando Compose de backup
  consistente hacia un volumen de respaldos.
- Proveer `.env.example`, generación documentada de secretos y guía de inicio,
  actualización, backup y restauración.

## Fuera de alcance

- Exposición pública a Internet, certificados públicos, DNS externo, OAuth, SSO
  o gestión corporativa de certificados.
- Registro de usuarios, más de un administrador, roles, recuperación de
  contraseña, MFA, revocación de sesiones individuales o auditoría de acceso.
- Rotación automática de secretos, gestor externo de secretos, Docker Swarm o
  Kubernetes.
- Varias réplicas de API, clustering de SQLite o migración a PostgreSQL.
- Programación automática de respaldos, retención, cifrado de backups o copia
  fuera del host.
- Cambiar las reglas de clasificación, los datos persistidos o fórmulas de
  análisis.

## Requisitos funcionales

### RF-01: Stack Compose y red

`docker compose up --build` debe levantar Caddy y la API en una red interna. La
API no debe declarar puertos publicados. Caddy debe servir los archivos
compilados de la SPA y reenviar `/v1/*` a la API interna. La SPA de producción
debe usar rutas del mismo origen y no depender de `VITE_API_BASE_URL` ni CORS.

El stack debe soportar un solo proceso API. Caddy debe emitir TLS mediante su CA
interna para el host privado configurado. La documentación debe explicar cómo
confiar esa CA en los dispositivos autorizados.

### RF-02: Variables y secretos

El stack debe cargar un archivo `.env` no versionado. Debe rechazarse una
configuración de producción que carezca de cualquiera de estos secretos:

- `ZUT_BALANCE_ADMIN_PASSWORD_HASH`: hash Argon2 de la contraseña del único
  administrador.
- `ZUT_BALANCE_SESSION_SECRET`: secreto criptográfico de sesión.
- `ZUT_BALANCE_API_KEY`: credencial Bearer para integraciones.

`ZUT_BALANCE_HOST` debe contener el host HTTPS privado. La ruta SQLite dentro
del contenedor, orígenes confiables para solicitudes web y ubicación de backup
deben ser configurables sin incluir secretos en la imagen. `.env.example` solo
debe declarar nombres y valores de ejemplo no utilizables.

### RF-03: Sesión de administrador

`POST /v1/auth/login` debe aceptar una contraseña de administrador, verificarla
con Argon2 y crear una sesión web firmada que expira a las 8 horas como máximo.
La respuesta no debe revelar si falta configuración, si la contraseña fue
incorrecta ni contener secretos.

`POST /v1/auth/logout` debe invalidar la sesión en el navegador mediante la
eliminación de su cookie. Todas las rutas de datos deben aceptar una sesión web
válida. Una sesión ausente, inválida o expirada debe devolver el error seguro de
autenticación existente.

La cookie debe usar `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/` y no debe
contener contraseña, API key ni datos de cartolas. Para métodos que mutan datos,
la API debe rechazar sesiones cuyo encabezado `Origin` no coincida con el origen
HTTPS privado configurado.

### RF-04: API key de integración

Las rutas de datos deben seguir aceptando `Authorization: Bearer` con
`ZUT_BALANCE_API_KEY`. La API key y una sesión de administrador tienen acceso
total inicial para cargar, leer, analizar y eliminar. `/health` sigue público.

La SPA no debe almacenar, solicitar ni enviar API keys. En el despliegue Compose
no se debe publicar CORS permissivo; clientes de integración de la red privada
usan la API HTTPS de Caddy con Bearer.

### RF-05: Persistencia y backup

SQLite debe vivir en un volumen Docker nombrado persistente, accesible solo por
la API y el proceso de backup. Eliminar o recrear contenedores sin eliminar el
volumen debe conservar cartolas y clasificaciones.

`docker compose run --rm backup` debe producir un backup consistente de SQLite
sin copiar el archivo de base directamente mientras la API está activa. Debe
escribir el resultado con marca de tiempo en un volumen de backups y devolver
error explícito si no puede completarlo. La documentación debe incluir
restauración desde un backup con el stack detenido.

### RF-06: Operación y actualización

La guía debe cubrir instalación de Docker Compose, creación de `.env`, generación
de hash Argon2/secreto/API key, inicio, acceso HTTPS, actualización de imágenes,
backup, restauración y parada del stack. Debe advertir que SQLite no permite
escalado horizontal y que el directorio o volúmenes del host contienen datos
financieros sensibles.

## Requisitos no funcionales

### RNF-01: Seguridad de red

Solo Caddy expone un puerto de red. La comunicación Caddy-API permanece en la
red Docker interna. La API no debe confiar en encabezados de proxy no
configurados ni permitir un origen CORS wildcard en Compose.

### RNF-02: Secretos y privacidad

Secretos no aparecen en Dockerfile, imágenes, artefactos Vite, logs, respuestas
HTTP, repositorio ni `.env.example`. La contraseña solo se entrega a login sobre
HTTPS. El hash Argon2, el secreto de sesión y API key se mantienen fuera del
control de versiones con permisos restrictivos.

### RNF-03: Integridad y disponibilidad

Una inicialización o actualización debe validar el esquema SQLite existente. El
backup usa el mecanismo de copia consistente de SQLite. Fallos de autenticación,
backup o configuración no deben dejar una sesión válida parcial ni corromper
datos.

### RNF-04: Testabilidad

Autenticación, expiración, logout, Origin, API key, configuración ausente y
backup deben probarse con datos sintéticos. Un smoke test Compose debe verificar
HTTPS, login, una solicitud de datos autenticada y ausencia de puerto API
publicado.

## Criterios de aceptación

- **CA-01:** Compose expone solo Caddy, sirve SPA y `/v1` bajo el mismo host
  HTTPS y la API no tiene puertos publicados.
- **CA-02:** Una configuración sin hash Argon2, secreto de sesión o API key se
  rechaza antes de aceptar rutas de datos.
- **CA-03:** Login con contraseña correcta establece una cookie segura de máximo
  8 horas; contraseña incorrecta no establece sesión ni revela secretos.
- **CA-04:** Una sesión válida accede a todas las rutas de datos; logout,
  expiración o cookie inválida resultan en `401` seguro.
- **CA-05:** Mutaciones autenticadas por sesión con Origin faltante o no confiable
  se rechazan; el Origin HTTPS configurado se acepta.
- **CA-06:** Una API key Bearer válida conserva acceso total para integración y
  una inválida devuelve `401`; la SPA compilada no contiene ni pide esa clave.
- **CA-07:** El volumen SQLite conserva datos tras recrear contenedores sin
  borrarlo; el volumen no se publica como archivo HTTP ni como puerto API.
- **CA-08:** El servicio `backup` genera un archivo SQLite restaurable y
  consistente mientras la API está activa.
- **CA-09:** `.env.example`, Dockerfiles, documentación e imágenes no incluyen
  secretos reales, y la guía cubre generación y permisos de `.env`.
- **CA-10:** Pruebas Python y smoke tests Compose cubren autenticación, proxy,
  almacenamiento, backup y configuración; no se habilita CORS wildcard.

## Casos límite

- Contraseña vacía, hash Argon2 inválido, secreto de sesión demasiado corto o
  API key ausente.
- Cookie alterada, expirada, sin `Secure` bajo HTTP o enviada con Origin ajeno.
- Solicitud de integración con Bearer malformado o ambos mecanismos presentes.
- Caddy no puede resolver host interno, certificado interno no confiado por un
  cliente o API no disponible al iniciar proxy.
- Volumen SQLite preexistente con esquema futuro o incompatible.
- Backup sin espacio, archivo destino existente, API escribiendo o restauración
  intentada con el stack activo.
- `.env` con permisos demasiado abiertos o accidentalmente incluido en build.

## Supuestos

- El operador controla una red privada y puede instalar la CA interna de Caddy
  en los equipos autorizados.
- Un administrador único es suficiente para la primera entrega.
- El host tiene Docker Engine y Docker Compose v2, con almacenamiento local para
  volúmenes persistentes y de backup.
- La API key de integración se entrega por un canal seguro a clientes de la red
  privada y se rota manualmente cuando sea necesario.

## Preguntas abiertas

- ¿Qué política de rotación y custodia se requerirá cuando más de un sistema use
  la API key de integración?
- ¿Cuándo se necesitarán roles, varios operadores, revocación de sesión o MFA?
- ¿Qué destino fuera del host y retención se requerirán para backups operativos?
- ¿Qué umbral de uso justificará migrar de SQLite a PostgreSQL?
