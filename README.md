# 🎓 Asistente Saber Pro

Asistente virtual basado en IA (RAG) para la preparación de pruebas **Saber Pro** en la Universidad de Cundinamarca, sede Fusagasugá.

## Stack

| Servicio | Tecnología | Puerto local |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | 3000 |
| Backend API | Laravel 11 (PHP 8.2) | 8080 |
| Microservicio IA | FastAPI + Gemini 2.0 Flash + ChromaDB | 8000 |
| Base de datos | PostgreSQL 15 | 5432 |
| Vector DB | ChromaDB | 8001 |

## Inicio rápido

### 1. Configurar variables de entorno

```bash
# En la raíz del proyecto
cp .env.example .env
# Edita .env y agrega tu GEMINI_API_KEY y APP_KEY de Laravel
```

### 2. Levantar con Docker Compose

```bash
docker compose up --build -d
```

### 3. Ejecutar migraciones

```bash
docker exec icfes_backend php artisan migrate --seed
```

### 4. Acceder a la app

- **Estudiantes:** http://localhost:3000/login
- **Coordinadores:** http://localhost:3000/coordinador

---

## Desarrollo local (módulo a módulo)

### Frontend (React)
```bash
cd frontend
npm install
npm run dev          # → http://localhost:5173
```

### Backend (Laravel)
```bash
cd backend
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate
php artisan serve --port=8080
```

### Microservicio IA (FastAPI)
```bash
# Primero levanta ChromaDB
docker run -p 8001:8000 chromadb/chroma

# Luego la IA
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Indexar documentos ICFES

Una vez tengas los documentos oficiales del ICFES en formato `.txt`:

```bash
# Desde dentro del contenedor ai-service, o con Python local:
python -m app.scripts.indexar \
  --directorio data/icfes_docs \
  --programa "Ingeniería de Sistemas"

# Para preguntas de práctica (JSON):
python -m app.scripts.indexar \
  --preguntas data/preguntas/ing_sistemas.json \
  --programa "Ingeniería de Sistemas"
```

---

## Autores

- Diego Hernán Guzmán Carrero
- Leonardo Juan Felipe Mesa Blanco

**Universidad de Cundinamarca — Sede Fusagasugá, 2026**
