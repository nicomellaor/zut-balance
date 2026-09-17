# Zut Balance

Zut Balance convierte cartolas bancarias digitales en movimientos normalizados,
clasificados y analizables. Está diseñado para entregar información de gasto
trazable a partir de datos verificados, no para dar asesoría financiera ni
interpretar documentos inciertos.

## Estado y alcance

Actualmente procesa cartolas PDF digitales de **Cuenta Vista Banco de Chile**
con los layouts y variantes documentados. Rechaza de forma explícita cartolas
escaneadas, protegidas, sin texto extraíble, de otros bancos o productos y
formatos no validados.

Es un proyecto privado e independiente, sin afiliación, patrocinio ni respaldo
de Banco de Chile.

El flujo es:

```text
Cartola PDF -> validación -> normalización -> categorización -> análisis -> señales
```

Las categorías, métricas y señales son deterministas. No hay OCR, IA,
clasificación probabilística, chatbot, predicciones ni recomendaciones
financieras. Consulte [Arquitectura](docs/architecture.md) y el
[roadmap](docs/roadmap.md) para conocer el estado y las fases futuras.

## Inicio rápido

Se requiere Python `>=3.12,<3.15`.

```bash
python -m pip install -e ".[dev]"
pytest
```

Uso como biblioteca:

```python
from zut_balance import parse_banco_chile_cuenta_vista

statement = parse_banco_chile_cuenta_vista("cartola.pdf")
for transaction in statement.transactions:
    print(transaction.date, transaction.movement_type, transaction.amount)
```

La función acepta una ruta local o el contenido binario de un PDF y devuelve una
cartola normalizada y conciliada. El número de cuenta se enmascara antes de
entregarlo al consumidor.

## Formas de uso

### API local

Para desarrollo de la API, configure una ruta SQLite y una API key de prueba:

```bash
export ZUT_BALANCE_DATABASE_PATH="./zut-balance.sqlite3"
export ZUT_BALANCE_API_KEY="un-secreto-largo-y-aleatorio"
uvicorn zut_balance.api:app
```

`GET /health` no requiere autenticación. Las rutas de datos aceptan una sesión
web válida o `Authorization: Bearer` con la API key. Consulte el
[contrato HTTP](docs/architecture.md#api-y-autenticación) y las especificaciones
para los detalles de cada endpoint.

### SPA de desarrollo

La SPA está en `frontend/` y requiere Node.js 24 o compatible. Siga su
[guía de desarrollo](frontend/README.md) para iniciar Vite, configurar la API
local y ejecutar sus pruebas. La interfaz usa una cookie `HttpOnly` y no solicita
ni conserva API keys.

### Despliegue privado con Docker

Para un despliegue reproducible, siga la [guía Docker](docs/deployment.md). El
stack sirve SPA y API desde el mismo origen HTTPS mediante Caddy, mantiene SQLite
y backups en volúmenes privados y no publica la API directamente. La
configuración local predeterminada usa `https://localhost:8443`.

El certificado se emite con una CA interna. Instale esa CA en los equipos
autorizados; no ignore advertencias TLS. La configuración detallada y la
operación están en la guía de despliegue.

## Privacidad y operación

- No se persiste el PDF original ni su texto extraído; SQLite guarda resultados
  normalizados hasta su eliminación explícita.
- La base SQLite y los backups contienen datos financieros sensibles y requieren
  controles de acceso del operador.
- Los ejemplos y pruebas usan solo datos sintéticos o anonimizados.
- La API key es para integraciones y no debe llegar a la SPA.

Lea [Privacidad](docs/privacy.md) antes de desplegar. Este repositorio es
privado: no debe compartirse con cartolas, secretos ni datos financieros reales.

## Documentación

- [Arquitectura](docs/architecture.md): componentes, flujo de datos y API.
- [Despliegue Docker](docs/deployment.md): configuración, inicio, backup y
  restauración privada.
- [Privacidad](docs/privacy.md): datos procesados, retención y responsabilidades.
- [Roadmap](docs/roadmap.md): fases completadas y planificadas.
- [Especificaciones](specs/): requisitos, planes y tareas por fase.

## Estado del repositorio

Zut Balance se mantiene como proyecto privado. No está destinado a distribución,
contribución pública ni reutilización externa sin autorización de sus
mantenedores.
