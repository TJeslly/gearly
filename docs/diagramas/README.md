# Diagramas de Gearly 1.0

Diagramas del documento de trabajo de grado, actualizados el 20 de noviembre de 2026 para reflejar la versión 1.0 del repositorio. Cada diagrama está escrito en Mermaid: GitHub lo dibuja en esta página y el archivo `.mmd` se puede abrir y editar en https://mermaid.live. Junto a cada uno está la imagen PNG que se usa en el documento.

## 1. Contexto (C4, nivel 1)

```mermaid
flowchart LR
  P(["Participante<br/>persona adulta, usuario nuevo"])
  E(["Equipo investigador<br/>operador con clave de administración"])
  G["<b>Gearly 1.0</b><br/>Prototipo web de recomendación<br/>de productos deportivos"]
  A[("Amazon Reviews 2023<br/>McAuley Lab · Hugging Face<br/>Sports and Outdoors")]
  I["Servidores de imágenes<br/>de Amazon"]
  P -- "HTTPS: declara intereses, marca 0 a 5 productos,<br/>recibe 10 recomendaciones y evalúa" --> G
  E -- "HTTPS: exporta evaluaciones,<br/>consulta y activa versiones del modelo" --> G
  A -. "Descarga única y preparación<br/>fuera de línea (scripts Python)" .-> G
  G -. "El navegador muestra la imagen<br/>enlazada, sin copiarla" .-> I
```

Imagen: [01_contexto.png](01_contexto.png) · Fuente: [01_contexto.mmd](01_contexto.mmd)

## 2. Contenedores (C4, nivel 2)

```mermaid
flowchart TB
  subgraph NAV["Navegador del participante"]
    SPA["Interfaz web<br/><i>React 18 + TypeScript + Vite</i><br/>pasos, tarjetas, evaluación y SUS"]
  end
  subgraph REN["Servicio web en Render · contenedor Docker"]
    API["API REST<br/><i>Python 3.13 + FastAPI + SQLAlchemy</i><br/>sesiones, perfil, recomendaciones,<br/>evaluación y administración"]
    REC["Motor de recomendación<br/><i>módulo Python en memoria</i><br/>POP · CONT · CF · HIB"]
    ART[("Artefactos versionados<br/>data/catalogo.json · data/modelo.json<br/>data/modelos/*.json · manifiesto.json")]
  end
  DB[("PostgreSQL en Neon<br/>perfiles, listas, participaciones,<br/>evaluaciones y ajustes")]
  subgraph OFF["Entorno de preparación (fuera de línea)"]
    SCR["Scripts Python<br/>descargar_datos · preparar_datos ·<br/>experimento_offline"]
    RAW[("Datos crudos de Amazon<br/>CSV 5-core + metadatos JSONL<br/>no se publican")]
  end
  SPA -- "HTTPS · JSON<br/>cookie HttpOnly + cabecera X-CSRF" --> API
  API --> REC
  REC -- "carga al iniciar o al activar" --> ART
  API -- "SQL sobre TLS<br/>DATABASE_URL como secreto" --> DB
  RAW --> SCR
  SCR -- "genera y versiona en Git" --> ART
```

Imagen: [02_contenedores.png](02_contenedores.png) · Fuente: [02_contenedores.mmd](02_contenedores.mmd)

## 3. Componentes de la API y del motor de recomendación (C4, nivel 3)

