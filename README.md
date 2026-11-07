# Gearly

Prototipo web que recomienda productos deportivos a **usuarios nuevos** (arranque en frío) a partir de preferencias explícitas: deportes, tipos de producto y hasta cinco productos que le gustan a la persona. Trabajo de grado de Ingeniería de Software, Universidad Manuela Beltrán.

**Autoras:** Laura Valeria Espejo Mantilla y Jeslly Téllez Mendoza.

## Qué hace

1. La persona elige deportes (running, ciclismo, entrenamiento) y, si quiere, tipos de producto.
2. Marca hasta 5 productos que le gusten (con foto y categoría en español). Al marcar uno, ve otros parecidos.
3. Recibe 10 recomendaciones, cada una con una explicación de por qué aparece.
4. Puede cambiar sus gustos o empezar de nuevo. Con su código (`G-XXXXXX`) retoma el perfil durante 7 días.
5. **Evaluación integrada:** con un código de participante (`P001`…), valora de 1 a 5 una mezcla ciega de las listas de popularidad, contenido e híbrido, responde el SUS en español (10 preguntas) y seis preguntas propias de experiencia. La exportación incluye el puntaje SUS de 0 a 100.

## Estrategias (backend/app/recomendador.py)

| Sigla | Estrategia | Idea |
|---|---|---|
| POP | Popularidad | Productos con más usuarios con reseña positiva (4 o 5) en entrenamiento |
| CONT | Contenido | Coseno entre el perfil y un vector TF-IDF del producto (disciplina/tipo, categorías, título y marca) |
| CF | Colaborativo producto-producto | Productos que valoraron bien las mismas personas (coseno con encogimiento) |
| HIB | Híbrido | `α·CONT + (1−α)·CF`, α elegido en validación |

## Estructura

```
backend/app/        API FastAPI (main.py) y recomendadores (recomendador.py)
backend/tests/      pruebas automáticas (usan un catálogo ficticio solo de prueba)
frontend/src/       interfaz React + TypeScript
scripts/            descarga de datos, preparación y experimento offline
data/               catálogo y modelo generados (se crean con los scripts)
docs/               despliegue, decisiones y resultados
```

## Paso 1. Preparar los datos (una sola vez)

Necesitas Python 3.12. Los datos crudos (~2–3 GB) van en una carpeta **fuera** del repositorio.

```powershell
py -3.12 -m pip install -r scripts\requirements.txt
py -3.12 scripts\descargar_datos.py C:\gearly-datos
py -3.12 scripts\preparar_datos.py C:\gearly-datos
py -3.12 scripts\experimento_offline.py C:\gearly-datos
```

Se generan `data/catalogo.json`, `data/modelo.json`, `data/manifiesto.json` (conteos y fechas de corte) y `docs/RESULTADOS_OFFLINE.md`. Súbelos a git: son necesarios para publicar la app.

## Paso 2. Ejecutar en tu computador

Terminal 1 (API):
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Terminal 2 (interfaz, requiere Node.js 22):
```powershell
cd frontend
npm install
npm run dev
```
Abre http://127.0.0.1:5173.

## Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## Publicar

Ver [docs/DESPLIEGUE.md](docs/DESPLIEGUE.md) (Render gratis + base de datos Neon gratis).

## Exportar resultados de la evaluación

`https://TU-APP.onrender.com/api/admin/exportar?clave=ADMIN_CLAVE` devuelve, por participante, las tres listas, los juicios, la media por lista y la encuesta.

## Datos y licencias

Productos, imágenes y reseñas provienen de **Amazon Reviews 2023** (Hou et al., 2024; McAuley Lab). Las imágenes se muestran enlazadas desde los servidores de Amazon y no se copian al repositorio. Los datos crudos no se redistribuyen. Uso exclusivamente académico.
