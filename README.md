# Zut Balance

## Idea general

Desarrollar una aplicación web de finanzas personales enfocada en automatizar el análisis de cartolas bancarias de bancos chilenos.

El usuario podrá subir una cartola en PDF y el sistema procesará automáticamente sus movimientos para extraer, normalizar, categorizar y analizar los gastos, mostrando posteriormente métricas e insights útiles para comprender sus hábitos financieros y detectar oportunidades de ahorro.

## Objetivo técnico

El valor principal del proyecto no estará en construir un CRUD financiero tradicional, sino en implementar un pipeline de procesamiento inteligente de documentos:

**PDF → extracción → normalización → categorización → análisis → insights**

La aplicación debe demostrar capacidades de:

- Desarrollo backend y full-stack.
- Procesamiento de documentos PDF.
- OCR como mecanismo de respaldo cuando el documento no permita extracción directa.
- Integración de modelos de IA.
- Automatización de procesamiento.
- Persistencia y modelado de datos.
- Visualización de métricas.
- Diseño considerando privacidad y datos sensibles.

## MVP

### 1. Carga y procesamiento de cartolas

El usuario carga una cartola bancaria en PDF.

Inicialmente se soportará uno o dos formatos específicos de bancos chilenos.

El sistema debe:

- Detectar el tipo/formato de documento.
- Intentar extracción directa de texto o tablas.
- Utilizar OCR solamente cuando sea necesario.
- Identificar las transacciones.
- Convertir los datos a un formato común.

Cada movimiento debería incluir, como mínimo:

- Fecha.
- Descripción o glosa.
- Monto.
- Tipo de movimiento.
- Categoría.
- Comercio identificado, cuando sea posible.

### 2. Categorización inteligente

Clasificar automáticamente los movimientos en categorías como:

- Alimentación.
- Transporte.
- Servicios.
- Entretenimiento.
- Compras.
- Suscripciones.
- Transferencias.
- Salud.
- Otros.

La solución debería combinar reglas deterministas con modelos de IA cuando la clasificación no sea evidente.

El usuario podrá corregir categorías incorrectas.

### 3. Métricas financieras

Generar métricas a partir de las transacciones procesadas, por ejemplo:

- Gastos totales.
- Gastos por categoría.
- Evolución mensual.
- Principales comercios.
- Gastos recurrentes.
- Variación respecto al período anterior.

### 4. Insights

Generar insights accionables basados en hechos calculados previamente por el backend.

Ejemplos:

- Categorías cuyo gasto aumentó significativamente.
- Gastos recurrentes o posibles suscripciones.
- Concentración de gasto en determinados comercios.
- Cambios relevantes entre períodos.
- Posibles oportunidades de ahorro.

La IA no debería analizar directamente datos sin procesar ni inventar conclusiones. El backend debe calcular primero estadísticas y patrones estructurados que posteriormente puedan convertirse en explicaciones comprensibles.

## Fuera del MVP

Inicialmente no se incluirán:

- Modelos predictivos de gasto o ahorro.
- Soporte para una gran cantidad de bancos.
- Open Banking.
- Asesoría financiera automática.
- Chatbot financiero.
- Funcionalidades complejas de presupuesto.

Estas características pueden evaluarse posteriormente.

## Arquitectura conceptual

```text
Frontend
   ↓
API Backend
   ↓
Document Processing
   ├── PDF text/table extraction
   └── OCR fallback
   ↓
Transaction Normalization
   ↓
Categorization Engine
   ├── Rules
   └── AI Classification
   ↓
Database
   ↓
Analytics Engine
   ↓
AI Insights
   ↓
Dashboard
```

## Principios del proyecto

- Utilizar IA únicamente cuando aporte valor.
- Priorizar soluciones deterministas cuando sean suficientes.
- Mantener separación clara entre extracción, categorización, análisis e IA.
- Diseñar componentes reemplazables y testeables.
- Medir la calidad de extracción y clasificación.
- Utilizar datos sintéticos o anonimizados para desarrollo y demostraciones públicas.
- Evitar almacenar innecesariamente documentos financieros originales.

## Posicionamiento

El proyecto debería presentarse como una:

**AI-assisted financial document processing and expense intelligence platform**

más que simplemente como una aplicación de finanzas personales.

El objetivo final es demostrar **Software Engineering + Backend + Automation + AI Integration** mediante un sistema completo y técnicamente justificable.

## Estado actual: ingesta de Cuenta Vista Banco de Chile

La primera feature implementada procesa cartolas PDF digitales de Cuenta Vista
del Banco de Chile. La compatibilidad se limita al layout representado por
`media/cartola_ejemplo_banco_chile.pdf`.

### Instalación local

Se requiere Python 3.12 o superior, hasta la versión 3.14.

```bash
python -m pip install -e ".[dev]"
```

### Uso

La función pública acepta el contenido binario de un PDF o una ruta local y
devuelve un `Statement` normalizado solamente si todas las validaciones pasan.

```python
from zut_balance import parse_banco_chile_cuenta_vista

statement = parse_banco_chile_cuenta_vista(
    "media/cartola_ejemplo_banco_chile.pdf"
)

for transaction in statement.transactions:
    print(transaction.date, transaction.movement_type, transaction.amount)
```

El resultado incluye banco, producto, período, moneda, paginación, resumen de
saldos y transacciones. Cada transacción contiene fecha, descripción original,
número de documento opcional, sucursal o canal opcional, monto entero en CLP,
tipo `debit` o `credit` y saldo informado opcional. El número de cuenta se
enmascara y nunca se devuelve completo.

### Errores esperados

Los errores de procesamiento heredan de `StatementError`:

- `InvalidPdfError`: el archivo no es un PDF legible o no se puede leer desde la ruta indicada.
- `EncryptedPdfError`: el PDF está protegido con contraseña.
- `TextExtractionError`: el PDF no expone texto extraíble.
- `UnsupportedStatementError`: el documento no coincide con el formato soportado.
- `UnreliableExtractionError`: faltan datos necesarios, la extracción es incompleta o los saldos no concilian.

### Límites actuales

- No hay OCR: documentos escaneados se rechazan explícitamente.
- No hay persistencia, API, interfaz gráfica, categorización, IA, métricas ni insights.
- No se soportan otros bancos, productos o layouts no documentados.
- La muestra de aceptación es de una página; las cartolas multipágina no están validadas aún.
- Las pruebas y ejemplos deben usar exclusivamente datos sintéticos o anonimizados. No se debe incorporar una cartola real al repositorio.
