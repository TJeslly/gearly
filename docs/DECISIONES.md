# Decisiones de diseño

- **Código nuevo.** Esta versión se escribió desde cero en noviembre de 2026. No reutiliza código ni datos generados del prototipo anterior (repositorio ManuelaBeta).
- **Hasta 5 selecciones y cero permitido**, como fija el protocolo del capítulo III (la beta anterior pedía de 3 a 10).
- **Imágenes y categoría en español** en cada tarjeta, por el hallazgo principal de la evaluación del 6 de noviembre (8 de 15 personas pidieron imágenes).
- **Evaluación dentro de la app** (H03 y H04): unión ciega de POP, CONT e HIB (5 cada una), en orden aleatorio, para comparar listas con juicios humanos y evitar copiar nombres a mano.
- **Contenido TF-IDF por grupos** (disciplina/tipo, categorías, título y marca) desde el inicio, con peso igual y sin ajustar con resultados de prueba.
- **Alfa del híbrido** elegido en validación entre 0,25 / 0,50 / 0,75 antes de evaluar en prueba.
- **Sin señal**, la app muestra popularidad y lo dice; nunca la presenta como personalizada.
- **Privacidad:** sesión anónima por cookie HttpOnly, CSRF en cambios, sin nombres ni correos (Ley 1581 de 2012).

## Cambio de protocolo de evaluación (7 de noviembre de 2026)

- **Antes (v1):** los usuarios de validación y prueba debían tener sus 6 positivas dentro de una ventana temporal (validación entre T0 y T1; prueba después de T1). Con el catálogo de 2.263 productos quedaban **36 usuarios de validación y 9 de prueba**, insuficientes.
- **Ahora (v2):** se usa toda la historia de los usuarios de validación y prueba, que siguen siendo disjuntos de los de entrenamiento. El modelo sigue usando solo entrenamiento antes de T0. Quedan unos 840 usuarios en cada grupo.
- **Cuándo se decidió:** después de ver solo los conteos de usuarios y **antes de calcular cualquier métrica**.
- **Límite:** algunos objetivos de prueba ocurren antes de T0. No hay fuga de datos del propio usuario (no está en el entrenamiento), pero la popularidad y los vecinos reflejan un periodo que se superpone con esas fechas.

## Corrección de clasificación (7 de noviembre de 2026)

Después de la primera corrida v2 se corrigió la asignación de tipo (las riñoneras y correas quedaban como «equipamiento»), se tradujeron más categorías y se excluyeron 4 productos clasificados por rutas promocionales («PD23…», «Holiday…»). Se volvió a correr todo. La conclusión no cambió: en la primera corrida HIB − CONT (k = 3) fue +0,0266 [0,0179; 0,0356]; en la vigente, +0,0274 [0,0187; 0,0362]. Se informan las cifras vigentes.

**Hallazgo del catálogo:** la categoría Sports and Outdoors de Amazon Reviews 2023 casi no tiene ropa ni calzado deportivo (están en otra categoría del conjunto). La app oculta los tipos sin productos. Running queda con 259 productos, la mayoría riñoneras e hidratación.

## SUS en la evaluación (7 de noviembre de 2026)

A pedido del tutor se añadió el **System Usability Scale** en su versión en español validada (Sevilla-González et al., 2020, JMIR Human Factors, CC BY 4.0), con el texto y la instrucción sin modificar. Las 10 preguntas son obligatorias, no admiten «No puedo evaluar» y se responden antes de las seis preguntas propias de Gearly, que se analizan aparte. La exportación calcula el puntaje SUS de 0 a 100 (Brooke, 1996): ítems impares x − 1, pares 5 − x, suma × 2,5.

## Alineación con el documento (9 de noviembre de 2026)

Antes de aplicar la evaluación se cerraron las diferencias entre la especificación del capítulo IV y la aplicación:

- **Estrategia fijada por el estudio:** `GET /recomendaciones` ya no acepta `?metodo=`; siempre usa el híbrido.
- **Consentimiento C01 y caracterización H01** dentro de la aplicación (`POST /participacion`), antes del recorrido. Si la persona no acepta, no se guarda nada. Si no cumple Q4 o Q5, se registra la exclusión sin datos sustantivos.
- **Retiro** (`POST /participacion/retiro`): borra valoraciones, encuesta y caracterización, y conserva solo la constancia del retiro. Se puede hacer al terminar o retomando la sesión con su código durante 7 días.
- **Límite de intentos** al retomar con código: 10 por IP cada 15 minutos (respuesta 429).
- **Latencia:** cada lista guarda su tiempo de cálculo; la exportación informa p50 y p95.
- Migración automática de columnas nuevas sobre la base ya publicada.

## Cambio de población (9 de noviembre de 2026)

La muestra pasa de «estudiantes de la UMB» a **adultos cercanos al equipo: compañeros de la UMB, amigos y familiares**, con interés en running, ciclismo o entrenamiento. Q4 ya no excluye: registra la relación con el equipo para analizarla. Solo excluye responder «No» en Q5. Consentimiento C01-v2. Quien quedó excluido con la regla anterior puede registrarse de nuevo. Limitación: muestra por conveniencia con posible sesgo de complacencia; se informará la relación de cada participante.
