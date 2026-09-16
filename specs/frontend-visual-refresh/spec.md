# Renovación visual de la interfaz

## Objetivo

Mejorar la interfaz web privada de Zut Balance para que la revisión de cartolas
y análisis de gasto sea más clara, coherente y utilizable en escritorio y móvil,
sin cambiar sus contratos HTTP, cálculos financieros ni flujo funcional base.

La dirección visual será un cuaderno de conciliación digital: datos como foco,
morado como tinta de trabajo y superficies sobrias que privilegian la lectura y
comparación de valores por sobre la decoración.

## Contexto

La SPA existente usa React, Material UI y MUI X Charts para autenticar una
sesión local, cargar cartolas, revisar movimientos y consultar análisis
determinista. Sus flujos funcionales están implementados, pero el tema es
mínimo, las tablas no comparten componentes MUI y hay inconsistencias de
tipografía, espaciado, semántica y comportamiento responsive.

La tabla de Comercios principales puede sobresalir de su contenedor porque
hereda un ancho mínimo global sin un área de desplazamiento propia. El
documento HTML también conserva metadatos provisionales en inglés y el título
`frontend`.

Esta iniciativa sucede después de la adaptación contractual mínima de señales.
No reemplaza ni modifica las especificaciones de interfaz, análisis histórico o
señales; define mejoras de presentación sobre sus contratos ya aprobados.

## Alcance

- Mantener React, Material UI, MUI X Charts y la composición funcional actual
  de la SPA.
- Definir un sistema visual MUI coherente con color primario morado, fondos,
  divisores, tipografía, espaciado, radios y foco visible.
- Usar una tipografía sans-serif disponible como dependencia local para toda la
  interfaz, con jerarquía legible para datos financieros y escalado responsive.
- Reorganizar la presentación del dashboard para aclarar jerarquía, manteniendo
  todas las métricas y secciones recibidas de la API.
- Presentar el resumen financiero como una franja de indicadores relacionada,
  en vez de tarjetas visualmente equivalentes e independientes.
- Aplicar una paleta diferenciada y accesible a los gráficos de evolución y
  categorías, sin alterar los datos, sus cálculos ni alternativas tabulares.
- Incorporar de forma puntual los iconos de Material UI ya instalados en las
  acciones de carga, volver, eliminar y cerrar sesión; las acciones conservarán
  texto visible.
- Usar componentes MUI para tablas y sus contenedores accesibles, con anchos
  mínimos adecuados a cada conjunto de columnas.
- Corregir el desborde de Comercios principales y soportar nombres de comercios,
  descripciones y montos largos sin ampliar el viewport de la página.
- Mejorar la jerarquía semántica de encabezados, regiones principales, tabs,
  selector de cartola ancla, tablas y gráficos.
- Corregir el idioma, título y metadatos básicos de `index.html` para la
  aplicación en español de Chile.
- Ampliar las pruebas unitarias y E2E para cubrir presentación, semántica y
  ausencia de overflow horizontal en viewports representativos.

## Fuera de alcance

- Modificar endpoints, autenticación, persistencia, CORS, contratos TypeScript
  de API o fórmulas de análisis.
- Recalcular, inferir o reinterpretar montos, cobertura, categorías, comercios,
  recurrencias, avisos o highlights en el cliente.
- Añadir rutas, gestor global de estado, nueva librería de gráficos, animaciones
  decorativas, telemetría o un rediseño desde cero.
- Reestructurar por completo los módulos de la SPA si no es necesario para las
  mejoras visuales y de accesibilidad.
- Incorporar iconos de una dependencia adicional: `@mui/icons-material` ya está
  disponible.
- Cambiar la funcionalidad de carga, historial, detalle, eliminación o análisis
  salvo los ajustes de estado y semántica necesarios para presentar esos flujos.
- Añadir recomendaciones financieras, contenido promocional o lenguaje que
  interprete candidatos de recurrencia como suscripciones confirmadas.

## Requisitos funcionales

### RF-01: Sistema visual y tipografía

La aplicación debe usar un tema MUI centralizado cuyo color primario sea un
morado de contraste suficiente. El tema debe aplicar de forma consistente
colores de superficie, texto, divisores, espaciado, bordes, controles y foco.

La interfaz debe usar una familia sans-serif local y una escala tipográfica
coherente. Los montos deben conservar una lectura estable y diferenciable de
las etiquetas y texto de apoyo. Los tamaños de títulos deben adaptarse a móvil
sin perder la jerarquía visual.

### RF-02: Jerarquía de pantalla y acciones

La sesión autenticada debe exponer regiones `header`, navegación principal y
`main`. La pantalla de acceso y cada vista principal deben tener un encabezado
de primer nivel semántico; los títulos de secciones deben seguir una jerarquía
correcta independientemente de su variante visual.

Los tabs deben identificar sus paneles asociados. El selector de cartola ancla
debe usar un grupo de radio con etiqueta comprensible. Las acciones de cargar,
volver, eliminar y cerrar sesión deben incluir un icono MUI y mantener una
etiqueta textual visible.

### RF-03: Dashboard de análisis

El dashboard debe conservar los datos existentes de avisos, highlights, resumen,
cobertura, evolución mensual, categorías, detalle mensual, comercios y recurrencias.
Debe establecer una jerarquía visual clara entre:

- límites de interpretación y highlight mensual;
- resumen financiero;
- evidencia visual y tabular de evolución y categorías;
- detalles de cobertura, comercios y recurrencias.

