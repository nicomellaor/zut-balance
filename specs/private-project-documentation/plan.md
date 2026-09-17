# Plan técnico: documentación para proyecto privado

## Enfoque técnico

La fase reorganiza la documentación existente sin cambiar código ni contratos. El
README se reduce a una entrada orientada a uso y mantenimiento internos; los
detalles de despliegue permanecen en `docs/deployment.md`. Un documento de
arquitectura y otro de privacidad centralizan afirmaciones que hoy están
dispersas entre README, roadmap y especificaciones.

## Componentes

| Ubicación | Cambio |
| --- | --- |
| `README.md` | Reestructurar como introducción, capacidades, límites, inicio rápido y mapa documental. |
| `docs/architecture.md` | Describir componentes, flujo de datos, límites operativos y enlaces a especificaciones. |
| `docs/privacy.md` | Documentar retención, autenticación, datos sensibles y responsabilidades del operador. |
| `specs/private-project-documentation/tasks.md` | Registrar implementación y verificación. |

## Interfaces y datos

No se crean interfaces, modelos ni migraciones. Los comandos documentados deben
coincidir con `pyproject.toml`, `frontend/package.json`, `compose.yaml` y
`docs/deployment.md`.

## Decisiones

- La documentación interna se mantiene en español.
- No se crea archivo `LICENSE`: se indicará que el repositorio es privado y no
  autoriza distribución o contribución pública.
- No se crean documentos de contribución pública ni de reporte externo de
  vulnerabilidades.
- La guía Docker mantiene el TLS interno vigente y no recomienda ignorar
  advertencias de certificado.

## Estrategia de verificación

- Revisar que todos los enlaces Markdown locales resuelvan a archivos existentes.
- Buscar secretos y datos prohibidos en los documentos nuevos o modificados.
- Comparar comandos y variables con los archivos de configuración vigentes.
- Ejecutar `git diff --check`; no se requieren pruebas de código por tratarse de
  documentación, pero se ejecutarán las comprobaciones documentales.

## Riesgos

- La documentación privada no sustituye un procedimiento interno para incidentes
  de seguridad o privacidad.
- Las instrucciones pueden quedar obsoletas si cambian Compose, el frontend o
  las variables de entorno; sus archivos fuente deben seguir siendo la referencia
  durante revisiones futuras.
