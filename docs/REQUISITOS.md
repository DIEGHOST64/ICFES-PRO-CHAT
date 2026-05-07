# Requisitos del Sistema — Ascenso Pro

## Requisitos Funcionales (RF)

### Módulo de Autenticación

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-01** | Registro de estudiante | El sistema debe permitir el registro de estudiantes mediante cédula, nombre, correo electrónico, programa académico y una clave secreta de exactamente un carácter. |
| **RF-02** | Almacenamiento seguro de contraseña | La contraseña del estudiante debe almacenarse como hash bcrypt de la concatenación `cédula + clave_secreta`, nunca en texto plano. |
| **RF-03** | Inicio de sesión del estudiante | El estudiante debe autenticarse con su número de cédula como identificador y su clave secreta de un carácter como contraseña. |
| **RF-12** | Inicio de sesión del coordinador | El coordinador debe autenticarse con correo electrónico institucional y contraseña estándar. |

### Módulo de Chat con IA

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-04** | Recepción de preguntas | El sistema debe recibir preguntas en texto libre del estudiante (máximo 2000 caracteres) con su programa y competencia objetivo. |
| **RF-05** | Almacenamiento de consultas | Cada interacción del estudiante (pregunta y respuesta) debe almacenarse en la base de datos con marca de tiempo, programa y competencia. |
| **RF-06** | Búsqueda semántica contextual | El sistema debe buscar en ChromaDB los fragmentos de documentos ICFES más relevantes a la pregunta del estudiante, filtrando por módulo (general o específico) y tipo de documento (ejemplo o práctica). |
| **RF-07** | Generación de respuesta aumentada | El sistema debe generar una respuesta usando Gemini 2.5 Flash, inyectando los fragmentos recuperados como contexto, adaptando el tono al estudiante y cerrando con una pregunta de verificación. |
| **RF-08** | Historial de conversaciones | El estudiante debe poder ver sus conversaciones de los últimos 5 días, agrupadas por fecha, y retomar cualquier conversación anterior. |
| **RF-10** | Calificación de respuestas | El estudiante debe poder calificar cada respuesta de la IA como útil (👍) o no útil (👎). |
| **RF-11** | Anonimización de datos | Los datos del estudiante deben anonimizarse mediante hash SHA-256 con sal fija del proyecto (`icfes_salt_`) antes de almacenarse en el registro de consultas. |

### Módulo de Práctica

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-09** | Generación de preguntas de práctica | El sistema debe generar preguntas tipo Saber Pro para la competencia seleccionada, en el nivel de dificultad elegido (Básico, Intermedio, Avanzado), y en la cantidad solicitada (5, 10, 15 o 20). |
| **RF-23** | Adaptación por nivel | Las preguntas deben adaptarse al nivel del estudiante: 80% en el nivel objetivo y 20% de variedad. Para Inglés, la distribución debe cubrir las 7 partes del examen (Partes 1-7). |

### Módulo de Dashboard (Coordinador)

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-13** | Listado de estudiantes | El coordinador debe poder ver el listado completo de estudiantes registrados con su cédula, nombre y programa. |
| **RF-14** | Filtro por programa | El listado de estudiantes debe poder filtrarse por programa académico. |
| **RF-15** | Indicadores generales (KPIs) | El dashboard debe mostrar: total de consultas, estudiantes únicos activos, consultas del día, porcentaje de calificaciones positivas y total de estudiantes registrados. |
| **RF-16** | Distribución por programa | El sistema debe mostrar un gráfico de barras y tabla con la cantidad de consultas desglosadas por programa académico. |
| **RF-17** | Tendencia de uso | El sistema debe mostrar un gráfico de líneas con la evolución temporal de consultas (diaria o semanal). |
| **RF-18** | Filtros de dashboard | El coordinador debe poder filtrar todos los datos del dashboard por programa, fecha de inicio y fecha de fin, con chips de tiempo rápido (7, 15, 30 días). |
| **RF-19** | Temas más consultados | El sistema debe mostrar una tabla con el ranking de competencias más preguntadas, incluyendo el programa asociado. |

### Módulo de Reportes

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-20** | Exportación a Excel | El coordinador debe poder descargar un archivo Excel con 11 hojas: Resumen, Por Programa, Tendencia, Temas, Prácticas Estudiante, Prácticas Competencia, Progresión Nivel, Distribución Dificultad, Inglés por Tipo, Tiempo Respuesta y Calificaciones. |
| **RF-21** | Exportación a PDF | El coordinador debe poder descargar un informe PDF con 13 secciones que incluyen KPIs, gráficos SVG, tablas de datos, progresión de nivel y recomendaciones de interpretación. |
| **RF-24** | Excel con datos completos | El reporte Excel debe incluir todos los datos crudos disponibles en el dashboard para que el coordinador pueda hacer su propio análisis. |
| **RF-25** | PDF con gráficos vectoriales | El reporte PDF debe incluir gráficos en formato SVG nativo (sin dependencia de Plotly ni navegador) para garantizar nitidez al imprimir. |

