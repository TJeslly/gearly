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
