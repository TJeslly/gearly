# Decisiones de diseño

- **Código nuevo.** Esta versión se escribió desde cero en noviembre de 2026. No reutiliza código ni datos generados del prototipo anterior (repositorio ManuelaBeta).
- **Hasta 5 selecciones y cero permitido**, como fija el protocolo del capítulo III (la beta anterior pedía de 3 a 10).
- **Imágenes y categoría en español** en cada tarjeta, por el hallazgo principal de la evaluación del 6 de noviembre (8 de 15 personas pidieron imágenes).
- **Evaluación dentro de la app** (H03 y H04): unión ciega de POP, CONT e HIB (5 cada una), en orden aleatorio, para comparar listas con juicios humanos y evitar copiar nombres a mano.
- **Contenido TF-IDF por grupos** (disciplina/tipo, categorías, título y marca) desde el inicio, con peso igual y sin ajustar con resultados de prueba.
- **Alfa del híbrido** elegido en validación entre 0,25 / 0,50 / 0,75 antes de evaluar en prueba.
- **Sin señal**, la app muestra popularidad y lo dice; nunca la presenta como personalizada.
- **Privacidad:** sesión anónima por cookie HttpOnly, CSRF en cambios, sin nombres ni correos (Ley 1581 de 2012).
