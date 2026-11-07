# Publicar Gearly gratis (Render + Neon)

Render da el servidor web y Neon la base de datos PostgreSQL. La base de Render gratis se borra a los 30 días; la de Neon no, por eso guardamos ahí las evaluaciones.

## 1. Base de datos en Neon
1. Entra a https://neon.tech y crea una cuenta (puedes usar GitHub).
2. Crea un proyecto llamado `gearly`, región más cercana (us-east).
3. Copia la **connection string** (empieza por `postgresql://`). Guárdala; no la subas a GitHub.

## 2. Servicio web en Render
1. Entra a https://render.com con tu cuenta de GitHub.
2. **New → Blueprint** y elige el repositorio `gearly`. Render lee `render.yaml`.
3. Cuando pida `DATABASE_URL`, pega la connection string de Neon.
4. Espera a que termine el despliegue (5–10 min la primera vez). Tu app queda en `https://gearly-xxxx.onrender.com`.
5. En **Environment** verás `ADMIN_CLAVE` (generada sola). Úsala para exportar resultados.

## 3. Comprobar
- `https://TU-APP.onrender.com/api/salud` debe mostrar `"productos"` mayor que 0.
- Si dice 0, falta subir `data/catalogo.json` y `data/modelo.json` (paso 1 del README).

## Notas
- En el plan gratis la app se duerme tras 15 min sin uso; el primer acceso tarda ~1 minuto. Ábrela antes de cada sesión de evaluación.
- Cada `git push` a `main` vuelve a desplegar.
