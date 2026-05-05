"""
Configuración central de módulos específicos ICFES Saber Pro
por programa académico de la Universidad de Cundinamarca.

Cada programa mapea a sus módulos específicos, temas evaluados,
tipo de pregunta y si requiere tablas/gráficos en el texto base.
"""

# ─────────────────────────────────────────────────────────────
# Mapeo: Programa → Módulos Específicos ICFES
# ─────────────────────────────────────────────────────────────

PROGRAMA_MODULOS_ESPECIFICOS: dict[str, dict] = {

    "Administración de Empresas": {
        "slug": "admin_empresas",
        "modulos": [
            {
                "nombre": "Gestión de Organizaciones",
                "temas": [
                    "Planeación estratégica y análisis DOFA",
                    "Estructura organizacional y diseño de cargos",
                    "Gestión del talento humano y liderazgo",
                    "Marketing, segmentación y comportamiento del consumidor",
                    "Cadena de valor y ventaja competitiva",
                    "Análisis del entorno empresarial (PESTEL)",
                    "Responsabilidad social empresarial",
                    "Indicadores de gestión y balanced scorecard",
                ],
                "tipo_preguntas": "caso_empresa",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Indicador | Meta | Resultado | Cumplimiento |\n"
                    "|---|---|---|---|\n"
                    "| Ventas Q1 | $120M | $108M | 90% |\n"
                    "| Rotación personal | <10% | 14% | No cumple |\n"
                    "| Satisfacción cliente | >85% | 88% | Cumple |"
                ),
            },
            {
                "nombre": "Formulación de Proyectos de Desarrollo",
                "temas": [
                    "Marco lógico y árbol de problemas",
                    "Análisis de stakeholders e involucrados",
                    "Indicadores de gestión e impacto",
                    "Evaluación ex-ante y ex-post de proyectos",
                    "Presupuestación y fuentes de financiación",
                    "Metodologías de formulación (MGA, PMI)",
                    "Viabilidad técnica, económica y social",
                ],
                "tipo_preguntas": "caso_proyecto",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Componente | Presupuesto | Ejecutado | % Avance |\n"
                    "|---|---|---|---|\n"
                    "| Capacitación | $45.000.000 | $38.500.000 | 85.6% |\n"
                    "| Infraestructura | $120.000.000 | $72.000.000 | 60.0% |\n"
                    "| Monitoreo | $15.000.000 | $15.000.000 | 100% |"
                ),
            },
        ],
    },

    "Contaduría Pública": {
        "slug": "contaduria",
        "modulos": [
            {
                "nombre": "Información y Control Contable",
                "temas": [
                    "Registro contable bajo NIIF/NIC",
                    "Partida doble, débitos y créditos",
                    "Estados financieros (Balance, Estado de Resultados, Flujo de Efectivo)",
                    "Control interno y auditoría",
                    "Conciliación bancaria",
                    "Análisis de cuentas y ajustes contables",
                    "Inventarios (PEPS, promedio ponderado)",
                    "Depreciación y amortización de activos",
                ],
                "tipo_preguntas": "caso_contable",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Cuenta | Debe | Haber |\n"
                    "|---|---|---|\n"
                    "| Caja | $5.000.000 | |\n"
                    "| Bancos | | $3.200.000 |\n"
                    "| Capital social | | $1.800.000 |"
                ),
            },
            {
                "nombre": "Gestión Financiera",
                "temas": [
                    "Análisis de razones financieras (liquidez, rentabilidad, endeudamiento)",
                    "Valor presente neto (VPN) y tasa interna de retorno (TIR)",
                    "Punto de equilibrio",
                    "Presupuesto maestro y flujo de caja proyectado",
                    "Costo de capital y estructura financiera",
                    "Evaluación de proyectos de inversión",
                    "Gestión del capital de trabajo",
                ],
                "tipo_preguntas": "caso_financiero",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Razón Financiera | Valor | Referencia Sector |\n"
                    "|---|---|---|\n"
                    "| Liquidez corriente | 1.8 | >1.5 |\n"
                    "| Endeudamiento | 62% | <60% |\n"
                    "| ROE | 12.4% | >10% |"
                ),
            },
        ],
    },

    "Ingeniería de Sistemas y Computación": {
        "slug": "ing_sistemas",
        "modulos": [
            {
                "nombre": "Diseño de Software",
                "temas": [
                    "Patrones de diseño (MVC, Singleton, Observer, Factory)",
                    "Diagramas UML (clases, secuencia, casos de uso)",
                    "Principios SOLID y clean code",
                    "Arquitectura de software (monolítica, microservicios, capas)",
                    "Bases de datos relacionales y normalización",
                    "Algoritmos y estructuras de datos",
                    "Testing y aseguramiento de calidad",
                    "Metodologías ágiles (Scrum, Kanban)",
                ],
                "tipo_preguntas": "caso_tecnico",
                "requiere_tabla": False,
            },
            {
                "nombre": "Formulación de Proyectos de Ingeniería",
                "temas": [
                    "Gestión de alcance y requisitos",
                    "Estimación de costos y cronogramas",
                    "Análisis de riesgos en proyectos de TI",
                    "Metodología PMI y ciclo de vida del proyecto",
                    "Métricas de calidad de software",
                    "Evaluación de viabilidad técnica",
                ],
                "tipo_preguntas": "caso_proyecto_ing",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Sprint | Historia de Usuario | Puntos | Estado |\n"
                    "|---|---|---|---|\n"
                    "| Sprint 1 | Login y registro | 8 | Completado |\n"
                    "| Sprint 2 | CRUD productos | 13 | En progreso |\n"
                    "| Sprint 3 | Reportes | 5 | Pendiente |"
                ),
            },
        ],
    },

    "Ingeniería Electrónica": {
        "slug": "ing_electronica",
        "modulos": [
            {
                "nombre": "Diseño de Sistemas de Control",
                "temas": [
                    "Sistemas de control en lazo abierto y cerrado",
                    "Función de transferencia y diagrama de bloques",
                    "Estabilidad (criterio de Routh-Hurwitz, Nyquist)",
                    "Controladores PID (proporcional, integral, derivativo)",
                    "Respuesta en frecuencia (diagramas de Bode)",
                    "Modelado de sistemas dinámicos",
                    "Señales y sistemas discretos",
                    "Electrónica de potencia y conversores",
                ],
                "tipo_preguntas": "caso_tecnico",
                "requiere_tabla": True,
                "requiere_latex": True,
                "ejemplo_tabla": (
                    "| Componente | Valor | Unidad |\n"
                    "|---|---|---|\n"
                    "| Resistencia R1 | 10 | kΩ |\n"
                    "| Capacitor C1 | 100 | μF |\n"
                    "| Inductancia L1 | 47 | mH |"
                ),
            },
            {
                "nombre": "Formulación de Proyectos de Ingeniería",
                "temas": [
                    "Gestión de proyectos electrónicos",
                    "Estimación de presupuesto para prototipos",
                    "Análisis de factibilidad técnica y económica",
                    "Normatividad técnica (IEEE, IEC)",
                    "Metodología de diseño de circuitos",
                    "Documentación técnica y planos",
                ],
                "tipo_preguntas": "caso_proyecto_ing",
                "requiere_tabla": True,
            },
        ],
    },

    "Ingeniería Agronómica": {
        "slug": "ing_agronomica",
        "modulos": [
            {
                "nombre": "Producción Agrícola",
                "temas": [
                    "Manejo integrado de cultivos (MIC)",
                    "Fertilización y nutrición vegetal",
                    "Manejo de suelos y análisis edafológico",
                    "Control de plagas y enfermedades (MIP)",
                    "Sistemas de riego y drenaje",
                    "Fisiología vegetal y fenología",
                    "Agricultura sostenible y buenas prácticas agrícolas (BPA)",
                    "Economía agrícola y costos de producción",
                ],
                "tipo_preguntas": "caso_agronomico",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Nutriente | Nivel en suelo | Nivel óptimo | Recomendación |\n"
                    "|---|---|---|---|\n"
                    "| Nitrógeno (N) | 18 ppm | 25-40 ppm | Aplicar urea |\n"
                    "| Fósforo (P) | 45 ppm | 20-40 ppm | Adecuado |\n"
                    "| Potasio (K) | 0.15 meq/100g | 0.3-0.6 | Aplicar KCl |"
                ),
            },
            {
                "nombre": "Pensamiento Científico - Ciencias Naturales",
                "temas": [
                    "Método científico y diseño experimental",
                    "Análisis estadístico de datos agrícolas",
                    "Ecología y ecosistemas",
                    "Bioquímica y procesos metabólicos en plantas",
                    "Genética y mejoramiento vegetal",
                    "Microbiología del suelo",
                ],
                "tipo_preguntas": "caso_cientifico",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Tratamiento | Rendimiento (t/ha) | Desv. Estándar |\n"
                    "|---|---|---|\n"
                    "| Control | 3.2 | 0.45 |\n"
                    "| Fertilizante A | 4.1 | 0.38 |\n"
                    "| Fertilizante B | 4.8 | 0.52 |\n"
                    "| A + B combinado | 5.3 | 0.41 |"
                ),
            },
        ],
    },

    "Zootecnia": {
        "slug": "zootecnia",
        "modulos": [
            {
                "nombre": "Producción Pecuaria",
                "temas": [
                    "Nutrición y alimentación animal",
                    "Sistemas de producción ganadera (extensivo, intensivo, semi-intensivo)",
                    "Reproducción y mejoramiento genético animal",
                    "Sanidad animal y planes sanitarios",
                    "Bienestar animal y normatividad",
                    "Manejo de praderas y pastoreo rotacional",
                    "Producción avícola, porcina y bovina",
                    "Economía pecuaria y costos de producción",
                ],
                "tipo_preguntas": "caso_pecuario",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Parámetro | Finca A | Finca B | Referencia |\n"
                    "|---|---|---|---|\n"
                    "| Carga animal (UA/ha) | 2.5 | 1.8 | 2.0-3.0 |\n"
                    "| Intervalo entre partos (días) | 420 | 380 | <400 |\n"
                    "| Ganancia diaria peso (g) | 650 | 780 | >700 |"
                ),
            },
            {
                "nombre": "Pensamiento Científico - Ciencias Naturales",
                "temas": [
                    "Método científico y diseño experimental en producción animal",
                    "Análisis estadístico de datos zootécnicos",
                    "Fisiología animal",
                    "Genética cuantitativa y heredabilidad",
                    "Ecología y manejo ambiental en producción animal",
                    "Microbiología ruminal y digestión",
                ],
                "tipo_preguntas": "caso_cientifico",
                "requiere_tabla": True,
            },
        ],
    },

    "Licenciatura en Ciencias Sociales": {
        "slug": "lic_sociales",
        "modulos": [
            {
                "nombre": "Enseñar",
                "temas": [
                    "Didáctica de las ciencias sociales",
                    "Estrategias pedagógicas y metodologías activas",
                    "Planeación curricular y diseño de unidades didácticas",
                    "Uso de recursos educativos y TIC en el aula",
                    "Transposición didáctica del saber disciplinar",
                    "Aprendizaje basado en problemas (ABP) y proyectos",
                    "Evaluación formativa vs sumativa",
                ],
                "tipo_preguntas": "caso_pedagogico",
                "requiere_tabla": False,
            },
            {
                "nombre": "Evaluar",
                "temas": [
                    "Tipos de evaluación (diagnóstica, formativa, sumativa)",
                    "Diseño de instrumentos de evaluación (rúbricas, matrices)",
                    "Retroalimentación efectiva",
                    "Análisis de resultados y toma de decisiones pedagógicas",
                    "Evaluación por competencias",
                    "Normatividad educativa colombiana sobre evaluación",
                ],
                "tipo_preguntas": "caso_evaluacion",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Criterio | Nivel Superior | Nivel Alto | Nivel Básico | Nivel Bajo |\n"
                    "|---|---|---|---|---|\n"
                    "| Argumentación | Sustenta con evidencias | Sustenta parcialmente | Opina sin evidencia | No argumenta |\n"
                    "| Análisis crítico | Contrasta fuentes | Identifica postura | Describe sin analizar | No analiza |"
                ),
            },
            {
                "nombre": "Formar",
                "temas": [
                    "Formación ciudadana y convivencia escolar",
                    "Desarrollo moral y ético del estudiante",
                    "Inclusión educativa y atención a la diversidad",
                    "Proyecto Educativo Institucional (PEI)",
                    "Relación escuela-comunidad",
                    "Normatividad educativa colombiana (Ley 115, Decreto 1290)",
                    "Gestión de aula y clima escolar",
                ],
                "tipo_preguntas": "caso_formacion",
                "requiere_tabla": False,
            },
        ],
    },

    "Licenciatura en Educación Física, Recreación y Deportes": {
        "slug": "lic_edufisica",
        "modulos": [
            {
                "nombre": "Enseñar",
                "temas": [
                    "Didáctica de la educación física y el deporte",
                    "Planeación de sesiones de clase en educación física",
                    "Desarrollo motor y etapas del crecimiento",
                    "Estilos de enseñanza en educación física (Mosston)",
                    "Adaptaciones curriculares para poblaciones especiales",
                    "Juego como herramienta pedagógica",
                    "Actividad física, salud y hábitos de vida saludable",
                ],
                "tipo_preguntas": "caso_pedagogico",
                "requiere_tabla": False,
            },
            {
                "nombre": "Evaluar",
                "temas": [
                    "Evaluación de capacidades físicas (test de Cooper, flexibilidad)",
                    "Instrumentos de evaluación en educación física",
                    "Valoración del desarrollo motor",
                    "Evaluación por competencias motrices",
                    "Análisis e interpretación de resultados de desempeño físico",
                    "Retroalimentación en contextos deportivos",
                ],
                "tipo_preguntas": "caso_evaluacion",
                "requiere_tabla": True,
                "ejemplo_tabla": (
                    "| Test | Estudiante A | Estudiante B | Promedio edad |\n"
                    "|---|---|---|---|\n"
                    "| Cooper 12 min (m) | 2100 | 1850 | 2000 |\n"
                    "| Flexibilidad (cm) | 12 | 8 | 10 |\n"
                    "| Salto horizontal (cm) | 180 | 165 | 170 |"
                ),
            },
            {
                "nombre": "Formar",
                "temas": [
                    "Formación integral a través del deporte",
                    "Valores y fair play en la actividad deportiva",
                    "Inclusión y adaptación en educación física",
                    "Recreación y aprovechamiento del tiempo libre",
                    "Cuerpo, identidad y expresión corporal",
                    "Normatividad educativa sobre educación física en Colombia",
                ],
                "tipo_preguntas": "caso_formacion",
                "requiere_tabla": False,
            },
        ],
    },
}


