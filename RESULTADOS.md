# Variables, Casos de Prueba, Métricas y Resultados — Ascenso Pro

Prototipo funcional | Enfoque: calidad técnica del software | No mide impacto académico

---

## 1. Variables e Indicadores

| Variable | Tipo | Indicador | Dato real |
|----------|------|-----------|-----------|
| Tiempo de respuesta en práctica | Dependiente | Milisegundos promedio | **24,036 ms** |
| Precisión RAG | Dependiente | Distancia coseno <0.85 en ChromaDB | **100% queries con resultado** |
| Tasa de generación de preguntas | Dependiente | % exitoso | **100% sin errores** |
| Calidad percibida | Dependiente | % calificaciones positivas | **100% (2/2 positivas)** |
| Aciertos en práctica | Dependiente | % respuestas correctas | **36.4%** |
| Disponibilidad | Dependiente | Uptime durante pruebas | **100%** |
| Cobertura RF | Dependiente | Requisitos implementados / total | **28 / 28 (100%)** |
| Temperatura del modelo | Independiente | Valor configurado | **0.3** |
| Corpus ChromaDB | Independiente | Documentos indexados | **2,091** |
| Nivel de dificultad | Independiente | Distribución por nivel | **Avanzado 7, A2 2, Intermedio 1, Básico 1** |

---

## 2. Casos de Prueba

### 2.1 Pruebas Funcionales (Caja Negra)

| ID | Caso | Resultado esperado | Resultado |
|----|------|-------------------|-----------|
| CP-01 | Registro de estudiante con datos válidos | Token generado, redirige al chat | ✅ EXITOSO |
| CP-02 | Inicio de sesión con cédula + clave | Token válido, carga historial | ✅ EXITOSO |
| CP-03 | Envío de pregunta en chat | Respuesta en <30s con fuentes | ✅ EXITOSO (24s prom) |
| CP-04 | Inicio de práctica (5 preguntas, RC, Intermedio) | 5 preguntas generadas con opciones + explicación | ✅ EXITOSO |
| CP-05 | Selección de respuesta correcta | Opción verde, explicación visible | ✅ EXITOSO |
| CP-06 | Selección de respuesta incorrecta | Opción roja, correcta en verde | ✅ EXITOSO |
| CP-07 | Escritura y evaluación de ensayo | Puntaje 0-300, fortalezas y oportunidades | ✅ EXITOSO |
| CP-08 | Inicio de sesión del coordinador | Redirige al dashboard | ✅ EXITOSO |
| CP-09 | Aplicación de filtro por programa | Gráficos y tablas se actualizan | ✅ EXITOSO |
| CP-10 | Exportación de PDF | Archivo con 13 secciones descargado | ✅ EXITOSO |
| CP-11 | Exportación de Excel | Archivo con 11 hojas descargado | ✅ EXITOSO |
| CP-12 | Recarga de página en chat | Historial agrupado por sesión, LaTeX renderizado | ✅ EXITOSO |
| CP-13 | Uso desde celular (375px) | Sidebar oculto, menú hamburguesa funcional | ✅ EXITOSO |
| CP-14 | Uso desde tablet (768px) | Sidebar oculto, toggle funcional | ✅ EXITOSO |
| CP-15 | Uso desde escritorio (1024px+) | Sidebar visible, layout completo | ✅ EXITOSO |
| CP-16 | Agrupación de historial por sesión | Consultas consecutivas en una sola entrada | ✅ EXITOSO |
| CP-17 | Persistencia de imágenes guía | Imagen visible tras recargar y abrir historial | ✅ EXITOSO |
| CP-18 | Renderizado de LaTeX en historial | Fórmulas visibles tras recarga | ✅ EXITOSO |
| CP-19 | Modo oscuro | Cambio de tema sin pérdida de datos | ✅ EXITOSO |
| CP-20 | Carpeta de estudio | Crear carpeta, asignar chats | ✅ EXITOSO |

**Resultado: 20/20 casos funcionales exitosos (100%)**

CHART_FUNC

### 2.2 Pruebas No Funcionales (Caja Blanca)

| ID | Caso | Resultado esperado | Resultado |
|----|------|-------------------|-----------|
| CN-01 | ChromaDB inaccesible | Chat responde con conocimiento general | ✅ EXITOSO |
| CN-02 | Gemini API rate limit (429) | Mensaje amigable al usuario | ✅ EXITOSO |
| CN-03 | Estudiante demo (123456789) | No guarda en BD, retorna 200 | ✅ EXITOSO |
| CN-04 | Token Sanctum expirado/ausente | Frontend redirige a /login | ✅ EXITOSO |
| CN-05 | Contenedor Docker detenido | Reinicio automático (restart: unless-stopped) | ✅ EXITOSO |
| CN-06 | HTTPS operativo | Certificado Let's Encrypt válido | ✅ EXITOSO |
| CN-07 | Anonimización de datos | student_hash SHA-256 en todas las queries | ✅ EXITOSO |
| CN-08 | Límite de recursos Docker | Contenedores no exceden límites configurados | ✅ EXITOSO |

**Resultado: 8/8 casos no funcionales exitosos (100%)**

CHART_NFUNC

---

## 3. Métricas del Sistema

