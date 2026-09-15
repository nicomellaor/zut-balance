# Frontend de Zut Balance

La SPA local permite cargar cartolas, revisar movimientos y explorar métricas.
Usa React, Vite, Material UI y MUI X Charts, pero no guarda datos ni API keys en
el navegador.

## Desarrollo

Se requiere Node.js 24 o compatible.

```bash
npm install
npm run dev
```

Vite reenvía `/v1` a `http://127.0.0.1:8000` para que el navegador conserve el
mismo origen. Inicie la API con autenticación web, hash Argon2, secreto de
sesión, `ZUT_BALANCE_API_KEY`, `ZUT_BALANCE_COOKIE_SECURE=false` y
`ZUT_BALANCE_TRUSTED_ORIGINS=http://127.0.0.1:5173` durante desarrollo.

La interfaz solicita la contraseña del administrador y conserva una sesión
firmada en una cookie `HttpOnly`; no solicita, almacena ni transmite API keys.

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