```mermaid
flowchart TB
  subgraph API["API FastAPI (prefijo /api)"]
    direction LR
    SEG["Seguridad<br/>cookie HttpOnly · CSRF · límite de intentos ·<br/>clave de administración · validación Pydantic"]
    R1["Rutas de sesión<br/>POST /sesiones · GET /sesiones/actual ·<br/>POST /sesiones/retomar"]
    R2["Rutas de catálogo y perfil<br/>GET /vocabulario · GET /productos ·<br/>PUT y DELETE /perfil"]
    R3["Rutas de recomendación<br/>GET /recomendaciones · GET /parecidos"]
    R4["Rutas del estudio<br/>POST /participacion · POST /participacion/retiro ·<br/>POST /evaluacion · PUT /evaluacion/{id}"]
    R5["Rutas de administración<br/>GET /admin/exportar · GET /admin/modelos ·<br/>POST /admin/modelos/activar"]
    REG["Registro de modelos<br/>lista versiones, revisa compatibilidad<br/>con el catálogo y activa"]
    PER["Persistencia<br/>SQLAlchemy: Perfil, Lista, Participacion,<br/>Evaluacion, Ajuste"]
  end
  subgraph MOT["Motor de recomendación (recomendador.py)"]
    direction LR
    POP["POP<br/>conteo de usuarios positivos"]
    CON["CONT · EspacioContenido<br/>TF-IDF en 3 grupos + coseno"]
    CF["CF<br/>vecinos producto-producto<br/>coseno con encogimiento, L = 50"]
    HIB["HIB<br/>α·CONT + (1 − α)·CF, α = 0,25"]
    EXP["Explicación de cada resultado"]
  end
  SEG --> R1 & R2 & R3 & R4 & R5
  R3 --> HIB
  R4 --> POP & CON & HIB
  HIB --> CON & CF
  R3 --> EXP
  R5 --> REG
  REG -- "reemplaza el motor activo" --> MOT
  R1 & R2 & R3 & R4 & R5 --> PER
```

Imagen: [03_componentes_api.png](03_componentes_api.png) · Fuente: [03_componentes_api.mmd](03_componentes_api.mmd)

## 4. Modelo de datos operativo (entidad-relación, PostgreSQL)

```mermaid
erDiagram
  PERFILES ||--o{ LISTAS : "recibe"
  PERFILES ||--o{ PARTICIPACIONES : "registra"
  PERFILES ||--o{ EVALUACIONES : "responde"
  PARTICIPACIONES ||--o{ EVALUACIONES : "autoriza"
  PERFILES {
    string id PK "UUID"
    string token_hash UK "SHA-256 del token de la cookie"
    string csrf
    string codigo UK "G-XXXXXX para retomar"
    text disciplinas "JSON, vocabulario válido"
    text tipos "JSON"
    text selecciones "JSON, 0 a 5 productos"
    int version "aumenta con cada cambio"
    datetime creado
    datetime expira "7 días"
  }
  LISTAS {
    string id PK
    string perfil_id FK
    int perfil_version
    string metodo_solicitado
    string metodo_resultante "método realmente usado"
    string modelo_version "versión de artefactos"
    text productos "JSON, 10 ids en orden"
    int latencia_ms
    datetime creado
  }
  PARTICIPACIONES {
    string id PK
    string perfil_id FK
    string codigo_participante "P0XX"
    string consentimiento_version "C01-v2"
    datetime consentimiento_fecha
    text h01 "JSON"
    text tecnico "navegador y pantalla"
    string estado "activa, excluida o retirada"
    string motivo
    datetime retirado
  }
  EVALUACIONES {
    string id PK
    string perfil_id FK
    string participacion_id FK
    text perfil_congelado "JSON"
    text listas "POP, CONT, HIB; no va al navegador"
    text orden "unión aleatoria"
    text juicios "1 a 5 o nulo"
    text encuesta "SUS y H04"
    string modelo_version
    datetime creado
    datetime terminado
  }
  AJUSTES {
    string clave PK "modelo_activo"
    text valor "versión activada"
    datetime actualizado
  }
```

Imagen: [04_modelo_datos.png](04_modelo_datos.png) · Fuente: [04_modelo_datos.mmd](04_modelo_datos.mmd)

## 5. Artefactos del modelo y su versión