# ─────────────────────────────────────────────────────────────
# Helpers de acceso rápido
# ─────────────────────────────────────────────────────────────

def get_programa_key(programa: str) -> str | None:
    """Devuelve el nombre exacto de un programa configurado, buscando por coincidencia exacta o parcial."""
    programa_norm = programa.strip()
    if programa_norm in PROGRAMA_MODULOS_ESPECIFICOS:
        return programa_norm

    programa_lower = programa_norm.lower()
    for key, config in PROGRAMA_MODULOS_ESPECIFICOS.items():
        if programa_lower in key.lower() or key.lower() in programa_lower:
            return key
        if config["slug"] in programa_lower.replace(" ", "_"):
            return key
    return None


def get_programa_config(programa: str) -> dict | None:
    """Devuelve la configuración de un programa, buscando por nombre exacto o parcial."""
    key = get_programa_key(programa)
    return PROGRAMA_MODULOS_ESPECIFICOS.get(key) if key else None


def get_all_programas() -> list[str]:
    """Lista de todos los programas configurados."""
    return list(PROGRAMA_MODULOS_ESPECIFICOS.keys())


def get_modulos_for_programa(programa: str) -> list[dict]:
    """Devuelve los módulos específicos de un programa."""
    config = get_programa_config(programa)
    if not config:
        return []
    return config.get("modulos", [])


def get_all_modulo_names() -> list[str]:
    """Lista única de todos los nombres de módulos específicos."""
    names: set[str] = set()
    for config in PROGRAMA_MODULOS_ESPECIFICOS.values():
        for modulo in config.get("modulos", []):
            names.add(modulo["nombre"])
    return sorted(names)
