# Documentación para proyecto privado

## Objetivo

Convertir la documentación de Zut Balance en una entrada clara y profesional
para uso y mantenimiento internos, sin alterar su comportamiento ni exagerar sus
capacidades.

## Contexto

El README actual reúne descripción de producto, uso de biblioteca, API,
desarrollo de la SPA, límites y enlaces técnicos. La fase 14 del roadmap ordena
esa información para un proyecto que permanece privado y procesa solo formatos
bancarios explícitamente soportados.

## Alcance

- Reestructurar el README como punto de entrada con propósito, capacidades,
  límites, inicio rápido y enlaces a documentación detallada.
- Crear o actualizar documentación de arquitectura, despliegue y privacidad.
- Identificar explícitamente el estado privado del repositorio sin atribuir una
  licencia ni autorizar su distribución.
- Mantener las instrucciones de desarrollo y despliegue reproducibles, separando
  claramente los flujos locales y Docker.

## Fuera de alcance

- Cambios a código, contratos HTTP, Docker Compose o comportamiento de la SPA.
- Publicar el repositorio, crear guías de contribución pública, elegir una
  licencia o definir un canal público de vulnerabilidades.
- Incorporar soporte para bancos, productos, OCR, IA, servicios externos o
  nuevas reglas de categorización.
- Prometer soporte, SLA, compatibilidad o seguridad fuera de lo verificado.

## Requisitos funcionales

### RF-01: README de entrada

El README debe explicar en lenguaje directo qué resuelve Zut Balance, el banco y
producto actualmente soportados, su flujo de datos y sus límites principales.
Debe incluir rutas claras para instalación, uso de biblioteca, API, SPA de
desarrollo y despliegue privado.

### RF-02: Documentación navegable

La documentación debe enlazar desde el README a arquitectura, despliegue,
privacidad, roadmap y especificaciones relevantes. Los enlaces internos deben
ser relativos y válidos dentro del repositorio.

### RF-03: Uso privado de datos

La documentación debe exigir datos sintéticos o anonimizados en pruebas y
ejemplos, y prohibir incorporar cartolas, secretos, backups o datos financieros
reales al repositorio. Los incidentes que puedan exponer datos o secretos deben
tratarse mediante un canal privado acordado por los mantenedores.

### RF-04: Límites y estado del repositorio

La documentación debe declarar que el soporte actual se limita a las cartolas
digitales validadas de Cuenta Vista Banco de Chile y que no entrega asesoría
financiera. Debe indicar que el repositorio permanece privado y no está
autorizado para distribución o contribución pública.

## Requisitos no funcionales

- La documentación debe estar en español claro y conservar nombres técnicos,
  comandos y variables exactos.
- No debe incluir secretos, cartolas reales, cuentas completas, datos personales
  ni instrucciones que recomienden ignorar advertencias TLS.
- Las afirmaciones de seguridad, privacidad y soporte deben coincidir con la
  implementación y especificaciones vigentes.

## Criterios de aceptación

- **CA-01:** El README permite identificar propósito, formato soportado, límites
  y rutas de inicio sin recorrer especificaciones históricas.
- **CA-02:** Los enlaces del README hacia documentación de operación resuelven
  dentro del repositorio.
- **CA-03:** La documentación exige datos sintéticos o anonimizados y prohíbe
  incorporar datos financieros o secretos reales al repositorio.
- **CA-04:** La documentación distingue desarrollo local de despliegue Docker y
  no contradice la guía de despliegue.
- **CA-05:** El repositorio figura como privado, sin declarar una licencia ni
  autorizar distribución o contribución pública.
- **CA-06:** La revisión de documentación no detecta secretos ni datos reales.

## Casos límite

- Un mantenedor solo quiere ejecutar pruebas, sin configurar Docker ni secretos
  de producción.
- Un lector asume que la aplicación admite cualquier banco, PDF escaneado u OCR.
- Un problema operativo puede exponer datos o secretos y requiere atención por
  los mantenedores sin divulgar información públicamente.

## Supuestos

- La documentación interna se mantiene en español.
- El repositorio conserva su enfoque de despliegue privado y no se expone a
  Internet como resultado de esta fase.
- La información técnica vigente en `docs/deployment.md` y las especificaciones
  existentes es la fuente de verdad para las instrucciones operativas.

## Preguntas abiertas

- ¿Qué procedimiento interno usarán los mantenedores para incidentes de
  seguridad o privacidad?
