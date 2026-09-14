# Zut Balance

Zut Balance es un proyecto de procesamiento de documentos financieros para
convertir cartolas bancarias en movimientos normalizados y confiables. Su visión
es construir una plataforma de inteligencia de gastos que avance desde la
ingesta determinista de PDFs hasta métricas e insights basados en datos
verificados.

El flujo objetivo es: PDF, extracción, normalización, categorización, análisis
e insights. La visión, las fases y sus dependencias están en
[docs/roadmap.md](docs/roadmap.md).

## Estado actual

Zut Balance incluye una librería y un servicio HTTP que procesan cartolas PDF
digitales de Cuenta Vista de Banco de Chile. Soporta el layout inicial y las
variantes sintéticas documentadas de varias páginas, períodos que cruzan de año,
columnas desplazadas y metadatos reordenados.

El parser devuelve una cartola normalizada y conciliada, o un error explícito
si el PDF no es legible, está protegido, no contiene texto extraíble, no
corresponde al formato soportado o no puede extraerse de forma confiable.

## Inicio rápido

Se requiere Python `>=3.12,<3.15`.

```bash
python -m pip install -e ".[dev]"
```

```python
from zut_balance import parse_banco_chile_cuenta_vista

statement = parse_banco_chile_cuenta_vista(
    "media/cartola_ejemplo_banco_chile.pdf"
)

for transaction in statement.transactions:
    print(transaction.date, transaction.movement_type, transaction.amount)
```

La función acepta una ruta local o el contenido binario de un PDF y devuelve un
`Statement` con metadatos, resumen de saldos y transacciones. El número de
cuenta se enmascara antes de entregarse al consumidor.

## Servicio HTTP

Inicie el servicio con:

```bash
uvicorn zut_balance.api:app
```

`GET /health` devuelve el estado operativo sin procesar cartolas. Para procesar
un PDF, envíe un único campo multipart llamado `file` a `POST /v1/statements`:

```bash
curl -F "file=@media/cartola_ejemplo_banco_chile.pdf;type=application/pdf" \
  http://127.0.0.1:8000/v1/statements
```

Una respuesta `200` contiene `metadata` (banco, producto, cuenta enmascarada,
moneda, período, número de cartola y paginación), `summary` (saldos y
retenciones) y `transactions` (fecha, descripción, referencias, monto, tipo y
saldo informado). Las fechas usan ISO 8601, los montos son enteros y los campos
opcionales ausentes son `null`.

Los errores usan el formato `{"error":{"code":"...","message":"..."}}`:
las entradas inválidas o cartolas rechazadas devuelven `400`, los límites de
tamaño o páginas devuelven `413` y los fallos inesperados devuelven `500`. Los
mensajes no incluyen el contenido de la cartola ni detalles de implementación.

## Límites y privacidad

- La API acepta un PDF de hasta `10 MiB` y `20` páginas por solicitud. No exige
  autenticación en esta fase.
- No hay persistencia, interfaz gráfica, categorización, métricas, IA ni OCR.
- El servicio no persiste PDFs ni resultados, y no ofrece recuperación de
  solicitudes anteriores. El runtime puede usar almacenamiento temporal durante
  una solicitud multipart; su limpieza corresponde al entorno de despliegue.
- Las cartolas escaneadas, otros bancos, otros productos y layouts no documentados se rechazan.
- El soporte multipágina se limita a la matriz sintética aprobada; las cartolas reales no validadas se rechazan.
- Las pruebas y ejemplos usan únicamente datos sintéticos o anonimizados; no se incorporan cartolas reales al repositorio.

## Documentación

- [Roadmap del proyecto](docs/roadmap.md): visión, prioridades y fases futuras.
- [Especificación de la ingesta actual](specs/banco-chile-cuenta-vista-ingestion/spec.md).
- [Plan técnico de la ingesta actual](specs/banco-chile-cuenta-vista-ingestion/plan.md).
- [Especificación de robustecimiento](specs/banco-chile-cuenta-vista-ingestion-hardening/spec.md).
- [Plan técnico de robustecimiento](specs/banco-chile-cuenta-vista-ingestion-hardening/plan.md).
- [Especificación del servicio de procesamiento](specs/processing-service/spec.md).
- [Plan técnico del servicio de procesamiento](specs/processing-service/plan.md).