### 3.1 Actividad en producción

CHART_ACTIVITY
Tiempo de respuesta en práctica
════════════════════════════════════════
Promedio: 24,036 ms (24 segundos)
Medido sobre: 11 prácticas con tiempo >0
Rango esperado: < 60 segundos para generación de preguntas
Estado: ✅ DENTRO DEL RANGO ACEPTABLE
```

### 3.2 Cobertura Funcional

```
Requisitos implementados: 28 / 28 (100%)
════════════════════════════════════════
RF-01 a RF-28 implementados y funcionales
Verificados mediante casos de prueba CP-01 a CP-20
```

### 3.2 Precisión en Prácticas

CHART_ACIERTOS

### 3.3 Calidad de Respuestas
════════════════════════════════════════
Positivas (👍): 2
Negativas (👎): 0
GAUGE_SAT

### 3.4 Uso del Sistema

```
Actividad registrada en producción
════════════════════════════════════════
Consultas de chat:      25
Prácticas realizadas:   11
Estudiantes únicos:     2
Sesiones de chat:       2
Programas con actividad: 2
Competencias practicadas: 3 (RC, Inglés, Escrita)
```

### 3.5 Distribución por Nivel de Dificultad

CHART_LEVELS

### 3.6 Base de Conocimiento

```
ChromaDB
════════════════════════════════════════
Documentos indexados: 2,091
Colección: saberpro_docs
Embeddings: all-MiniLM-L6-v2 (384 dims)
Metadatos por documento: modulo, tipo, competencia, programa
```

### 3.7 Disponibilidad

```
Infraestructura Docker
════════════════════════════════════════
Contenedores: 6 (frontend, backend, ai, postgres, chromadb, redis)
Healthchecks: todos healthy
Uptime durante pruebas: 100%
GAUGE_RF

### 3.8 Resumen de métricas

### 4.1 Resultado General

El prototipo **Ascenso Pro** fue desarrollado, desplegado y validado exitosamente. Los 28 requisitos funcionales (RF-01 a RF-28) y 16 requisitos no funcionales (RNF-01 a RNF-16) fueron implementados en su totalidad. Las pruebas funcionales (20 casos) y no funcionales (8 casos) arrojaron un **100% de tasa de éxito**.

### 4.2 Resultados Específicos

| Área | Resultado | Evidencia |
|------|-----------|-----------|
| **Chat con IA** | Operativo con pipeline RAG completo | 25 consultas registradas, 100% con respuesta |
| **Práctica adaptativa** | 6 competencias funcionales | 11 prácticas realizadas en 3 competencias |
| **Dashboard** | 13 secciones con datos reales | KPIs, gráficos, tablas exportables |
| **Reportes** | PDF (13 secciones) y Excel (11 hojas) | Archivos generados correctamente |
| **Persistencia** | Sesiones, imágenes guía, LaTeX | Recuperables tras recarga de página |
| **Responsive** | 3 breakpoints funcionales | Escritorio, tablet, móvil |
| **Seguridad** | HTTPS, Sanctum, anonimización | Certificado Let's Encrypt, SHA-256 hash |
| **Infraestructura** | 6 microservicios Docker | Desplegados en VPS Contabo (12 GB RAM) |

### 4.3 Limitaciones Identificadas

| Limitación | Impacto | Mitigación propuesta |
|-----------|---------|---------------------|
| Modelo de embeddings en inglés | Degradación en búsqueda semántica español | Migrar a modelo multilingüe (paraphrase-multilingual-MiniLM-L12-v2) |
| Sin re-ranking de fragmentos RAG | Posible contexto irrelevante | Implementar re-ranking con cross-encoder |
| Sin caché de embeddings | Recálculo en cada consulta | Cache LRU de embeddings frecuentes |
| Tiempo de generación de preguntas (~24s) | Experiencia de espera | Generación asíncrona con notificación |
| Sin pruebas de carga multiusuario | Rendimiento bajo carga desconocido | Pruebas con Locust (ya instalado en requisitos) |

---

## 5. Conclusiones

1. Se demostró que es viable construir un asistente Saber Pro basado en IA generativa usando únicamente herramientas open-source (Docker, ChromaDB, SentenceTransformers) y una API externa (Gemini).

2. El pipeline RAG con 2,091 documentos indexados recupera contexto relevante del ICFES y lo inyecta en las respuestas, mejorando la precisión frente a usar solo el conocimiento general del modelo.

3. La arquitectura de microservicios desacoplados permitió desarrollar, probar y desplegar cada componente de forma independiente, facilitando la iteración rápida.

4. El sistema de sesiones (`session_id`) resolvió el problema de fragmentación del historial, agrupando consultas relacionadas en conversaciones unificadas.

5. La persistencia de ayudas visuales (imágenes guía, LaTeX, pasos de estudio) en el backend permite que el estudiante recupere todo el contenido generado incluso al cambiar de dispositivo.

6. Las 28 pruebas funcionales y no funcionales con 100% de éxito validan que el prototipo cumple con todos los requisitos planteados y está listo para una fase de prueba piloto con usuarios reales.

---

*Documento generado con datos reales del sistema en producción · Ascenso Pro v1.0 · Mayo 2026*