### Módulo de Chat IA del Coordinador

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RF-22** | Chat IA con datos del dashboard | El coordinador debe poder hacer preguntas en lenguaje natural sobre los datos del dashboard a través de un chat, y recibir respuestas basadas en datos reales. El chat debe tener acceso a cédulas y correos electrónicos de los estudiantes. |

---

## Requisitos No Funcionales (RNF)

### Rendimiento

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-01** | Tiempo de respuesta del chat | El sistema debe generar una respuesta en el chat en menos de 15 segundos para el 90% de las consultas, incluyendo la búsqueda semántica y la generación de la respuesta. |
| **RNF-02** | Tiempo de generación de preguntas | La generación de una sesión de práctica (hasta 20 preguntas) no debe exceder los 60 segundos. |
| **RNF-03** | Tiempo de exportación de reportes | La generación de un PDF o Excel no debe exceder los 30 segundos para el volumen típico de datos de un semestre. |

### Disponibilidad

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-04** | Tolerancia a fallos de servicios externos | Si ChromaDB no está disponible, el chat debe seguir funcionando usando solo el conocimiento general de Gemini, sin mostrar errores al estudiante. |
| **RNF-05** | Recuperación automática | Los servicios Docker deben reiniciarse automáticamente (`restart: unless-stopped`) ante fallos del sistema operativo o cierres inesperados. |

### Seguridad

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-06** | Protección de datos personales | Los datos de los estudiantes deben anonimizarse antes de usarse en métricas agregadas. Las contraseñas nunca deben almacenarse en texto plano. |
| **RNF-07** | Comunicación cifrada | Toda la comunicación entre el navegador y el servidor debe estar cifrada mediante HTTPS con TLS 1.2 o superior. |
| **RNF-08** | Autenticación robusta | Las rutas protegidas deben validar tokens de Sanctum en cada petición. Las contraseñas de coordinadores deben tener mínimo 6 caracteres. |

### Usabilidad

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-09** | Diseño responsive | La interfaz debe adaptarse correctamente a dispositivos móviles (375px), tablets (768px) y escritorio (≥1024px). El menú lateral debe convertirse en un drawer deslizable en pantallas pequeñas. |
| **RNF-10** | Retroalimentación inmediata | El sistema debe mostrar indicadores visuales de carga (spinners, animaciones, dots de escritura) durante operaciones que tomen más de 1 segundo. |
| **RNF-11** | Modo oscuro | La interfaz debe ofrecer modo claro y modo oscuro, con transición suave y persistencia de la preferencia del usuario. |

### Mantenibilidad

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-12** | Carga eficiente de modelos | El modelo de embeddings (`all-MiniLM-L6-v2`) debe cargarse una sola vez en memoria y reutilizarse para todas las consultas, evitando recargas que degraden el rendimiento. |
| **RNF-13** | Arquitectura desacoplada | Los servicios deben estar contenerizados (Docker) y comunicarse mediante APIs REST, permitiendo modificar o reemplazar componentes individuales sin afectar al resto del sistema. |
| **RNF-14** | Variables de entorno | Todas las configuraciones sensibles (API keys, credenciales de base de datos, URLs de servicios) deben gestionarse mediante variables de entorno, nunca hardcodeadas en el código fuente. |

### Escalabilidad

| ID | Requisito | Descripción |
|----|-----------|-------------|
| **RNF-15** | Orquestación con Docker Compose | El sistema debe desplegarse con un solo comando (`docker compose up -d`) en cualquier servidor Linux con Docker instalado. |
| **RNF-16** | Límites de recursos por contenedor | Cada servicio debe tener límites de memoria y CPU definidos en la configuración de Docker Compose para evitar que un servicio acapare todos los recursos del servidor. |

---

## Trazabilidad: Requisitos → Componentes

| Requisito | Componente(s) que lo implementa(n) |
|-----------|-----------------------------------|
| RF-01, RF-02, RF-03, RF-12 | `AuthController.php`, `Student.php`, migración `students` |
| RF-04, RF-07, RF-22 | `consultar.py`, `gemini_client.py` |
| RF-05, RF-08, RF-10, RF-11 | `QueryController.php`, `client.ts` |
| RF-06 | `chroma_client.py`, `rag_service.py` |
| RF-09, RF-23 | `sugerencias.py`, `gemini_client.py` |
| RF-13, RF-14 | `StudentController.php` |
| RF-15 a RF-19 | `DashboardController.php`, `DashboardPage.tsx` |
| RF-20, RF-24 | `reportes.py` (endpoint `/excel`) |
| RF-21, RF-25 | `reportes.py` (endpoint `/pdf`) |
| RNF-01 a RNF-03 | `rag_service.py`, `gemini_client.py`, `reportes.py` |
| RNF-04, RNF-05 | `docker-compose.yml`, `chroma_client.py` |
| RNF-06, RNF-07, RNF-08 | `QueryController.php`, `nginx.conf`, `AuthController.php` |
| RNF-09 | `ChatPage.tsx`, `PracticePage.tsx` |
| RNF-10, RNF-11 | `ChatPage.tsx`, `ThemeContext.tsx` |
| RNF-12, RNF-13 | `rag_service.py`, `docker-compose.yml` |
| RNF-14 | `.env`, `docker-compose.yml` |
| RNF-15, RNF-16 | `docker-compose.yml` |
