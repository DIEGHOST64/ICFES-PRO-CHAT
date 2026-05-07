# Metodología de Desarrollo — RUP (Rational Unified Process)

El proyecto se desarrolló siguiendo las 4 fases de la metodología RUP (Rational Unified Process), seleccionada por su enfoque iterativo e incremental que permite entregar prototipos funcionales en cada etapa mientras se mitigan riesgos técnicos de forma progresiva. El objetivo fue construir un **prototipo completamente funcional** —no un sistema en producción— que demuestre la viabilidad de un asistente Saber Pro basado en inteligencia artificial.

---

## Fase 1 — Inicio

**Duración aproximada:** 2 semanas

**Objetivo de la fase:** Validar la viabilidad del proyecto, definir el alcance del prototipo y establecer las bases técnicas del sistema.

### Actividades realizadas

**1. Análisis del problema**
Se identificó que los estudiantes de la Universidad de Cundinamarca no cuentan con una herramienta de preparación guiada para las pruebas Saber Pro. Los cuadernillos oficiales existen pero son estáticos: no ofrecen retroalimentación personalizada ni se adaptan al nivel del estudiante. Se definió que el prototipo debía resolver dos necesidades principales: (a) un chat conversacional que explique conceptos tipo ICFES usando IA generativa, y (b) un módulo de práctica con preguntas adaptativas que simule el examen real.

**2. Definición de requisitos funcionales**
Se documentaron 19 requisitos funcionales (RF-01 a RF-19) que cubren:
- Registro y autenticación de estudiantes (RF-01 a RF-03)
- Chat con IA contextual usando RAG (RF-04 a RF-07)
- Historial de consultas y calificaciones (RF-08, RF-10)
- Práctica por competencias con preguntas adaptativas (RF-09, RF-11)
- Autenticación del coordinador (RF-12)
- Panel de gestión de estudiantes (RF-13, RF-14)
- Dashboard con métricas e indicadores (RF-15 a RF-19)

**3. Selección del stack tecnológico**
Tras evaluar alternativas, se seleccionó:
- **Frontend:** React 18 + TypeScript + Vite (SPA rápida y moderna)
- **Backend:** Laravel 11 (API REST robusta con autenticación Sanctum)
- **IA:** FastAPI + Google Gemini 2.5 Flash (generación de texto e imágenes)
- **Vector DB:** ChromaDB (búsqueda semántica de documentos ICFES)
- **Embeddings:** SentenceTransformers `all-MiniLM-L6-v2` (384 dimensiones)
- **Infraestructura:** Docker Compose con 6 microservicios

**4. Diseño de la arquitectura**
Se diseñó una arquitectura de microservicios desacoplados orquestados con Docker Compose:
- **Nginx:** reverse proxy, SSL, serving de estáticos
- **Frontend (React):** interfaz de estudiante y coordinador
- **Backend (Laravel):** API REST, autenticación, base de datos
- **AI Service (FastAPI):** pipeline RAG, generación de preguntas, reportes
- **PostgreSQL:** datos relacionales (13 tablas)
- **ChromaDB:** base vectorial para búsqueda semántica

Se elaboró el diagrama C4 de contenedores y el modelo entidad-relación (ERD) de la base de datos.

**5. Estudio del corpus documental**
Se recopilaron y analizaron cuadernillos oficiales ICFES, guías de orientación y ejemplos de preguntas para cada competencia. Se identificaron las 5 competencias genéricas (Lectura Crítica, Razonamiento Cuantitativo, Comunicación Escrita, Inglés, Ciudadanas) más los módulos específicos de cada programa académico. Este material se usó posteriormente como base de conocimiento para el pipeline RAG.

### Entregables de la fase
- Documento de requisitos funcionales (RF-01 a RF-19)
- Diagrama de arquitectura C4
- Modelo entidad-relación (ERD)
- Stack tecnológico definido y justificado
- Primer prototipo funcional: login, registro y chat básico

---

