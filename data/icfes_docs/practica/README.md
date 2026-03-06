# 📝 Carpeta: Cuadernillos de Preguntas de Práctica

Aquí van los PDFs del tipo **"Cuadernillo de preguntas de práctica"** del ICFES.

## ¿Qué contiene este tipo de cuadernillo?
- Preguntas de práctica **SIN solución explicada**
- Simulación del formato real del examen
- Mayor cantidad de preguntas que los cuadernillos de ejemplos

## ¿Dónde descargarlo?
- https://www.icfes.gov.co/saber-pro → sección "Material de práctica"
- Buscar: *"Cuadernillo de preguntas de práctica"* por módulo

## Módulos disponibles:
- Lectura Crítica
- Razonamiento Cuantitativo
- Comunicación Escrita
- Inglés
- Competencias Ciudadanas
- Módulos específicos por programa

## Cómo indexar:
```bash
docker exec icfes_ai python -m app.scripts.indexar \
  --raiz data/icfes_docs \
  --programa "General"

# O solo práctica:
docker exec icfes_ai python -m app.scripts.indexar \
  --directorio data/icfes_docs/practica \
  --tipo practica \
  --programa "Ingeniería de Sistemas" \
  --fuente "Cuadernillo Práctica ICFES 2024"
```

## Naming recomendado
```
lectura_critica_practica_2024.pdf
razonamiento_cuantitativo_practica_2024.pdf
ingles_practica_2024.pdf
```
