# REPORTE DE HANDOFF Y RESUMEN DE PROYECTO: ICFES PRO AI (ABRIL 2026)

Este documento sirve como puente para que el usuario formatée su PC y el próximo agente de IA pueda retomar el trabajo sin fricciones.

---

## 1. ESTADO ACTUAL DEL PROYECTO (MAINTENANCE MODE)

El proyecto **ICFES Pro AI** es una plataforma de preparación para el examen Saber Pro que utiliza Modelos de Lenguaje (Gemini) y Bases de Datos Vectoriales para generar y servir simulacros de alta calidad.

### Arquitectura Principal
- **AI Service (Python/FastAPI):** Gestiona la generación asíncrona de preguntas. Usa un "Background Miner" para llenar el banco de preguntas mientras el usuario navega.
- **Base de Datos Vectorial (ChromaDB):** Almacena ~1300+ preguntas ya validadas y categorizadas.
- **Backend (Laravel/Postgres):** Maneja la lógica de negocio, usuarios y persistencia tradicional.
- **Frontend (React/Vite):** Interfaz de usuario con soporte para LaTeX (KaTeX) y componentes dinámicos.

### Logros Recientes
- **Estabilización de Inglés:** Filtrado de niveles CEFR (A1-B2) y corrección de "Spanglish" en prompts.
- **Razonamiento Cuantitativo:** Implementación de tablas en Markdown y fórmulas en LaTeX que el frontend ya renderiza.
- **Comunicación Escrita:** Generación de prompts de ensayo basados en debates éticos actuales.
- **Persistencia Crítica:** Corrección de fallos donde el minero generaba preguntas pero no las guardaba en disco.

---

## 2. INSTRUCCIONES DE RESPALDO (CRÍTICO ANTES DE FORMATEAR)

**NO FORMATEES sin asegurar estos archivos:**

> **¡ATENCIÓN! - Archivos que NO están en Git (o suelen ignorarse):**
> 1. **Archivo `.env`:** Contiene las `GEMINI_API_KEY` y las llaves de Laravel. Sin esto, el sistema no arrancará.
> 2. **Carpeta `data/`:** Aquí reside la base de datos de ChromaDB. Si se pierde, habrá que pagar de nuevo a Google para regenerar las 1300+ preguntas.
> 3. **Base de Datos Postgres:** Si usas Docker con volúmenes locales, asegúrate de respaldar los volúmenes de Docker o hacer un export (`pg_dump`).

**Recomendación:** Comprime toda la carpeta raíz `ICFES-PRO-CHAT/` en un `.zip` y súbelo a una nube privada o disco externo.

---

## 3. ESTADO DE LOS MÓDULOS DE IA

| Módulo | Estado | Notas del Agente Anterior |
| :--- | :--- | :--- |
| **Inglés** | ✅ Completado | Banco robusto (Partes 1-7). Filtrado de avisos cortos corregido. |
| **Razonamiento** | ⚠️ En Limpieza | Se eliminaron "alucinaciones" de texto basura. Fórmulas LaTeX validadas. |
| **Lectura Crítica** | ✅ Estable | Basado en fragmentos de cuadernillos oficiales. |
| **Ciudadanas** | ✅ Estable | Enfoque en constitución y competencias ciudadanas. |
| **Escrita** | ✅ Estable | Genera temas de debate en lugar de preguntas de opción múltiple. |

---

## 4. INSTRUCCIONES PARA EL PRÓXIMO AGENTE (READ ME)

Hola, próximo agente. Aquí es donde debes enfocarte:

1. **Configuración de Entorno:**
   - Asegúrate de que el `.env` esté presente.
   - Corre `docker-compose up -d`.
   - Verifica la base de datos con `python ai-service/check_db.py`.

2. **Tareas Pendientes:**
   - **Limpieza de Razonamiento Cuantitativo:** Continuar revisando que las preguntas generadas no tengan texto administrativo residual (ej: "Aquí tienes tu pregunta...").
   - **Escalabilidad:** Evaluar la migración de ChromaDB de local a un servicio en la nube si el tráfico aumenta.
   - **Frontend:** Asegurar que los nuevos tipos de tablas en Razonamiento Cuantitativo se vean bien en dispositivos móviles.

3. **Contexto Técnico:**
   - El archivo `ai-service/app/services/gemini_client.py` es el corazón de la IA.
   - El archivo `ai-service/app/routes/sugerencias.py` es donde se ensamblan los simulacros.

---

Si encuentras errores de importación al llegar, revisa `IA_MODULE_STATUS.md` en `ai-service/docs/`. Allí documentamos cómo corregimos los errores de *Shadowing* y *UnboundLocalError*.

**¡Buena suerte con el nuevo sistema formateado!**
