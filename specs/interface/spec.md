# Interfaz web local

## Objetivo

Entregar una interfaz web local en español de Chile que permita ingresar una
clave de acceso por sesión, cargar cartolas compatibles, revisar movimientos
persistidos y explorar métricas deterministas sin exponer datos financieros más
allá de lo que requiere cada vista.

## Contexto

Las fases 3 a 7 exponen una API FastAPI autenticada con una API key de proceso:
cartolas, movimientos clasificados y análisis calculado al vuelo. No existe un
frontend, tooling de Node ni sesión de usuario. La fase 8 materializa el
dashboard del roadmap sin modificar las reglas, persistencia ni fórmulas de
análisis existentes.

Frontend y backend permanecen en este repositorio. El frontend vivirá en
`frontend/` con sus propias dependencias y scripts; no se crea otro repositorio
ni se requiere una nueva sesión de trabajo. La documentación bajo
`specs/interface/` es el contexto persistente para retomar implementación en una
sesión distinta si fuera necesario.

## Alcance

- Crear una SPA React/Vite separada del backend y ubicada en `frontend/`.
- Usar Material UI para controles, tabla, diálogos, estados y diseño responsive,
  y MUI X Charts para gráficos de métricas.
- Solicitar la API key al iniciar una sesión de interfaz y conservarla solo en
  memoria del navegador mientras la SPA está abierta.
- Cargar una cartola PDF mediante la API existente y mostrar éxito genérico,
  errores seguros y estado de carga.
- Listar cartolas con paginación, abrir su detalle, revisar sus movimientos
  autenticados y eliminar una cartola tras confirmación explícita.
- Permitir seleccionar cartolas y un rango para solicitar análisis, proponiendo
  inicialmente la unión de sus períodos declarados.
- Mostrar resumen, cobertura, evolución mensual, categorías, comercios
  principales y candidatos de recurrencia de `GET /v1/analysis`.
- Configurar CORS del backend mediante una lista explícita de orígenes de UI.
- Documentar instalación, desarrollo, build, pruebas, variables no secretas y
  arranque coordinado de frontend y backend.

## Fuera de alcance

- Usuarios, registro, recuperación de contraseña, roles, multi-tenancy,
  cookies de sesión o renovación de credenciales.
- Persistir la API key en `localStorage`, `sessionStorage`, IndexedDB, cookies,
  URL, archivos de build, logs o telemetría.
- Exponer la interfaz en un origen no configurado, permitir CORS wildcard o
  eliminar la autenticación de la API.
- Editar cartolas, movimientos, categorías, reglas o candidatos recurrentes.
- Mostrar PDFs, números de cuenta completos, hashes de origen, identificadores
  internos de movimiento, exportaciones, OCR, insights asistidos o presupuestos.
- Cambiar contratos de `POST /v1/statements` para distinguir carga nueva de una
  deduplicada.

## Requisitos funcionales

### RF-01: Inicio de sesión local

La SPA debe iniciar en una pantalla de acceso que solicite una API key. Tras
aceptarla, todas las solicitudes de datos deben enviar `Authorization: Bearer`
con esa clave. Recargar la página, cerrar la pestaña o cerrar la sesión de la UI
debe borrar la clave y volver a la pantalla de acceso.

Una clave rechazada debe mostrar un mensaje seguro y permitir reintentar. La UI
no debe mostrar, registrar ni volver a renderizar la clave ingresada.

### RF-02: Carga de cartolas

La vista de carga debe aceptar un único archivo PDF, indicar el límite de 10 MiB
y 20 páginas que aplica el backend, y deshabilitar envíos duplicados mientras la
solicitud está activa. Debe mostrar progreso de espera, éxito genérico o el
mensaje seguro de error recibido.

Después de un éxito, la UI debe refrescar el historial y navegar al detalle de
la cartola devuelta. No debe afirmar si la cartola fue creada o reutilizada.

### RF-03: Historial y detalle

El historial debe usar la paginación existente de cartolas y mostrar banco,
producto, cuenta enmascarada, moneda, período y fecha de creación. Debe ofrecer
abrir el detalle de una cartola.

El detalle debe mostrar metadatos, resumen y una tabla responsive de movimientos
con fecha, descripción, referencia/canal cuando existan, monto CLP, tipo,
categoría y comercio cuando exista. Las descripciones son visibles solo en esta
vista autenticada; no se usan como etiquetas de gráficos ni se incluyen en
errores.

### RF-04: Eliminación explícita

La eliminación debe abrir un diálogo que explique que borra permanentemente la
cartola, movimientos y clasificaciones. Solo una confirmación explícita puede
llamar a `DELETE /v1/statements/{statement_id}`. Tras éxito, la interfaz debe
eliminar la cartola de historial y selección de análisis, invalidar su detalle y
refrescar cualquier análisis dependiente.

### RF-05: Asistente de análisis

La vista de análisis debe permitir seleccionar entre una y cien cartolas del
historial. Antes de consultar, debe mostrar banco, producto, moneda, cuenta
enmascarada y períodos elegidos, y detectar localmente incompatibilidades o
solapamientos visibles. El backend sigue siendo la autoridad para validar el
ámbito.

Al cambiar una selección compatible, la UI debe proponer como rango inicial la
fecha mínima y máxima de los períodos seleccionados. El usuario puede editar
ambas fechas dentro del máximo de 24 meses. La UI no debe solicitar análisis
hasta que haya selección y rango válidos.

### RF-06: Presentación de métricas

