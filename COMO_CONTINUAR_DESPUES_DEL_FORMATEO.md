# CONTINUAR DESPUÉS DEL FORMATEO – PROYECTO ICFES (ABRIL 2026)

## ¿Qué hacer después de restaurar el entorno?

Este archivo contiene instrucciones detalladas para que cualquier agente, desarrollador o colaborador pueda continuar el desarrollo del sistema de práctica ICFES exactamente donde se dejó, sin perder contexto ni tiempo.

---

## 1. Objetivo y Estado Actual
- El sistema prioriza preguntas curadas (alta calidad, contexto claro, revisadas manualmente) y mezcla con preguntas generadas por IA si la cantidad lo requiere.
- El endpoint `/sugerencias` ya funciona y devuelve preguntas curadas con contexto enriquecido y LaTeX donde aplica.
- El frontend y backend están integrados y validados.
- No se usan ni deben buscarse datos sensibles ni contraseñas.

---

## 2. Estructura y Archivos Clave
- **Preguntas curadas:** `data/icfes_docs/general/ejemplos/preguntas_curadas_iniciales_2019_2021.json`
- **Script de curación:** `ai-service/app/scripts/curar_preguntas_icfes.py`
- **Script de indexado:** `ai-service/app/scripts/indexar.py`
- **Lógica de endpoint:** `ai-service/app/routes/sugerencias.py`
- **Frontend:** `frontend/` (React, Vite)
- **Orquestación:** `docker-compose.yml`

---

## 3. Flujo de trabajo para continuar

1. **Ampliar el lote de preguntas curadas**
   - Genera más preguntas por área/competencia (idealmente 15+ por área).
   - Asegúrate de que cada pregunta tenga contexto claro y, si es necesario, notación LaTeX.
   - Ejemplo de pregunta curada:
     ```json
     {
       "id": "mat_001",
       "area": "Matemáticas",
       "competencia": "Razonamiento cuantitativo",
       "enunciado": "¿Cuál es el valor de $x$ en la ecuación $2x + 3 = 7$?",
       "texto_base": "Para resolver ecuaciones lineales, se despeja la incógnita aplicando operaciones inversas.",
       "opciones": ["1", "2", "3", "4"],
       "respuesta_correcta": "2",
       "explicacion": "Despejando: $2x = 4 \\Rightarrow x = 2$.",
       "latex": true
     }
     ```

2. **Indexar el nuevo lote**
   - Ejecuta el script de indexado cada vez que actualices el JSON de preguntas curadas.
   - Comando típico:
     ```bash
     python ai-service/app/scripts/indexar.py
     ```

3. **Validar el endpoint y frontend**
   - Asegúrate de que `/sugerencias` devuelve correctamente las nuevas preguntas.
   - El frontend debe mostrar correctamente el LaTeX (usa KaTeX o MathJax).

4. **Mantener la mezcla aleatoria y priorización de calidad**
   - El sistema debe seguir mezclando preguntas curadas y generadas si la cantidad lo requiere.

5. **Documentar cambios relevantes**
   - Si modificas la estructura de datos o el flujo, documenta aquí o en el README principal.

---

## 4. Seguridad y privacidad
- No busques, pidas ni almacenes credenciales ni datos sensibles.
- Todo lo necesario está en los archivos y scripts del repositorio.

---

## 5. Si tienes dudas
- Revisa los scripts y archivos mencionados.
- Usa el ejemplo de pregunta curada como referencia.
- Si el frontend no renderiza LaTeX, revisa la integración de KaTeX/MathJax.
- Si surgen errores, documenta y corrige en el flujo correspondiente.

---

¡Con este archivo puedes continuar el desarrollo sin perder contexto ni tiempo!