# Contexto del Proyecto - IcfesProject

## 1. Información General

- **Título:** Asistente Virtual Basado en IA para la Integración de Componentes Genérico y Específico de las Pruebas Saber Pro en los Programas Académicos de la Universidad de Cundinamarca, Sede Fusagasugá.
- **Autores:** Diego Hernán Guzmán Carrero, Leonardo Juan Felipe Mesa Blanco.
- **Directores:** Jorge Rolando Pardo Morales, Jesús Antonio Villarraga Palomino.
- **Línea de Investigación:** Ingeniería de Sistemas y Computación.
- **Fecha:** 2026.

---

## 2. Problema

- Las pruebas Saber Pro son cruciales para medir la calidad institucional en Colombia.
- Comportamiento deficiente en UCundinamarca: Ingeniería de Sistemas bajó de 154 a 144 puntos; Contaduría Pública se mantiene en 144.
- **Causa raíz:** Falta de estrategias de acompañamiento personalizadas para componentes genéricos y específicos.
- **Brecha tecnológica:** Métodos tradicionales insuficientes; ausencia de tutor IA personalizado.

---

## 3. Pregunta de Investigación

> ¿Es viable construir un asistente virtual basado en RAG que articule bancos de preguntas y marcos de referencia de Saber Pro, ofreciendo retroalimentación precisa a estudiantes y paneles de control analítico a coordinadores?

---

## 4. Objetivos

### General
Desarrollar e implementar un asistente académico inteligente que centralice y procese información de los componentes genérico y específico de las pruebas Saber Pro.

### Específicos
1. Diseñar una base de conocimiento vectorial semánticamente organizada por programa y competencia.
2. Construir los módulos de software: backend (Laravel), microservicio IA con RAG (FastAPI), frontend (React).
3. Validar mediante pruebas técnicas: rendimiento, precisión y seguridad.

---

## 5. Alcance y Delimitaciones

- **Alcance:** Prototipo funcional para estudiantes y coordinadores en sede Fusagasugá. Alimentado con guías ICFES y bancos de preguntas de todas las carreras.
- **Delimitaciones:** Solo entorno de laboratorio controlado. Sin despliegue en producción a gran escala ni estudio longitudinal.

---

## 6. Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Frontend | React 18 |
| Backend Principal | Laravel 11 (PHP) |
| Microservicio IA | FastAPI (Python) |
| Base Datos Vectorial | ChromaDB |
| Base Datos Relacional | PostgreSQL |
| Modelo LLM | Gemini Flash |
| Autenticación | Eloquent ORM + Bcrypt |
| Comunicación | APIs RESTful |

---

## 7. Arquitectura RAG

1. **Indexación:** Documentos → Embeddings → ChromaDB
2. **Recuperación:** Consulta usuario → Embedding → Búsqueda semántica en ChromaDB
3. **Generación:** Fragmentos relevantes + LLM → Respuesta natural y verificada

---

## 8. Metodología: Modelo en Espiral (Boehm, 1988)

| Fase | Descripción |
|---|---|
| Fase 1 | Análisis y Planeación (entrevistas, grupos focales, definición de requerimientos) |
| Fase 2 | Curación de Contenido (recopilación guías ICFES, generación embeddings, carga a ChromaDB) |
| Fase 3 | Desarrollo de Módulos (Laravel + FastAPI + React) |
| Fase 4 | Validación Técnica (rendimiento, precisión anti-alucinaciones, seguridad) |
| Fase 5 | Documentación y Cierre (manuales usuario y técnico) |

---

## 9. Marco Normativo

- **Ley 1581 de 2012:** Protección de datos personales en Colombia.
- **Acuerdo No. 012 del 09 de julio de 2024 (UCundinamarca):** Lineamientos para trabajos de grado.
- **Directrices del ICFES:** Propiedad intelectual y uso de guías oficiales.

---

## 10. Impacto Esperado

- **Estudiantes:** Preparación personalizada, disponible 24/7, democrática.
- **Coordinadores/Docentes:** Reportes analíticos para decisiones pedagógicas.
- **Universidad:** Posicionamiento como pionera en IA educativa en la región.

---

---

## 11. Requisitos Funcionales (RF)

### Módulo Estudiante

| ID | Requisito |
|---|---|
| RF-01 | Registro solicitando cédula, nombre, programa y clave secreta (carácter especial/letra). |
| RF-02 | Almacenar credenciales: cédula, nombre, programa y hash bcrypt de (cédula + clave). |
| RF-03 | Inicio de sesión validando cédula + clave contra hash y generando token de sesión. |
| RF-04 | Mostrar nombre del estudiante y filtrar contenido según su programa tras autenticación. |
| RF-05 | Interfaz de chat para preguntas en lenguaje natural con respuestas de IA. |
| RF-06 | RAG: buscar en ChromaDB fragmentos relevantes filtrados por programa usando similitud semántica. |
| RF-07 | Enviar contexto recuperado a Gemini Flash y mostrar respuesta con fuentes. |
| RF-08 | Historial de chat: solo mensajes de los últimos 5 días, ordenados cronológicamente. |
| RF-09 | Preguntas de práctica aleatorias filtradas por programa y competencia con retroalimentación. |
| RF-10 | El estudiante puede calificar respuestas como "útil" o "no útil". |
| RF-11 | Registrar cada consulta en PostgreSQL: ID anonimizado, pregunta, respuesta, programa, competencia, tiempo, calificación, fecha. |

