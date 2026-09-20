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
antes de acceder. Siga [Confianza TLS en red privada](#confianza-tls-en-red-privada)
para exportarla e instalarla. No ignore advertencias TLS.

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

## Confianza TLS en red privada

La CA interna permite que Caddy emita certificados para el host privado
configurado. Trátela como material sensible de confianza: distribúyala solo a
equipos autorizados mediante un canal controlado. Nunca distribuya archivos de
`caddy-data` ni intente extraer la clave privada de Caddy.

### Exportar e identificar la CA

Con `caddy` activo, exporte su certificado raíz al directorio actual del host
Docker. El archivo no contiene secretos de aplicación, pero no debe sustituirse
por uno recibido de un origen no verificado:

```bash
docker compose cp \
  caddy:/data/caddy/pki/authorities/local/root.crt \
  ./zut-balance-caddy-root.crt
openssl x509 -in ./zut-balance-caddy-root.crt -noout \
  -subject -issuer -serial -fingerprint -sha256
```

Compare la huella SHA-256 con el operador del servidor mediante un canal
independiente antes de transferir e instalar el archivo en otro equipo. Si el
comando de copia falla, compruebe `docker compose ps`: Caddy debe haberse iniciado
al menos una vez para crear su CA.

La CA se conserva en el volumen `caddy-data` durante actualizaciones, reinicios y
`docker compose down`. `docker compose down -v` elimina ese volumen y genera una
CA nueva al volver a iniciar el stack; exporte, compruebe y distribuya la nueva
CA, y retire la anterior de los equipos autorizados.

### Instalar en el sistema

Transfiera `zut-balance-caddy-root.crt` al equipo autorizado después de comprobar
su huella. Ejecute solo el procedimiento correspondiente al sistema operativo.

**Windows (PowerShell como administrador)**

```powershell
$certificate = Import-Certificate `
  -FilePath "$PWD\zut-balance-caddy-root.crt" `
  -CertStoreLocation Cert:\LocalMachine\Root
$certificate.Thumbprint
```

Guarde el thumbprint mostrado para retirar exactamente ese certificado:

```powershell
Remove-Item "Cert:\LocalMachine\Root\<thumbprint>"
```

**macOS (Terminal con una cuenta administradora)**

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  ./zut-balance-caddy-root.crt
```

Para retirarlo, abra **Keychain Access**, seleccione el llavero **System**, busque
el sujeto mostrado por `openssl x509`, elimine ese certificado y autentíquese. Si
prefiere la terminal, obtenga primero su huella SHA-1 con
`security find-certificate -a -Z /Library/Keychains/System.keychain` y ejecute:

```bash
sudo security delete-certificate -Z <huella-sha1> \
  /Library/Keychains/System.keychain
```

**Debian y Ubuntu**

```bash
sudo install -m 0644 ./zut-balance-caddy-root.crt \
  /usr/local/share/ca-certificates/zut-balance-caddy-root.crt
sudo update-ca-certificates
```

Para retirarlo:

```bash
sudo rm /usr/local/share/ca-certificates/zut-balance-caddy-root.crt
sudo update-ca-certificates
```

**Fedora y RHEL**

```bash
sudo install -m 0644 ./zut-balance-caddy-root.crt \
  /etc/pki/ca-trust/source/anchors/zut-balance-caddy-root.crt
sudo update-ca-trust extract
```

Para retirarlo:

```bash
sudo rm /etc/pki/ca-trust/source/anchors/zut-balance-caddy-root.crt
sudo update-ca-trust extract
```

### Instalar en Firefox

Firefox puede usar un almacén de certificados distinto al del sistema. En cada
perfil de Firefox que no reconozca el sitio tras instalar la CA del sistema:

1. Abra **Configuración** > **Privacidad y seguridad** > **Certificados** >
   **Ver certificados**.
2. En **Autoridades**, seleccione **Importar** y elija
   `zut-balance-caddy-root.crt` cuya huella ya comprobó.
3. Marque **Confiar en esta CA para identificar sitios web** y confirme.
4. Para retirarla, vuelva a **Autoridades**, seleccione el certificado por el
   sujeto mostrado durante la inspección y use **Eliminar o no confiar**.

No acepte una excepción temporal ni continúe si Firefox muestra una advertencia.
Una advertencia después de importar la CA suele indicar un host distinto a
`ZUT_BALANCE_HOST`, una CA anterior o que Firefox usa otro perfil.

### Verificar la confianza

En un equipo con acceso al servidor, defina explícitamente el host y puerto que
configuró en `.env`; no cargue `.env` como script porque contiene secretos.

```bash
host=balance.intranet
port=443
curl --fail --cacert ./zut-balance-caddy-root.crt \
  "https://${host}:${port}/health"
```

El comando debe devolver correctamente la respuesta de `/health`. Debe fallar si
el archivo de CA es incorrecto, el host no coincide con el certificado o el
servidor no está disponible. No use `--insecure`, `-k` ni excepciones del
navegador. Finalmente abra la misma URL HTTPS en el navegador y confirme que no
aparece una advertencia de certificado.

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
