# Privacidad

## Datos procesados

Zut Balance recibe cartolas PDF digitales para extraer metadatos, saldos y
movimientos. Los resultados normalizados incluyen fechas, montos, descripciones,
referencias disponibles y clasificaciones derivadas. Las glosas y comercios
pueden revelar hábitos de consumo y deben tratarse como información financiera
sensible.

## Retención

El servicio no persiste el PDF original ni el texto extraído. SQLite conserva las
cartolas normalizadas, sus movimientos y clasificaciones hasta que un operador
las elimina. La eliminación de una cartola elimina en cascada sus movimientos y
clasificaciones asociadas.

Los backups SQLite también contienen estos datos. El operador decide su
ubicación, acceso, retención y eliminación; los backups no se cifran ni copian
fuera del host automáticamente.

## Protección operativa

- El despliegue Docker publica solo Caddy; la API y SQLite no exponen puertos al
  host o a la red.
- El acceso web usa una cookie `HttpOnly`, `Secure` y `SameSite=Strict`; las API
  keys son solo para integraciones.
- TLS usa la CA interna de Caddy en redes privadas. Los equipos autorizados deben
  confiar esa CA; no se deben ignorar advertencias de certificado.
- El archivo `.env`, los volúmenes Docker y el archivo SQLite requieren permisos
  restrictivos y no deben compartirse.

## Uso del repositorio

No agregue cartolas reales, glosas identificables, números de cuenta completos,
secretos, backups ni archivos `.env` al repositorio, issues, logs o ejemplos.
Use fixtures sintéticos o anonimizados. El repositorio es privado y los problemas
que puedan exponer datos o secretos deben tratarse por los mantenedores mediante
un canal privado acordado.
