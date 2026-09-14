# Frontend de Zut Balance

La SPA local permite cargar cartolas, revisar movimientos y explorar métricas.
Usa React, Vite, Material UI y MUI X Charts, pero no guarda datos ni API keys en
el navegador.

## Desarrollo

Se requiere Node.js 24 o compatible.

```bash
npm install
cp .env.example .env
npm run dev
```

`VITE_API_BASE_URL` es una URL pública no secreta. Para desarrollo local use
`http://127.0.0.1:8000`. El backend debe permitir el origen de Vite mediante
`ZUT_BALANCE_CORS_ORIGINS=http://127.0.0.1:5173`.

La interfaz solicita la API key directamente al operador y la mantiene solo en
memoria. Recargar, cerrar la pestaña o usar "Cerrar sesión" la elimina.

## Calidad

```bash
npm test
npm run build
npm run test:e2e
```

Las pruebas E2E inician Vite y una API FastAPI con SQLite temporal y datos de
ejemplo anonimizados. El navegador Chromium se instala una vez con:

```bash
npx playwright install chromium
```