### Módulo Coordinador

| ID | Requisito |
|---|---|
| RF-12 | Autenticación con correo institucional, contraseña y rol administrativo. |
| RF-13 | Listado de estudiantes: nombre, cédula, programa, fecha de registro (sin clave secreta). |
| RF-14 | Filtro de estudiantes por programa académico. |
| RF-15 | Dashboard: total consultas, estudiantes distintos, consultas del día, promedio calificaciones positivas. |
| RF-16 | Gráfico de barras con distribución de consultas por programa. |
| RF-17 | Gráfico de líneas con tendencia de uso diaria/semanal. |
| RF-18 | Filtros por programa y rango de fechas. |
| RF-19 | Tabla de temas más consultados ordenada por frecuencia. |
| RF-20 | Exportación a Excel (resumen, detalle, tendencia, temas). |
| RF-21 | Exportación a PDF institucional con gráficos y tablas. |

### Módulo Sistema (Backend/Servicios)

| ID | Requisito |
|---|---|
| RF-22 | Endpoint `/consultar` (FastAPI): recibe pregunta + programa, consulta ChromaDB, usa Gemini Flash, devuelve respuesta con fuentes. |
| RF-23 | Endpoint `/sugerencias` (FastAPI): preguntas de práctica por programa y competencia. |
| RF-24 | Endpoint `/reportes/excel` (FastAPI): genera y devuelve archivo Excel. |
| RF-25 | Endpoint `/reportes/pdf` (FastAPI): genera PDF con Plotly + WeasyPrint. |
| RF-26 | Gestión de usuarios (Laravel): registro, autenticación y roles. |
| RF-27 | Almacenamiento de consultas (Laravel) en PostgreSQL. |

---

## 12. Requisitos No Funcionales (RNF)

### Rendimiento
| ID | Requisito |
|---|---|
| RNF-01 | 95% de consultas en < 5 segundos con 20 usuarios concurrentes. |
| RNF-02 | Soportar 20 usuarios simultáneos sin degradación > 50%. |
| RNF-03 | Procesar ≥ 5 consultas por segundo. |
| RNF-04 | Reportes Excel/PDF en < 3 segundos para hasta 10,000 registros. |

### Seguridad
| ID | Requisito |
|---|---|
| RNF-05 | Bcrypt para credenciales + tokens con expiración (Laravel Sanctum). |
| RNF-06 | No almacenar datos personales identificables en registros de consultas. |
| RNF-07 | HTTPS obligatorio. |

### Tecnología
| ID | Requisito |
|---|---|
| RNF-08 | Backend: Laravel 11+ (PHP 8.2) con Sanctum. |
| RNF-09 | IA: FastAPI (Python 3.11+) con ChromaDB y cliente Gemini. |
| RNF-10 | Frontend: React 18+ con TypeScript, Axios y Plotly.js. |
| RNF-11 | BD Relacional: PostgreSQL 15 con migraciones Laravel. |
| RNF-12 | BD Vectorial: ChromaDB persistente con embeddings `all-MiniLM-L6-v2`. |
| RNF-13 | Contenedores: Docker + Docker Compose con servicios separados. |

### Usabilidad y Mantenimiento
| ID | Requisito |
|---|---|
| RNF-14 | Interfaz responsive (móvil y escritorio). |
| RNF-15 | Mensajes de error claros y no técnicos. |
| RNF-16 | Código comentado + README con instrucciones de despliegue. |
| RNF-17 | Git + GitHub con ramas por funcionalidad. |
| RNF-18 | Despliegue con `docker-compose up` sin configuración manual adicional. |
| RNF-19 | Disponibilidad > 99% durante sustentación (túnel Cloudflare o VPS). |
| RNF-20 | Control de consumo API Gemini: no superar $50 USD. |

---

## 13. Stack Tecnológico Detallado

| Capa | Tecnología |
|---|---|
| **Backend Principal** | Laravel 11+ (PHP 8.2), Laravel Sanctum, PostgreSQL 15 |
| **Microservicio IA** | FastAPI (Python 3.11+), ChromaDB, Gemini Flash API, sentence-transformers (`all-MiniLM-L6-v2`), LangChain (opcional) |
| **Reportes** | Plotly (Python), WeasyPrint (PDF), pandas + XlsxWriter (Excel) |
| **Frontend** | React 18+ con TypeScript, Axios, Plotly.js, React Router DOM |
| **Infraestructura** | Docker, Docker Compose, Cloudflare Tunnel / Nginx + VPS |
| **Control de Versiones** | Git + GitHub |
| **Herramientas Dev** | Composer, npm/yarn, pip, Postman/Insomnia, VS Code |

