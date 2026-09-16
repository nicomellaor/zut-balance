# Plan técnico: renovación visual de la interfaz

## Enfoque técnico

La renovación conserva la SPA React/Vite, Material UI, MUI X Charts, el cliente
HTTP y la composición funcional actual. La implementación concentrará los tokens
visuales y estilos de componentes en el tema MUI, sustituirá las tablas HTML por
primitivas MUI y ajustará la estructura visual y semántica de `App.tsx` sin
modificar los contratos de `api.ts` ni la lógica financiera.

La dirección se materializa como un cuaderno de conciliación digital: el morado
es la tinta primaria, las superficies claras priorizan la evidencia y los datos
numéricos se alinean para comparación. La franja de resumen será el único gesto
visual distintivo; las demás secciones permanecen funcionales y contenidas.

## Componentes y archivos

| Ubicación | Cambio |
| --- | --- |
| `frontend/package.json` | Añadir `@fontsource-variable/ibm-plex-sans` para empaquetar tipografía local. No añadir librería de iconos. |
| `frontend/package-lock.json` | Actualizar mediante instalación de la dependencia tipográfica. |
| `frontend/src/theme.ts` | Crear tokens de paleta, tipografía, forma, foco, estilos de componentes MUI y colores de gráficos. |
| `frontend/src/main.tsx` | Importar la fuente local y usar el tema centralizado. |
| `frontend/src/index.css` | Conservar únicamente reset global, utilidades de wrapping y preferencias de movimiento; eliminar colores y tipografía que duplican el tema. |
| `frontend/index.html` | Corregir idioma, título, descripción, color de tema y referencia de favicon. |
| `frontend/src/App.tsx` | Aplicar estructura semántica, jerarquía visual, iconos, tabs y radio group accesibles, componentes MUI de tablas, resumen agrupado, gráficos con paleta y contenedores responsive. |
| `frontend/src/App.test.tsx` | Añadir pruebas de títulos, roles, grupo de radio, acciones y renderizado del dashboard renovado. |
| `frontend/e2e/dashboard.spec.ts` | Añadir comprobaciones de ancho de documento en proyectos móvil y escritorio, conservando el flujo existente. |

La implementación puede extraer componentes locales de `App.tsx` solo cuando
evite repetición de tablas o haga explícito el límite responsive. No se moverán
estados de sesión, detalle ni análisis a un gestor externo.

## Sistema visual

### Tokens de color

| Token | Valor | Uso |
| --- | --- | --- |
| `primary.main` | `#592C82` | Acciones, selección, foco y serie mensual. |
| `primary.light` | `#E9DDF4` | Fondo de selección y superficies de apoyo. |
| `background.default` | `#F5F5F8` | Papel frío de la aplicación. |
| `background.paper` | `#FFFFFF` | Superficies de lectura. |
| `text.primary` | `#272330` | Texto y cifras principales. |
| `divider` | `#DDD9E2` | Separación estructural. |
| `info.main` | `#34758A` | Información y serie secundaria. |
| `warning.main` | `#B66A1E` | Cobertura parcial. |

La paleta de categorías será constante y declarada en el tema: violeta, azul, turquesa,
ámbar y rosa apagado. Se asignará como paleta de MUI X Charts sin modificar datasets ni
asignar semánticas financieras al color.

### Tipografía y espaciado

`IBM Plex Sans Variable` se cargará desde la dependencia local y será la fuente
única del tema. Las cifras usarán `fontVariantNumeric: 'tabular-nums'` donde
corresponda. El tema definirá tamaños responsive para `h1` a `h4`, pesos 600
para encabezados y 500 para valores destacados.

Las superficies de sección usarán una escala de padding de 16 px en móvil y
24 px desde `sm`; el resumen financiero podrá usar padding compacto. Las tablas
tendrán celdas compactas y separadores de tema. El radio será moderado y se
reservará el borde y cambio de superficie para jerarquía, no para decorar cada
elemento.

### Interacción y accesibilidad

El tema definirá foco visible con contorno morado de alto contraste. No se
añadirán animaciones de entrada; las transiciones de Material UI se limitarán a
los controles ya interactivos y respetarán reducción de movimiento mediante CSS
global si existen transiciones personalizadas.

Los iconos se importarán selectivamente desde `@mui/icons-material` y se
marcarán decorativos porque cada botón conservará su nombre textual.

## Estructura de presentación

### Shell y vistas

- `AppBar` se renderiza como `header`; el contenedor principal como `main`.
- El nombre de producto será el `h1` visualmente compacto de la aplicación.
- `Tabs` y sus paneles tendrán IDs y atributos ARIA recíprocos.
- Las vistas de Cartolas y Análisis conservarán el mismo estado y navegación.
- El acceso usará `main` y un `h1` propio, sin cambiar la autenticación.

### Selector de análisis