```mermaid
classDiagram
  direction TB
  class Catalogo {
    <<data/catalogo.json>>
    +id: parent_asin
    +nombre, marca
    +disciplina: running | ciclismo | entrenamiento
    +tipo: ropa | accesorios | proteccion | equipamiento
    +categoria_es, ruta, imagen
  }
  class Modelo {
    <<data/modelo.json · data/modelos/*.json>>
    +version: GEARLY-20261107-L50
    +popularidad: Map id → usuarios positivos
    +vecinos: Map id → 50 pares (id, similitud)
    +alfa: 0,25
  }
  class Manifiesto {
    <<data/manifiesto.json>>
    +fuente, revisión, huellas SHA-256
    +cortes T0 y T1, semilla
    +conteos de limpieza y particiones
  }
  class Ajuste {
    <<tabla ajustes>>
    +clave: modelo_activo
    +valor: versión
    +actualizado
  }
  class Lista {
    <<tabla listas>>
    +modelo_version
    +metodo_resultante
  }
  Modelo ..> Catalogo : solo ids del catálogo publicado
  Manifiesto ..> Modelo : describe cómo se generó
  Ajuste ..> Modelo : apunta a la versión activa
  Lista ..> Modelo : registra la versión usada
```

Imagen: [05_artefactos.png](05_artefactos.png) · Fuente: [05_artefactos.mmd](05_artefactos.mmd)

## 6. Preparación de datos, particiones y experimento offline

```mermaid
flowchart TB
  D1["descargar_datos.py<br/>CSV 5-core y metadatos JSONL<br/>revisión fija y huella SHA-256"] --> D2
  D2["preparar_datos.py · validar<br/>campos, faltantes, fechas,<br/>duplicados e identificadores"] --> D3
  D3["Depurar y clasificar<br/>positiva = calificación 4 o 5<br/>disciplina y tipo por ruta de categorías<br/>excluir sin título o sin imagen"] --> D4
  D4["Particiones por hash de usuario<br/>70 % entrenamiento · 15 % validación · 15 % prueba<br/>semilla 20261107 · corte T0 = 24/07/2019"]
  D4 --> E1["Entrenamiento (antes de T0)<br/>90.156 usuarios"]
  D4 --> E2["Validación<br/>843 usuarios"]
  D4 --> E3["Prueba<br/>840 usuarios"]
  E1 --> M1["Catálogo de 2.259 productos<br/>POP y vecinos CF (L = 50)<br/>→ catalogo.json, modelo.json, manifiesto.json"]
  E2 --> X1["experimento_offline.py<br/>elegir α en validación (0,25 · 0,50 · 0,75)"]
  M1 --> X1
  X1 --> X2["Prueba: 5 primeras positivas = apoyo<br/>k = 1, 3 y 5 visibles · resto = objetivos<br/>listas de 5 y 10 · mismos usuarios para todos"]
  E3 --> X2
  X2 --> X3["NDCG, Precision y Recall por usuario<br/>bootstrap 2.000 · IC 95 %<br/>cobertura, listas vacías, tiempo y memoria"]
  X3 --> R["docs/resultados_offline.json<br/>docs/RESULTADOS_OFFLINE.md"]
```

Imagen: [06_preparacion_datos.png](06_preparacion_datos.png) · Fuente: [06_preparacion_datos.mmd](06_preparacion_datos.mmd)

## 7. Secuencia de una recomendación

```mermaid
sequenceDiagram
  autonumber
  actor U as Participante
  participant W as Interfaz React
  participant A as API FastAPI
  participant B as PostgreSQL
  participant R as Motor (HIB)
  U->>W: Guarda deportes, tipos y 0 a 5 productos
  W->>A: PUT /api/perfil {disciplinas, tipos, selecciones, version} + X-CSRF
  A->>A: Valida cookie, CSRF, vocabulario, máximo 5 y versión
  A->>B: Actualiza perfil (version + 1)
  A-->>W: 200 perfil aceptado (o 409 / 422)
  W->>A: GET /api/recomendaciones
  A->>B: Lee perfil de la sesión
  A->>R: recomendar('hibrido', disciplinas, tipos, selecciones, 10)
  alt Sin intereses ni selecciones
    R-->>A: POP (alternativa registrada)
  else Solo intereses
    R-->>A: CONT (HIB se reduce a contenido)
  else Con selecciones
    R-->>A: α·CONT + (1 − α)·CF
  end
  A->>B: Guarda lista: método resultante, versión de modelo, latencia
  A-->>W: lista_id, método, motivo y 10 productos con explicación
  W-->>U: Tarjetas con foto, categoría y explicación
```

