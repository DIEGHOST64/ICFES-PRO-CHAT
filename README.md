# Asistente Saber Pro - ICFES

Asistente virtual con IA (RAG + Gemini) para preparacion de pruebas **Saber Pro**. Universidad de Cundinamarca, sede Fusagasuga.

## Stack

| Servicio | Tecnologia | Puerto |
|----------|-----------|--------|
| Frontend | React 18 + Vite + TypeScript | 3000 |
| Backend | Laravel 11 (PHP 8.2) | 8080 |
| IA | FastAPI + Gemini 2.5 Flash + ChromaDB | 8000 |
| DB | PostgreSQL 15 | 5432 |
| Cache | Redis 7 | 6379 |

## Inicio rapido

```bash
cp .env.example .env              # Editar GEMINI_API_KEY
docker compose up -d --build
docker exec icfes_backend php artisan migrate --seed
```

**Acceso:** `http://localhost:3000`

| Rol | Usuario | Clave |
|-----|---------|-------|
| Creador de Oportunidades | 2026102 | demo123 |
| Gestor de Conocimiento | coordinador@example.com | password |

## Modulos

### Creador de Oportunidades (Estudiante)
- Practica por competencia con **filtro de dificultad** (Basico/Intermedio/Avanzado/Todas)
- **+2000 preguntas** generadas con IA, tablas Markdown y LaTeX
- **Generacion automatica**: 2 preguntas nuevas por visita (background miner)
- Apoyo visual y explicaciones paso a paso con KaTeX
- Modo entrenamiento general y especifico por programa

### Gestor de Conocimiento (Coordinador)
- Dashboard con KPIs, graficos Plotly y tablas de rendimiento
- **Informe estrategico IA** con hallazgos, riesgos y plan de accion
- Exportacion Excel (6 hojas) y PDF con graficos SVG
- Filtros por programa, fecha y presets (7/30/90 dias)

## Banco de preguntas

```bash
# Regenerar Razonamiento Cuantitativo (~300 preguntas, 45 min)
docker exec icfes_ai python app/scripts/pre_generar_rc_clean.py

# Regenerar Especificas por programa
docker exec icfes_ai python app/scripts/pre_generar_especificas.py

# Ver conteo actual
docker exec icfes_ai python -c "
from app.services.chroma_client import ChromaService
ChromaService.initialize()
print(ChromaService.get_collection().count())
"
```

## Documentacion

- **[Documentacion tecnica completa](DOCUMENTACION.md)** — Diagramas C4, ERD, flujos, estados, endpoints
- **[Swagger / OpenAPI](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/DIEGHOST64/ICFES-PRO-CHAT/main/swagger.json)** — Documentacion interactiva de la API (ver online)

> Tambien disponible en `http://localhost:8000/docs` con el servidor corriendo.

## Endpoints principales

| Ruta | Descripcion |
|------|-------------|
| `/sugerencias` | Preguntas de practica (filtro por competencia, dificultad, nivel) |
| `/sugerencias/apoyo-pregunta` | Explicacion y guia visual por pregunta |
| `/sugerencias/datos-curiosos` | Datos curiosos del ICFES |
| `/consultar` | Chat RAG con documentos ICFES |
| `/consultar/guia-imagen` | Generacion de imagen guia |
| `/reportes/excel` | Exportar dashboard a Excel |
| `/reportes/pdf` | Exportar dashboard a PDF |
| `/sugerencias/admin-analisis` | Informe estrategico IA para coordinacion |

## Estructura del proyecto

```
ai-service/           # Microservicio IA (FastAPI)
  app/
    routes/           # sugerencias, consultar, reportes
    services/         # Gemini, ChromaDB, mutator
    config/           # Modulos especificos por programa
    scripts/          # Pre-generacion de banco
  data/               # PDFs ICFES para indexar
backend/              # Laravel 11 (API + autenticacion)
frontend/             # React 18 + Vite (PWA)
data/                 # Documentos ICFES (PDFs)
```

## Autores

Diego Hernan Guzman Carrero | Leonardo Juan Felipe Mesa Blanco
**Universidad de Cundinamarca — 2026**