## Fase 2 — Elaboración

**Duración aproximada:** 2 semanas

**Objetivo de la fase:** Resolver los riesgos técnicos críticos y construir la arquitectura base del sistema antes de invertir en funcionalidades avanzadas.

### Actividades realizadas

**1. Pipeline RAG (Retrieval-Augmented Generation)**
Este fue el principal riesgo técnico: ¿podría Gemini responder correctamente usando documentos reales del ICFES como contexto? Para resolverlo se implementó un pipeline completo:

- **Ingesta de documentos:** Script `indexar.py` que procesa PDFs del ICFES con PyMuPDF, dividiéndolos en fragmentos de 600 caracteres con solapamiento de 120 caracteres para preservar contexto.
- **Generación de embeddings:** Cada fragmento se convierte en un vector de 384 dimensiones usando SentenceTransformers.
- **Almacenamiento:** Los vectores se indexan en ChromaDB con metadatos (competencia, tipo —ejemplo o práctica—, programa, página de origen) en una colección única `saberpro_docs`.
- **Búsqueda semántica:** Ante una pregunta del estudiante, se genera su embedding, se consulta ChromaDB filtrando por módulo y tipo, y se recuperan los 4 fragmentos más relevantes (2 ejemplos + 2 práctica).
- **Generación de respuesta:** Los fragmentos se inyectan como contexto en el prompt de Gemini 2.5 Flash, que genera una respuesta personalizada con tono colombiano, explicaciones guiadas y preguntas de verificación.

**2. Arquitectura de base de datos**
Se diseñó e implementó el esquema relacional en PostgreSQL con 13 tablas normalizadas:
- `students`: datos de estudiantes (cédula, nombre, email, programa)
- `coordinators`: gestores de conocimiento
- `queries`: registro de cada consulta y práctica con campos para competencia, nivel, tiempo de respuesta, acierto, tipo de pregunta
- Tablas de soporte: `sessions`, `personal_access_tokens`, `cache`, `jobs`

Se implementó anonimización mediante hash SHA-256 con sal fija (`student_hash`) para proteger la identidad del estudiante en las métricas.

**3. Lógica adaptativa por nivel**
Se diseñó un sistema que adapta la dificultad de las preguntas según el desempeño del estudiante. Variables de estado (`nivel_objetivo`, `nivel_pregunta`) rastrean el nivel actual y permiten subir/bajar según la tasa de aciertos. El banco de preguntas se generó bajo demanda usando Gemini, con filtros de calidad automatizados (detección de texto literal, alineación semántica, detección de idioma).

**4. Resolución de riesgos de infraestructura**
- **ChromaDB como dependencia externa:** Se implementó healthcheck con reintentos y reconexión automática.
- **Límites de la API de Gemini:** Se agregó rate limiting y manejo de errores 429 con mensajes amigables.
- **Volumen de dependencias Python:** Se creó un Dockerfile optimizado con instalación en capa separada para aprovechar cache de Docker.

**5. Validación temprana con el corpus**
Se verificó que el pipeline RAG recuperara fragmentos relevantes para preguntas de prueba en cada competencia. Se ajustó el umbral de distancia coseno (<0.85) y se implementó una cascada de fallback de 3 niveles: filtro por módulo+tipo → solo tipo → sin filtro.

### Entregables de la fase
- Pipeline RAG funcional con 2091 documentos indexados
- Base de datos PostgreSQL con esquema completo y migraciones
- Sistema de práctica adaptativa con generación de preguntas
- Documentación de la arquitectura y flujo de datos
- Riesgos técnicos mitigados

---

## Fase 3 — Construcción

**Duración aproximada:** 3 semanas

**Objetivo de la fase:** Desarrollar iterativamente todas las funcionalidades restantes hasta alcanzar un prototipo completo.

### Iteraciones

**Iteración 1 — Chat conversacional completo**
- Historial de conversaciones agrupado por fecha (últimos 5 días)
- Carpetas de estudio para organizar chats por temas
- Modo oscuro/claro con persistencia
- Sugerencias rápidas personalizadas según historial
- Transición animada entre chat y práctica

