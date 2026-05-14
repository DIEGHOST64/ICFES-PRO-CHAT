# Cronograma de Desarrollo — Ascenso Pro

Metodología RUP (Rational Unified Process) | 8 semanas totales

---

## Diagrama de Gantt

```
SEMANA         S1    S2    S3    S4    S5    S6    S7    S8
               │     │     │     │     │     │     │     │
───────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
FASE 1: INICIO ████████████│     │     │     │     │     │
  RF y alcance ████████████│     │     │     │     │     │
  Stack/Arq    ████████████│     │     │     │     │     │
  MVP funcional█████████████│     │     │     │     │     │
───────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
FASE 2: ELABOR ████████████████████████│     │     │     │
  Pipeline RAG      │██████████████████│     │     │     │
  DB (13 tablas)    │██████████████████│     │     │     │
  Práctica adapt.   │     ████████████████│     │     │     │
  Riesgos mitigados │██████████████████│     │     │     │
───────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
FASE 3: CONSTR │     │     │█████████████████████████████│
  It.1: Chat    │     │     │█████│     │     │     │     │
  It.2: Práctica│     │     │     █████│     │     │     │
  It.3: Dashboard│    │     │     │█████│     │     │     │
  It.4: PDF/Excel│    │     │     │     █████│     │     │
  It.5: Chat IA  │     │     │     │     │█████│     │     │
  It.6: Responsive│    │     │     │     │     █████│     │
  It.7: Deploy   │     │     │     │     │     │█████│     │
  It.8: Sesiones │     │     │     │     │     │     ██████│
───────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
FASE 4: TRANSI │     │     │     │     │     │     │██████████
  Pruebas reales│     │     │     │     │     │     │█████│
  Bugs correg.  │     │     │     │     │     │     │██████████
  Documentación │     │     │     │     │     │     │     ████████
  Manual usuario│     │     │     │     │     │     │     ████████
  Métricas      │     │     │     │     │     │     │     ████████
```

---

## Tabla de Actividades por Semana

### Semana 1 — Fase de Inicio

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-2 | Análisis del problema y necesidades | Documento de contexto |
| 2-3 | Definición de 28 requisitos funcionales (RF-01 a RF-28) | Lista de RF |
| 3-4 | Selección y justificación del stack tecnológico | Stack definido |
| 4-5 | Diseño de arquitectura C4 (6 microservicios) | Diagrama C4 |
| 5-7 | Implementación del MVP: login, registro, chat básico | MVP funcional |

### Semana 2 — Fase de Inicio / Elaboración

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-2 | Estudio del corpus documental ICFES | Corpus seleccionado |
| 2-5 | Indexación de PDFs en ChromaDB (2,091 documentos) | Base vectorial |
| 5-7 | Pipeline RAG: embeddings → búsqueda → generación | RAG funcional |

### Semana 3 — Fase de Elaboración

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-3 | Diseño e implementación de base de datos (13 tablas) | Esquema PostgreSQL |
| 3-5 | Sistema de práctica adaptativa (6 competencias) | Módulo de práctica |
| 5-7 | Mitigación de riesgos técnicos (ChromaDB, Gemini) | Riesgos controlados |

### Semana 4 — Fase de Elaboración / Construcción

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-2 | Iteración 1: Chat conversacional completo, historial | Chat mejorado |
| 2-4 | Validación temprana con corpus ICFES | Pruebas RAG |
| 4-7 | Iteración 2: Inglés (7 partes), ensayos, calificaciones | Práctica avanzada |

### Semana 5 — Fase de Construcción

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-3 | Iteración 3: Dashboard del gestor (13 secciones) | Panel de control |
| 3-5 | Iteración 4: Exportación PDF (13 secciones) y Excel (11 hojas) | Reportes |
| 5-7 | Iteración 5: Chat IA del coordinador con datos completos | Modo IA |

### Semana 6 — Fase de Construcción

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-3 | Iteración 6: Diseño responsive (móvil, tablet, escritorio) | UI adaptativa |
| 3-5 | Iteración 7: Despliegue en VPS, dominio, HTTPS | Producción |
| 5-7 | Iteración 8: Sesiones de chat, persistencia visual | Funcionalidad completa |

### Semana 7 — Fase de Construcción / Transición

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-3 | Pruebas con usuarios reales (estudiantes + coordinador) | Feedback |
| 3-5 | Corrección de bugs detectados (10 bugs) | Sistema estable |
| 5-7 | Ajustes finales de UI/UX | Producto pulido |

### Semana 8 — Fase de Transición

| Día | Actividad | Entregable |
|-----|-----------|-----------|
| 1-2 | Elaboración de documentación técnica (16 secciones) | DOCUMENTACION.md |
| 2-3 | Elaboración de manual de usuario (29 capturas) | MANUAL_USUARIO.md |
| 3-4 | Documentación de requisitos (28 RF + 16 RNF) | REQUISITOS.md |
| 4-5 | Documentación de resultados (28 casos de prueba) | RESULTADOS.md |
| 5-6 | Documentación de metodología RUP | METODOLOGIA_RUP.md |
| 6-7 | Generación de PDFs finales con portada institucional | PDFs entregables |
| 7-8 | Preparación para presentación y defensa | Sustentación |

---

## Resumen por Fase

| Fase | Duración | Iteraciones | Entregables principales |
|------|----------|------------|------------------------|
| **Inicio** | 1.5 semanas | — | RF, arquitectura, stack, MVP |
| **Elaboración** | 2 semanas | — | RAG pipeline, BD, práctica adaptativa |
| **Construcción** | 3.5 semanas | 8 iteraciones | Chat, práctica, dashboard, PDF, IA, responsive, deploy, sesiones |
| **Transición** | 1 semana | — | Pruebas, bugs, 5 documentos, PDFs finales |
| **TOTAL** | **8 semanas** | **8 iteraciones** | Prototipo funcional completo |

---

## Hitos Clave (Milestones)

| Hito | Semana | Descripción |
|------|--------|-------------|
| **M1 — MVP** | S1 | Login, registro y chat básico funcional |
| **M2 — RAG** | S2 | Pipeline RAG con 2,091 documentos indexados |
| **M3 — Práctica** | S3 | Módulo de práctica adaptativa con 6 competencias |
| **M4 — Dashboard** | S5 | Panel del coordinador con 13 secciones y KPIs |
| **M5 — Deploy** | S6 | Sistema en producción con HTTPS y dominio |
| **M6 — Validación** | S7 | Pruebas con usuarios reales, 10 bugs corregidos |
| **M7 — Documentación** | S8 | 5 documentos técnicos + PDFs con portada |
| **M8 — Entrega final** | S8 | Prototipo funcional + documentación completa |

---

## Distribución del Esfuerzo

```
                    Horas estimadas: ~320 horas totales
                    
                    Documentación  ████████████████ 20%
                    Pruebas        ██████████ 12%
                    Deploy/DevOps  ██████ 8%
                    Frontend       ████████████████████████ 30%
                    Backend        ████████████████ 20%
                    IA / RAG       ████████ 10%
```

---

*Cronograma del proyecto Ascenso Pro · Metodología RUP · 8 semanas*