Imagen: [07_secuencia_recomendacion.png](07_secuencia_recomendacion.png) · Fuente: [07_secuencia_recomendacion.mmd](07_secuencia_recomendacion.mmd)

## 8. Flujo de primer uso y evaluación

```mermaid
flowchart TB
  S([Entrar a Gearly]) --> A1["Sesión anónima<br/>código G-XXXXXX"]
  A1 --> Q{"¿Quiere participar<br/>en el estudio?"}
  Q -- No --> F1
  Q -- Sí --> C1["Leer y aceptar C01<br/>responder H01"]
  C1 --> Q5{"Q5: ¿le interesa alguna<br/>actividad?"}
  Q5 -- No --> EX["Excluida: se registra<br/>sin presión"] --> F1
  Q5 -- "Sí / no estoy seguro" --> F1
  F1["Paso 1: deportes"] --> F2["Paso 2: tipos de producto"]
  F2 --> F3["Paso 3: marcar 0 a 5 productos"]
  F3 --> F4["Paso 4: 10 recomendaciones HIB<br/>explicadas"]
  F4 --> CM{"¿Cambiar gustos?"}
  CM -- Sí --> F1
  CM -- No --> EV{"¿Participación activa?"}
  EV -- No --> FIN([Fin])
  EV -- Sí --> H3["Evaluar: unión ciega de POP, CONT e HIB<br/>orden aleatorio, 1 a 5 o «No puedo valorar»"]
  H3 --> SUS["SUS (10 ítems obligatorios)<br/>y preguntas H04"]
  SUS --> FIN
  FIN -.-> RT["Puede retirar sus respuestas<br/>en cualquier momento"]
```

Imagen: [08_flujo_uso_evaluacion.png](08_flujo_uso_evaluacion.png) · Fuente: [08_flujo_uso_evaluacion.mmd](08_flujo_uso_evaluacion.mmd)

## 9. Despliegue

```mermaid
flowchart TB
  subgraph DEV["Equipo"]
    GH["Repositorio GitHub<br/>TJeslly/gearly (público)<br/>código + artefactos"]
    LOC["Equipo local<br/>SQLite y scripts de preparación"]
  end
  subgraph RENDER["Render · plan gratuito"]
    WEB["Servicio web Docker<br/>uvicorn: API /api + interfaz compilada /<br/>variables secretas: DATABASE_URL, ADMIN_CLAVE"]
  end
  subgraph NEON["Neon · plan gratuito"]
    PG[("PostgreSQL<br/>conexión cifrada (TLS)")]
  end
  CLI["Navegador<br/>móvil, tableta o computador"]
  AMZ["Imágenes de Amazon"]
  LOC -- "git push" --> GH
  GH -- "despliegue al publicar en main<br/>(render.yaml)" --> WEB
  CLI -- "HTTPS<br/>gearly-2o9e.onrender.com" --> WEB
  WEB -- "SQL / TLS" --> PG
  CLI -. "HTTPS" .-> AMZ
```

Imagen: [09_despliegue.png](09_despliegue.png) · Fuente: [09_despliegue.mmd](09_despliegue.mmd)

## 10. Procedimiento para activar una nueva versión del modelo

```mermaid
sequenceDiagram
  autonumber
  actor O as Equipo (operador)
  participant S as Scripts de preparación
  participant G as GitHub + Render
  participant A as API (Registro de modelos)
  participant B as PostgreSQL
  O->>S: Ejecuta preparar_datos.py con nuevo catálogo o datos
  S-->>O: catalogo.json, modelo.json con nueva versión, manifiesto
  O->>S: experimento_offline.py (α en validación, métricas en prueba)
  O->>G: Guarda la versión en data/modelos/ y publica (git push)
  G-->>A: Nuevo despliegue: el modelo activo sigue igual
  O->>A: GET /api/admin/modelos con la clave
  A-->>O: Versión activa, huella del catálogo, versiones y problemas
  O->>A: POST /api/admin/modelos/activar con la versión
  A->>A: Revisa campos, α y que todos los ids estén en el catálogo
  alt Incompatible
    A-->>O: 409 con la lista de problemas (no cambia nada)
  else Compatible
    A->>A: Carga el modelo en memoria y lo usa para nuevas listas
    A->>B: Guarda ajustes.modelo_activo
    A-->>O: 200 estado actualizado
  end
  Note over A,B: Cada lista y evaluación guarda modelo_version,<br/>así se sabe qué versión vio cada persona
```

