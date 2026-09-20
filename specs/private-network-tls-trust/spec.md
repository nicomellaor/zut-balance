# TLS confiable en red privada

## Objetivo

Permitir que los equipos autorizados de una red privada confíen de forma segura
en el certificado HTTPS emitido por la CA interna persistida de Caddy, incluida
la configuración de Firefox cuando usa un almacén de certificados propio.

## Contexto

El despliegue Docker publica Caddy como único punto de entrada HTTPS y configura
`tls internal`. Caddy conserva su autoridad raíz en el volumen nombrado
`caddy-data`, en
`/data/caddy/pki/authorities/local/root.crt` dentro del contenedor. La guía
actual indica que se debe confiar esa CA, pero no proporciona un procedimiento
operable para exportarla, instalarla, verificarla ni retirarla.

Firefox puede usar su almacén propio y no heredar la confianza del sistema
operativo. Por ello, confiar la CA en el sistema no basta para garantizar acceso
sin advertencias desde ese navegador.

## Alcance

- Documentar un procedimiento para exportar la CA raíz activa desde el servicio
  `caddy` en ejecución, sin acceder directamente a los archivos internos de los
  volúmenes Docker.
- Documentar cómo inspeccionar la identidad y huella SHA-256 de la CA exportada
  antes de distribuirla a un equipo autorizado.
- Documentar instalación y retiro de la CA para almacenes de confianza de
  Windows, macOS y las familias Linux Debian/Ubuntu y Fedora/RHEL.
- Documentar instalación y retiro en Firefox cuando use su almacén propio,
  incluyendo la confianza para identificar sitios web.
- Documentar comprobaciones observables de confianza: validación HTTPS con la
  CA exportada y navegación HTTPS sin ignorar advertencias de certificado.
- Aclarar que la CA es sensible para la seguridad de la red privada y que solo
  debe distribuirse a equipos autorizados mediante un canal controlado.
- Conservar una comprobación automatizada de Compose que extraiga la CA y valide
  el endpoint HTTPS con ella.

## Fuera de alcance

- Sustituir `tls internal`, emitir certificados públicos o solicitar certificados
  a una CA externa.
- Exponer el servicio a Internet, añadir DNS público o modificar puertos, redes,
  autenticación, cookies o secretos de aplicación.
- Automatizar la distribución de certificados mediante MDM, GPO, Ansible u otra
  gestión centralizada de equipos.
- Generar, rotar o revocar automáticamente la CA de Caddy.
- Confiar certificados de sitio individuales en lugar de la CA raíz interna.

## Requisitos funcionales

### RF-01: Exportación controlada

La guía debe indicar un comando Compose que copie
`/data/caddy/pki/authorities/local/root.crt` desde el contenedor `caddy` a un
archivo local elegido por el operador. Debe indicar que Caddy y su volumen
persistente deben estar activos, y que recrear el stack con `docker compose down
-v` elimina esa CA y exige repetir la distribución.

### RF-02: Identificación de la CA

La guía debe indicar cómo inspeccionar el sujeto, emisor y huella SHA-256 del
archivo exportado con herramientas locales. El operador debe poder comparar esa
huella por un canal independiente antes de instalar el certificado en otro
equipo autorizado.

### RF-03: Almacenes de confianza del sistema

La guía debe proporcionar pasos separados de instalación y retiro para Windows,
macOS, Debian/Ubuntu y Fedora/RHEL. Cada procedimiento debe instalar únicamente
la CA exportada en el almacén de autoridades raíz confiables del equipo y
requerir privilegios administrativos cuando el sistema lo necesite.

### RF-04: Firefox

La guía debe explicar que Firefox puede requerir la importación directa de la
CA en su almacén propio. Debe indicar la ruta de interfaz para importar y retirar
la CA, habilitar la confianza para identificar sitios web y verificar el acceso
al host HTTPS privado sin aceptar excepciones ni advertencias.

### RF-05: Verificación de confianza

La guía debe incluir una comprobación no interactiva que consulte `/health` por
HTTPS usando el archivo de CA exportado y una comprobación desde el navegador.
La comprobación debe fallar ante una CA incorrecta, un host no coincidente o un
servidor no disponible; no debe usar opciones que omitan la validación TLS.

### RF-06: Regresión automatizada

El smoke test Compose debe seguir obteniendo la CA desde Caddy y validando
`/health` mediante `curl --cacert`, sin usar `--insecure`. Debe seguir cubriendo
login, acceso autenticado, backup manual y ausencia de puerto publicado para la
API.

## Requisitos no funcionales

- La documentación no debe contener certificados, claves privadas, secretos ni
  huellas que se presenten como valores reutilizables.
- No debe instruir a ignorar advertencias TLS, crear excepciones permanentes ni
  desactivar la verificación de certificados.
- La exportación y los ejemplos deben usar rutas locales explícitas y no asumir
  acceso directo al directorio de volúmenes de Docker.
- Los procedimientos deben mantener el alcance de red privada y el principio de
  mínimo privilegio.

## Criterios de aceptación

- **CA-01:** La guía permite exportar desde un `caddy` activo el archivo raíz
  persistido por Caddy mediante Docker Compose.
- **CA-02:** La guía permite inspeccionar y comparar sujeto, emisor y huella
  SHA-256 de la CA antes de instalarla en otro equipo autorizado.
- **CA-03:** La guía contiene instrucciones de instalación y retiro para Windows,
  macOS, Debian/Ubuntu y Fedora/RHEL, sin requerir acceso al volumen Docker.
- **CA-04:** La guía contiene instrucciones específicas para importar, confiar y
  retirar la CA en Firefox cuando usa un almacén propio.
- **CA-05:** Un operador puede validar `/health` con `curl --cacert` y acceder
  desde un navegador autorizado sin advertencias ni excepciones TLS.
- **CA-06:** El smoke test Compose pasa usando la CA extraída de Caddy y no
  incluye una opción que omita validación TLS.
- **CA-07:** El despliegue conserva `tls internal`, no publica puertos nuevos y
  no añade certificados públicos, claves ni secretos al repositorio.

## Casos límite

- El operador intenta exportar la CA antes de iniciar `caddy` o después de haber
  eliminado sus volúmenes.
- El archivo copiado corresponde a otra instalación, fue sustituido o su huella
  no coincide con la comunicada por el operador del servidor.
- El host privado se accede por un nombre o IP distinto al configurado en
  `ZUT_BALANCE_HOST`.
- Firefox no usa el almacén del sistema o conserva una importación anterior tras
  que la CA de Caddy fue eliminada y regenerada.
- El equipo autorizado no tiene privilegios para modificar su almacén raíz.
- Un equipo deja de estar autorizado y requiere retirar la CA previamente
  instalada.

## Supuestos

- El operador controla el host Docker, los equipos autorizados y un canal seguro
  para comunicar huellas y transferir la CA.
- Los equipos autorizados disponen de herramientas nativas de gestión de
  certificados o acceso a la interfaz de Firefox.
- La CA de Caddy continúa persistida en `caddy-data` mientras no se elimine ese
  volumen explícitamente.

## Preguntas abiertas

- Ninguna para la operación manual de equipos autorizados. La distribución y
  rotación centralizadas se evaluarán si el número de equipos lo justifica.
