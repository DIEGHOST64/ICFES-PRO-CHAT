# Estado e Implementación del Módulo de Inteligencia Artificial (ICFES Pro AI)

Este documento resume la arquitectura, estado actual y soluciones implementadas en el módulo de generación de Inteligencia Artificial (AI Service) del proyecto ICFES Pro AI a fecha de Abril de 2026.

## 1. Arquitectura General y Flujo de Trabajo

El módulo de Inteligencia Artificial ("AI Service") fue migrado de una arquitectura síncrona/bloqueante a una **arquitectura completamente asíncrona de alto rendimiento** orientada a la persistencia.

### Flujo Principal
1. **Solicitud de Frontend:** Cuando el usuario pide un simulacro (ej, 15 preguntas de Inglés), la petición entra al endpoint `/api/ai/sugerencias`.
2. **Capa Inicial (Caché Rápida):** El motor buscará primero si el simulacro exacto ya está ensamblado en un caché transitorio (`_get_cached_sugerencias`). Si está, devuelve respuesta en milisegundos.
3. **Capa Base (ChromaDB):** Si no hay caché vivo, el motor extrae directamente la cantidad solicitada de **preguntas previamente validadas** desde la base de datos `ChromaDB`, entregándolas casi inmediatamente.
4. **Capa Generativa de Respaldo (Fallo Catastrófico):** Únicamente si ChromaDB no tiene preguntas disponibles, ensambla constructos deterministas básicos para no detener al usuario, e inicia la **minería en background**.

### Minería Asíncrona (Background Miner)
Para mantener un banco permanente, la función `_background_question_miner` se ejecuta sin bloquear al estudiante.
- Solicita llamadas por lotes a `Gemini 3.1 Pro`.
- Aplica **Filtros Anti-Literalidad, Anti-Spanglish y Estructura (Opciones >= 4, o 3 para Inglés, o Ensayo para Escrita)**.
- Verifica encajes de coherencia con el nivel CEFR y tipo de parte del examen.
- Pasa los supervivientes (tras el descarte, de ahí el Oversampling original del 300%) hacia `_almacenar_preguntas_db()`, el puente final que guarda permanentemente los registros en ChromaDB.

## 2. Correcciones de Defectos (Bugfixes Críticos)

Durante la implementación en producción, el sistema enfrentó varios fallos silenciosos críticos que impedían llenar el banco de ChromaDB:

*   **Falla del Guardado Fantasma:** La función `_background_question_miner` descartaba la memoria RAM de todas las preguntas generadas pero no incluía la instrucción para grabar contra disco (`_almacenar_preguntas_db`). Esto fue añadido al final del ciclo vital del minero.
*   **Shadowing Imports en Python:** Un intento de importación local de `ChromaService` en `_background_question_miner` generó un comportamiento conocido como *Shadowing*, donde la variable global colapsó generando errores de _UnboundLocalError_. Se corrigió conectando las preguntas creadas a la instancia principal abierta en vivo.
*   **Errores Silenciosos de Índices en Excepciones (IndexError):** Ciertas áreas como **Comunicación Escrita** (que no devuelven opciones múltiples, sino listas de ensayos `[]`) provocaban fallas masivas `IndexError` ocultos en cláusulas `try/except` generalistas, lo que ocasionaba la eliminación del 100% de la tanda asíncrona generada. Se construyeron manejadores específicos por área.
*   **Restricciones Absolutas por Longitud (`min_words`):** Las peticiones enfocadas en Inglés Parte 1, 2 y 3 (Avisos Cortos) devolvían entre 5 a 10 palabras (Avisos de 'Staff Only'), las cuales eran desechadas masivamente por las murallas de validación `_normalize_text_base_quality()` que exigían mínimo 30 palabras. Fueron omitidas de este filtro garantizando su retención.

## 3. Sembrado y Banco de Preguntas Completado

Se desarrolló y perfeccionó el archivo de minería por lotes: `app/scripts/pre_generar_banco.py`.
Actualmente el banco cuenta con más de **1300 registros verificados** pre-generados en la base de datos distribuido en las competencias con sobredemanda:
- **Comunicación Escrita:** ~284 (preguntas sin opciones, enfocadas en debates éticos generados).
- **Inglés:** ~291 (partes 1 a 7 con niveles A2 y CEFR estandarizados).
- **Lectura Crítica / Ciudadanas / Razonamiento:** Contabilizan por cada una +50 generadas AI. Totalizando abasto robusto para peticiones de 15, 22 o 30 registros.

## 4. Respaldos (Backups)

La base de datos corre internamente sobre Docker amarrada bajo un *Named Volume* mapeado. Al ser completamente SQLite (ChromaDB lo usa under the hood), exportarlo a un servidor local o un VPS en la nube garantiza el uso vitalicio de los más de mil prompts sin pagos directos de facturación a la API.

---
_Creado con soporte de la IA y listo para pruebas o paso de Antigravity al ecosistema de nube._