**Iteración 2 — Módulo de práctica avanzado**
- Inglés con las 7 partes del examen real (avisos, oraciones, conversaciones, textos, etc.)
- Evaluación de ensayos de Comunicación Escrita con puntaje de 0 a 300
- Diseño visual diferenciado por tipo de pregunta (señales, cloze, lectura)
- Calificación de respuestas (👍/👎) y retroalimentación inmediata

**Iteración 3 — Dashboard del gestor de conocimiento**
- Fila de KPIs: total consultas, estudiantes únicos, consultas hoy, calificaciones positivas, total estudiantes
- Filtros por programa, rango de fechas y chips de tiempo rápido (7/15/30 días)
- 13 secciones de gráficos interactivos con Plotly.js:
  - Cobertura de adopción (medidor)
  - Ranking de estudiantes (barras)
  - Consultas por programa (barras + tabla)
  - Tendencia de uso (línea de tiempo)
  - Temas más consultados (tabla)
  - Evolución por competencia general (gráficos de línea por competencia)
  - Evolución por competencia inglés (niveles CEFR)
  - Distribución por dificultad (barras apiladas)
  - Inglés — desglose por tipo de pregunta
  - Tiempo de respuesta (barras agrupadas)
  - Comparativa por programa y competencia
  - Tablas de detalle (puntajes individuales y por competencia)

**Iteración 4 — Exportación de reportes**
- **PDF (13 secciones):** Informe completo con gráficos SVG nativos (sin dependencia de Plotly ni navegador), tablas de datos y recomendaciones de interpretación
- **Excel (11 hojas):** Datos crudos para análisis propio del coordinador, incluyendo calificaciones, tiempos de respuesta y progresión de nivel

**Iteración 5 — Chat IA del gestor**
- Modo de conversación con acceso a todos los datos del dashboard
- La IA puede responder preguntas en lenguaje natural como "¿Cuál es el programa con mejor desempeño en Lectura Crítica?"
- Acceso a cédulas y correos electrónicos de estudiantes mediante JOIN en las consultas
- Historial de conversación con persistencia

**Iteración 6 — Diseño responsive**
- Sidebar del chat convertido en menú deslizable (drawer) para dispositivos móviles
- Header de práctica rediseñado con flexbox (eliminados los `position: absolute` que causaban solapamiento)
- Grids adaptativos: 2 columnas en móvil, `auto-fit` en desktop
- Burbujas de chat ocupan hasta 92% del ancho en pantallas pequeñas
- Detección de dispositivo con `window.matchMedia` para comportamiento adaptativo

**Iteración 7 — Despliegue en VPS**
- Contratación de VPS en Contabo (12 GB RAM, 6 vCPU, 200 GB SSD)
- Instalación de Docker y Docker Compose en Ubuntu 24.04
- Migración del banco de preguntas (2091 documentos ChromaDB) al servidor
- Configuración de dominio `ascensopro.pro` con registro DNS tipo A
- Certificado SSL/TLS con Let's Encrypt (renovación automática)
- Nginx como reverse proxy unificado (frontend, backend, IA por el mismo puerto 80/443)
- Redirección automática HTTP → HTTPS

### Entregables de la fase
- Prototipo completamente funcional con todas las características
- Sistema desplegado y accesible en `https://ascensopro.pro`
- 28 capturas de pantalla documentando cada funcionalidad

---

## Fase 4 — Transición

**Duración aproximada:** 1 semana

**Objetivo de la fase:** Validar el prototipo con usuarios reales, corregir defectos encontrados y documentar el sistema para su presentación.

### Actividades realizadas

**1. Pruebas con usuarios reales**
Se realizaron sesiones de prueba con estudiantes voluntarios y un coordinador. Las pruebas no midieron impacto académico (mejora en puntajes Saber Pro), sino **problemas técnicos y de usabilidad del prototipo**:

