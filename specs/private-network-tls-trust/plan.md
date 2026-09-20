# Plan técnico: TLS confiable en red privada

## Enfoque técnico

La fase conserva el modelo `tls internal` de Caddy y documenta su operación
manual. La guía usará `docker compose cp` para exportar la CA desde el
contenedor en ejecución, en vez de referirse a la ubicación física y dependiente
del entorno de los volúmenes Docker. El archivo origen es el certificado raíz
que Caddy conserva en `/data/caddy/pki/authorities/local/root.crt`.

Después de exportarlo, la guía hará que el operador inspeccione sujeto, emisor y
huella SHA-256 con `openssl x509`. La comparación de la huella se realizará por
un canal independiente antes de instalar el archivo en un equipo autorizado.
La documentación tratará la CA raíz como material sensible de confianza, aunque
no sea una clave privada ni un secreto de aplicación.

La guía organizará la instalación y retiro por destino: almacén raíz del sistema
en Windows, macOS, Debian/Ubuntu y Fedora/RHEL, y almacén propio de Firefox. La
verificación tendrá dos niveles: `curl --cacert` contra `/health` para comprobar
el archivo exportado y el certificado servido, y una visita del navegador sin
advertencia para comprobar el almacén elegido. No se usarán excepciones de
navegador ni opciones que omitan TLS.

La automatización existente ya cubre la parte reproducible del servidor: el
smoke test inicia Caddy, exporta el mismo `root.crt` con Compose y ejecuta
`curl --cacert` contra `/health`. Se conservará y se ejecutará como regresión;
la instalación en almacenes de cliente se valida manualmente porque requiere un
equipo autorizado y privilegios de su sistema.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `docs/deployment.md` | Sustituir la indicación genérica de confiar la CA por procedimientos de exportación, identificación, instalación, retiro y verificación por plataforma y Firefox. |
| `scripts/smoke-compose.sh` | Sin cambio funcional previsto; conservar su extracción de `root.crt` y validación `curl --cacert` como regresión automatizada. |
| `compose.yaml` y `Caddyfile` | Sin cambios: mantienen los volúmenes persistentes de Caddy y `tls internal`. |
| `specs/private-network-tls-trust/` | Registrar requisitos, plan, tareas y resultados de validación de la fase. |

## Interfaces y datos

No cambian endpoints, modelos, imágenes, variables de entorno, puertos, redes,
volúmenes ni el esquema SQLite.

La interfaz operativa documentada será:

- Exportación: `docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt <archivo-local>`.
- Inspección: `openssl x509 -in <archivo-local> -noout -subject -issuer -fingerprint -sha256`.
- Verificación del archivo: `curl --fail --cacert <archivo-local> https://<host>:<puerto>/health`.
- Almacenes de confianza: comandos nativos con privilegio administrativo cuando
  corresponda y los controles de certificados de Firefox para su almacén propio.

La guía no debe cargar `.env` como script de shell porque contiene valores con
formato de shell y secretos. El operador sustituirá explícitamente host y puerto
configurados en sus comandos de verificación.

## Dependencias y decisiones técnicas

- `docker compose cp` permite exportar la CA sin depender del driver de volumen,
  de rutas de Docker Desktop o de permisos directos sobre el host Docker.
- `openssl` se usa para mostrar metadatos y huella del certificado PEM sin
  modificarlo; Docker/Caddy siguen siendo la fuente de la CA.
- `curl --cacert` valida la cadena y el nombre HTTPS servido contra la CA
  exportada. No demuestra que el almacén del sistema o Firefox quedó instalado,
  por lo que se complementa con una comprobación de navegador.
- La distribución continúa manual y por equipo autorizado. MDM, GPO y rotación
  de CA no se introducen sin una necesidad operativa concreta.
- El certificado de sitio sigue siendo generado por Caddy para
  `ZUT_BALANCE_HOST`; acceder por otro host o IP puede fallar aunque la CA esté
  confiada.

## Estrategia de pruebas

- Ejecutar `bash scripts/smoke-compose.sh` para comprobar que el certificado raíz
  se puede copiar desde Caddy y valida `/health` mediante `curl --cacert`, sin
  `--insecure`, además de las regresiones de login, Bearer, backup y puerto API.
- Revisar los comandos documentados para confirmar que la exportación apunta al
  archivo raíz persistido de Caddy y que el comando `openssl` muestra sujeto,
  emisor y huella SHA-256.
- En un equipo autorizado por cada familia de sistema aplicable, seguir el
  procedimiento de instalación, abrir la URL HTTPS configurada en un navegador y
  confirmar ausencia de advertencia. Repetir la comprobación en Firefox cuando
  use almacén propio.
- Retirar la CA de un equipo de prueba y confirmar que el navegador vuelve a
  rechazar el certificado, antes de reinstalarla o retirar el equipo de la red.
- Ejecutar `git diff --check` y revisar que no se añadieron certificados, claves,
  secretos, puertos ni instrucciones de omisión TLS.

## Riesgos y migración

- La CA se conserva mientras exista `caddy-data`; `docker compose down -v` la
  elimina. Su regeneración invalida la confianza instalada en clientes y exige
  exportar y distribuir la nueva CA.
- Confiar una CA interna permite a quien controle su clave correspondiente emitir
  certificados aceptados por esos equipos. Por ello solo se distribuye en equipos
  autorizados y se retira al perder autorización.
- Firefox puede no usar el almacén del sistema, por lo que una instalación exitosa
  del sistema no sustituye su verificación específica.
- No hay migración de datos ni cambio de contrato. La fase solo amplía la guía y
  valida la operación existente.