Imagen: [10_activacion_modelo.png](10_activacion_modelo.png) · Fuente: [10_activacion_modelo.mmd](10_activacion_modelo.mmd)

## 11. Casos de uso (UML)

![Casos de uso](11_casos_uso.png)

Fuente editable: [11_casos_uso.svg](11_casos_uso.svg).

## 12. Diagrama de clases (UML)

```mermaid
classDiagram
direction TB
class Perfil {
  +id: String «PK»
  +token_hash: String «único»
  +csrf: String
  +codigo: String «G-XXXXXX»
  +disciplinas: List~disciplina~
  +tipos: List~tipo~
  +selecciones: List~producto_id~ «máx. 5»
  +version: int
  +expira: DateTime
}
class Lista {
  +id: String «PK»
  +perfil_version: int
  +metodo_solicitado: String
  +metodo_resultante: String
  +modelo_version: String
  +productos: List~producto_id~
  +latencia_ms: int
}
class Participacion {
  +id: String «PK»
  +codigo_participante: String
  +consentimiento_version: String
  +consentimiento_fecha: DateTime
  +h01: JSON
  +tecnico: JSON
  +estado: activa | excluida | retirada
}
class Evaluacion {
  +id: String «PK»
  +participacion_id: String «FK»
  +perfil_congelado: JSON
  +listas: Map~metodo, ids~
  +orden: List~producto_id~
  +juicios: Map~id, 1..5 o nulo~
  +encuesta: JSON
}
class Producto {
  <<catálogo JSON>>
  +id: String «parent_asin»
  +nombre: String
  +marca: String
  +disciplina: String
  +tipo: String
  +categoria_es: String
  +imagen: URL
}
class Recomendador {
  <<servicio>>
  +alfa: float = 0,25
  +recomendar(metodo, disciplinas, tipos, seleccionados) Resultado
  +puntajes(metodo, ...) Map
  +explicar(producto, metodo) String
  +parecidos(semilla) List
}
class EspacioContenido {
  +vec: Map~id, vector TF-IDF~
  +perfil(disciplinas, tipos, seleccionados) vector
  +puntajes(perfil, candidatos) Map
}
class ModeloCongelado {
  <<data/modelo.json y data/modelos/*.json>>
  +version: GEARLY-20261107-L50
  +popularidad: Map
  +vecinos: Map «L = 50»
  +alfa: float
}
Perfil "1" --> "0..*" Lista : recibe
Perfil "1" --> "0..*" Participacion : registra
Participacion "1" --> "0..*" Evaluacion : responde
Perfil ..> Producto : selecciona
Lista ..> Recomendador : producida por
Evaluacion ..> Recomendador : POP, CONT, HIB
class Ajuste {
  +clave: String «PK» = modelo_activo
  +valor: String «versión»
  +actualizado: DateTime
}
class RegistroModelos {
  <<servicio>>
  +modelos_disponibles() Map~version, archivo~
  +revisar_compatibilidad(modelo, catalogo) List~problema~
  +activar(version) Estado
}
RegistroModelos ..> ModeloCongelado : revisa y carga
RegistroModelos ..> Ajuste : guarda versión activa
RegistroModelos ..> Recomendador : reemplaza el activo
Recomendador *-- EspacioContenido
Recomendador ..> ModeloCongelado : carga
Recomendador ..> Producto : ordena
```

Imagen: [12_clases.png](12_clases.png) · Fuente: [12_clases.mmd](12_clases.mmd)