El resumen debe mostrar sus cuatro indicadores como un grupo visualmente
relacionado y responder correctamente al cambio de columnas en móvil. Los
gráficos deben usar colores diferenciados, legibles y consistentes con el tema.
Las alternativas tabulares siguen visibles y representan datos devueltos por la
API sin modificaciones.

### RF-04: Tablas, contenido largo y responsive

Cada tabla debe usar componentes Material UI y tener un nombre accesible. El
desplazamiento horizontal, si es necesario, debe quedar contenido en el área de
la tabla, ser alcanzable con teclado y no producir desplazamiento horizontal del
documento.

Comercios principales debe caber en su tarjeta y permitir desplazamiento
horizontal de su tabla cuando el ancho disponible no alcance. Nombres de
comercios y descripciones largos deben poder partirse sin desbordar. Los montos
y recuentos deben conservar alineación y no partirse de manera ambigua.

La interfaz debe funcionar desde 320 px de ancho hasta escritorio; controles,
resúmenes, gráficos y tablas deben adaptarse al espacio disponible.

### RF-05: Metadatos y estados de presentación

El documento HTML debe declarar `lang="es-CL"`, título `Zut Balance | Cartolas y
análisis`, una descripción breve y un color de tema coherente. No debe conservar
una referencia a un favicon inexistente.

Los estados de carga de acciones existentes deben comunicar ocupación a
tecnologías asistivas. Los estados vacíos y de error deben mantener lenguaje
claro, descriptivo y consistente con las acciones disponibles.

## Requisitos no funcionales

### RNF-01: Compatibilidad y privacidad

La renovación no debe introducir almacenamiento persistente para credenciales,
datos de cartola o resultados de análisis. Debe conservar autenticación,
solicitudes y datos exactamente dentro de los contratos actuales.

### RNF-02: Accesibilidad

La interfaz debe conservar navegación completa con teclado, foco visible y
diálogos MUI con manejo de foco. Tablas y gráficos deben tener nombres
comprensibles; los gráficos mantienen una alternativa tabular visible. El color
no será el único medio para transmitir información.

### RNF-03: Calidad visual y rendimiento

La familia tipográfica y los iconos deben provenir de dependencias locales o ya
instaladas; no se cargan recursos de terceros en tiempo de ejecución. La
renovación debe evitar animaciones no solicitadas y respetar preferencias de
movimiento reducido cuando exista transición de interacción.

### RNF-04: Verificación

Las pruebas existentes deben seguir pasando. Las nuevas pruebas deben verificar
la semántica relevante y que el ancho desplazable del documento no exceda su
ancho visible en móvil y escritorio.

## Criterios de aceptación

- **CA-01:** El tema MUI usa morado como color principal y aplica una tipografía
  local, superficies, divisores y foco consistente en acceso, navegación,
  formularios, dashboard y tablas.
- **CA-02:** El dashboard muestra todos los datos de análisis actuales sin
  modificar sus valores y su resumen se presenta como un grupo visual coherente,
  responsive y legible.
- **CA-03:** Los gráficos de evolución y categorías usan colores diferenciados,
  mantienen formato CLP y sus alternativas tabulares accesibles.
- **CA-04:** Las acciones de cargar, volver, eliminar y cerrar sesión conservan
  texto visible e incorporan iconos de `@mui/icons-material`.
- **CA-05:** Comercios principales, movimientos, categorías y detalle mensual no
  generan overflow horizontal del documento con contenido largo; sus tablas se
  desplazan dentro de contenedores accesibles cuando corresponde.
- **CA-06:** La SPA presenta `header`, `nav` y `main`, encabezados jerárquicos,
  tabs asociados a paneles, grupo de radio etiquetado y tablas/gráficos con
  nombres accesibles.
- **CA-07:** `index.html` usa español de Chile, el título exacto `Zut Balance |
  Cartolas y análisis`, descripción y color de tema, sin favicon inexistente.
- **CA-08:** Lint, pruebas unitarias, build y E2E pasan; E2E comprueba ausencia
  de overflow horizontal en una viewport móvil y una de escritorio.
- **CA-09:** No cambian las rutas de API, los parámetros enviados, los cálculos
  financieros, la autenticación ni el almacenamiento de datos de la SPA.

## Casos límite

- Viewports de 320 px, 393 px, 768 px y escritorio amplio.
- Comercios, categorías y descripciones con palabras largas sin espacios.
- Montos CLP grandes, negativos, cero y valores no disponibles.
- Sin cartolas, sin comercios, sin categorías, sin recurrencias, sin avisos o
  sin highlight mensual.
- Cobertura con huecos y meses parciales.
- Carga, consulta de análisis, apertura de detalle y eliminación en curso.
- Navegación con teclado entre tabs, selector de cartola, tablas desplazables y
  diálogo de eliminación.

## Supuestos

- La interfaz sigue orientada a un operador local de confianza que revisa sus
  propias cartolas chilenas.
- `@fontsource-variable/ibm-plex-sans` es una dependencia justificable para
  empaquetar una fuente local; su disponibilidad y versión se validarán durante
  la implementación.
- `@mui/icons-material` permanece como dependencia de iconos, pues ya está
  instalada en el proyecto.
- La estructura funcional actual se preserva; solo se extraerán componentes si
  ello reduce duplicación o permite validar mejor la presentación.

## Preguntas abiertas

- No hay preguntas abiertas que bloqueen la planificación o implementación.