Una respuesta de análisis válida debe presentar claramente:

- gasto, cantidad de movimientos, créditos y débitos excluidos;
- cobertura de clasificación y comercio;
- rangos cubiertos, huecos y meses parciales;
- desglose de gasto por categoría;
- evolución mensual y variaciones, incluyendo valores no disponibles;
- hasta diez comercios principales;
- candidatos de recurrencia con cadencia, evidencia y estadísticas.

Los gráficos de evolución y categorías deben tener una alternativa textual o
tabular equivalente. La UI debe distinguir explícitamente resultados vacíos,
cobertura parcial y candidatos recurrentes de suscripciones confirmadas.

### RF-07: Estados y errores

Cada flujo de datos debe tener estados de carga, vacío, éxito y error. Los
errores de autenticación deben volver a solicitar la clave sin exponerla. Los
errores de ámbito incompatible o cartolas solapadas deben mantener la selección
y explicar cómo corregirla. Errores inesperados deben usar un mensaje genérico y
no revelar respuestas, SQL ni datos de cartolas.

## Requisitos no funcionales

### RNF-01: Seguridad y privacidad

La clave solo existe en memoria de JavaScript durante la sesión actual. La SPA
no debe incluir secretos en variables de build ni enviar la clave a un origen
distinto del backend configurado. CORS acepta únicamente orígenes explícitos.

### RNF-02: Accesibilidad y responsive

La interfaz debe ser utilizable con teclado y lector de pantalla, mantener foco
correcto en diálogos y ofrecer etiquetas para formularios, tablas y gráficos.
Debe funcionar en escritorio y móvil, con tablas adaptadas o desplazamiento
horizontal accesible cuando sea necesario.

### RNF-03: Determinismo y contratos

La SPA presenta datos tal como los devuelve la API; no recalcula categorías,
métricas, coberturas ni recurrencias. Montos se formatean como CLP entero y las
fechas se muestran con localización `es-CL`, sin alterar sus valores ISO de la
API.

### RNF-04: Repositorio y calidad

`frontend/` conserva sus dependencias, scripts y artefactos de build separados
del paquete Python. Debe haber pruebas unitarias de interfaz y E2E de los flujos
principales contra una API de prueba. Ningún artefacto generado ni secreto se
versiona.

## Criterios de aceptación

- **CA-01:** La SPA está en `frontend/`, puede instalarse, ejecutarse y
  construirse sin modificar las dependencias Python.
- **CA-02:** La clave se usa solo en memoria, se elimina al recargar o cerrar
  sesión y nunca aparece en almacenamiento web, URL, build, logs ni errores.
- **CA-03:** La carga acepta solo un PDF a la vez, maneja estados y errores de la
  API, refresca historial y abre detalle sin afirmar si la cartola fue creada.
- **CA-04:** El historial pagina cartolas y el detalle muestra los campos
  autenticados de movimientos, clasificación y comercio sin mostrar datos fuera
  de alcance.
- **CA-05:** El borrado requiere confirmación y, tras éxito, actualiza historial,
  detalle y selección/análisis sin conservar la cartola eliminada en pantalla.
- **CA-06:** El asistente propone el rango unión, valida selección/rango y trata
  incompatibilidad o solapamiento como error corregible sin inventar métricas.
- **CA-07:** El dashboard representa todas las secciones de análisis, incluyendo
  vacíos, huecos, meses parciales, variaciones nulas y recurrencias como
  candidatos.
- **CA-08:** Los gráficos tienen alternativa accesible y la interfaz funciona en
  viewport móvil y escritorio con navegación por teclado.
- **CA-09:** El backend solo permite orígenes UI configurados explícitamente; la
  SPA no puede depender de CORS wildcard.
- **CA-10:** Pruebas unitarias y E2E cubren inicio de sesión, carga, historial,
  detalle, borrado, selección y análisis contra respuestas de prueba seguras.

## Casos límite

- API key vacía, errónea, expirada durante una solicitud o reinicio de la SPA.
- PDF no válido, mayor que el límite, solicitud de carga lenta o error de red.
- Historial vacío, última página parcial y cartola eliminada mientras está abierta.
- Descripciones largas, comercio ausente, categoría `sin_categoria` y montos
  grandes.
- Selección vacía, repetida, de más de cien cartolas, incompatible o solapada.
- Rango de un día, fechas inválidas, más de 24 meses, meses vacíos, huecos y
  porcentaje de variación nulo.
- Análisis sin movimientos, sin comercios o sin candidatos recurrentes.
- Viewport móvil, foco al abrir/cerrar diálogos y gráficos sin interacción de
  puntero.

## Supuestos

- La interfaz se usa localmente por un operador de confianza que conoce la API
  key de la instancia.
- El backend se ejecuta con una ruta SQLite y API key configuradas, y la SPA
  recibe por configuración no secreta la URL base de esa API.
- Material UI, MUI X Charts, React, Vite, Vitest, Testing Library y Playwright
  son dependencias justificadas para entregar el flujo y su validación.
- El historial actual entrega suficiente metadato para orientar la selección;
  la validación final siempre ocurre en `GET /v1/analysis`.

## Preguntas abiertas

- ¿Qué mecanismo de despliegue servirá la SPA y el backend en producción cuando
  dejen de usarse solo localmente?
- ¿Cuándo será necesario reemplazar la clave local por identidad de usuario y
  sesión de servidor?
- ¿Se requerirá exportar tablas, reportes o gráficos en una fase posterior?