- La selección conserva una única cartola ancla y la consulta existente.
- `FormControl`, `FormLabel`, `RadioGroup` y `Radio` reemplazan inputs nativos.
- Las etiquetas de cartola usarán datos actuales, con fechas formateadas para
  Chile y separación visual suficiente.
- Fechas y botón conservan su disposición de columna en móvil y fila desde `sm`.

### Resumen, señales y cobertura

- Avisos y highlight permanecen primero, en una sección de límites y cambios
  observados, sin recrear los datos de detalle.
- Los cuatro KPI usan un único `Paper` con `Grid` y divisores responsivos, en
  vez de cuatro superficies independientes.
- Cobertura temporal y de clasificación se agrupan visualmente en una sección
  secundaria, usando sus valores API existentes.

### Tablas y gráficos

- Se creará un componente local reutilizable `ResponsiveTable` o un patrón
  equivalente que combine `TableContainer`, `Table`, encabezados `scope="col"`
  y un `aria-label` recibido por props.
- Cada tabla define su propio `minWidth`: movimientos puede requerir uno amplio;
  categoría, detalle mensual y comercios usarán mínimos inferiores. Ninguna
  regla global impondrá 720 px a todas las tablas.
- Los contenedores de tabla serán focusables y desplazarán solo horizontalmente.
- Celdas textuales aplicarán `overflowWrap: 'anywhere'`; celdas monetarias y de
  cantidad usarán `whiteSpace: 'nowrap'`, alineación a la derecha y números
  tabulares.
- Grid items y paneles de gráfico usarán `minWidth: 0` para impedir que su
  contenido amplíe la página.
- Evolución mensual empleará la serie morada; categorías emplearán la paleta
  ordinal. Ejes y tooltips formatearán valores como CLP mediante el formatter
  existente. Las tablas equivalentes se mantienen visibles.

## Modelos e interfaces

No se modifican los tipos de API ni el contenido de las solicitudes. Los únicos
tipos nuevos, si se requieren, serán locales de presentación:

- `ResponsiveTableProps`: nombre accesible, ancho mínimo y contenido de tabla.
- Un conjunto constante de colores de categoría para configuración de gráficos.

Los componentes de dashboard seguirán recibiendo `Analysis` y mostrarán cada
campo como llega del backend. La función `money` conserva `es-CL`, CLP y cero
decimales. El formateador de fechas conserva las fechas ISO originales y solo
cambia su presentación.

## Dependencias y decisiones

- Se añadirá `@fontsource-variable/ibm-plex-sans`, pues permite la tipografía
  aprobada sin una solicitud a fuentes externas durante ejecución.
- Se reutiliza `@mui/icons-material`, ya instalada. No se agrega otra librería
  de iconos.
- Se conservan MUI y MUI X Charts; no se agrega sistema de diseño alternativo ni
  dependencias de layout o animación.
- Se elimina la referencia al favicon inexistente en vez de crear un recurso
  gráfico nuevo, ya que el alcance no incluye identidad de marca ilustrada.
- No se incluyen controles de tema oscuro: el producto no lo requiere en esta
  iniciativa y aumentaría el alcance de contraste y pruebas.

## Estrategia de pruebas

- Unitarias con Testing Library:
  - verificar encabezados y landmarks de acceso y shell autenticado;
  - comprobar tabs asociados a sus paneles;
  - comprobar el grupo de radios etiquetado y el mantenimiento de una ancla;
  - comprobar botones de acción con sus etiquetas visibles;
  - renderizar comercios con nombres largos y validar el contenedor accesible;
  - conservar casos del dashboard para avisos, highlights y estados vacíos.
- Validar `index.html` de forma liviana o mediante prueba de build para idioma y
  título si el tooling actual permite hacerlo sin añadir dependencias.
- E2E Playwright:
  - conservar acceso, carga, análisis y eliminación;
  - en Chromium y móvil comprobar que
    `document.documentElement.scrollWidth <= document.documentElement.clientWidth`
    tras renderizar el dashboard;
  - conservar la comprobación de foco de teclado ya existente.
- Ejecutar `npm run lint`, `npm run test`, `npm run build` y `npm run test:e2e`.
- Ejecutar `git diff --check` antes de completar la iniciativa.

## Riesgos y migración

- Los ajustes de tipografía pueden modificar alturas de componentes y densidad de
  gráficos; se revisarán en 320 px, 393 px, 768 px y escritorio amplio mediante
  E2E y, si está disponible, capturas locales.
- MUI X Charts puede requerir APIs específicas para formatter de ejes y tooltip
  según su versión actual; se verificará contra los tipos instalados antes de
  editar, sin cambiar de dependencia si una opción no está disponible.
- El reemplazo de tablas HTML puede afectar selectores y pruebas existentes;
  las pruebas deben usar roles y nombres, no detalles de estructura frágiles.
- La fuente local aumenta ligeramente el bundle. Es un coste aceptado para una
  tipografía consistente sin tráfico de terceros.
- No existe migración de datos ni compatibilidad contractual: el cambio es solo
  de presentación y activos del frontend.