| Problema detectado | Corrección aplicada |
|-------------------|-------------------|
| Los asteriscos `**` del Markdown no se renderizaban como negrita en el chat | Se ajustaron los componentes de ReactMarkdown añadiendo `fontWeight: 700` y `color: inherit` explícitos |
| La sesión del estudiante expiraba inesperadamente durante la práctica | Se agregó el guard `sanctum` explícito en `config/auth.php` y se extendió el tiempo de sesión |
| El menú lateral no se desplegaba en dispositivos móviles | Se rediseñó con control por estado React (`sidebarOpen`) y `transform: translateX()`, eliminando dependencia de clases CSS |
| El PDF de reportes no incluía todas las secciones del dashboard | Se agregaron 4 secciones faltantes: distribución por dificultad, inglés por tipo, tiempo de respuesta y calificaciones |
| El dashboard aparecía desplazado hacia la derecha en monitores grandes | Se corrigió el layout eliminando `display: flex` innecesario del contenedor raíz |
| Las preguntas generadas no se guardaban correctamente en el banco | Se implementó guardado asíncrono con `background_tasks` y reintentos |

**2. Corrección de errores en producción**
- **Bug de centrado del dashboard:** Se reemplazó el grid de 2 columnas por flex column con `width: 100%` para las tarjetas de la segunda sección.
- **Bug de guardado de ensayos:** Se corrigió el campo `respuesta` faltante en las peticiones de práctica de Escritura.
- **Bug de timezone:** Se agregó `TZ: America/Bogota` a todos los servicios Docker para consistencia horaria.
- **Bug de registro:** Se agregó el campo `email` a la migración de estudiantes (estaba solo como ALTER TABLE manual).

**3. Elaboración de documentación**

| Documento | Contenido |
|-----------|-----------|
| **Manual de usuario** | Guía paso a paso con 29 capturas reales del sistema. Cubre: ingreso, registro, chat, práctica, dashboard, exportación de reportes, modo IA, dispositivos compatibles y solución de problemas frecuentes. |
| **Documentación técnica** (`DOCUMENTACION.md`) | 16 secciones con diagramas Mermaid: arquitectura C4, modelo ERD, flujo RAG, pipeline de preguntas, endpoints de la API, estructura de la base de datos, configuraciones y stack tecnológico. |
| **Especificación OpenAPI** (`swagger.json`) | Documentación de todos los endpoints de la API REST con esquemas de request/response. |

**4. Preparación para presentación**
- El sistema se dejó operativo en `https://ascensopro.pro` con credenciales demo
- Se generó el logo institucional "Ascenso Pro" con Gemini 2.5 Flash Image
- Se configuró el favicon y el título de la pestaña del navegador
- Se creó el archivo `.env.example` para facilitar despliegues futuros

### Entregables de la fase
- Prototipo validado con usuarios reales y bugs corregidos
- Manual de usuario ilustrado (PDF, 4.7 MB)
- Documentación técnica completa con 16 secciones y diagramas
- Especificación OpenAPI 3.0 (Swagger)
- Sistema funcional y accesible públicamente

---

## Resumen del ciclo de desarrollo

| Fase | Duración | Foco | Entregable principal |
|------|----------|------|---------------------|
| **Inicio** | 2 semanas | Viabilidad y alcance | MVP: login + chat básico |
| **Elaboración** | 2 semanas | Riesgos técnicos | RAG pipeline + base de datos + práctica |
| **Construcción** | 3 semanas | Funcionalidades | Dashboard + PDF + IA + responsive |
| **Transición** | 1 semana | Validación y documentación | Manual + bugs corregidos + deploy |

**Resultado final:** Prototipo completamente funcional de un asistente Saber Pro basado en IA generativa, con modo estudiante (chat + práctica), modo coordinador (dashboard + informes), arquitectura de microservicios en Docker, desplegado en VPS con HTTPS, documentado y validado con usuarios reales.
