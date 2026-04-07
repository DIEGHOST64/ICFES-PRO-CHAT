// ── Tipos globales del proyecto ──────────────────────────

export interface Student {
    nombre: string;
    programa: string;
}

export interface Coordinator {
    nombre: string;
    email: string;
}

export interface AuthToken {
    token: string;
    role: 'student' | 'coordinator';
}

export interface QueryRecord {
    id: number;
    pregunta: string;
    respuesta: string;
    competencia?: string;
    calificacion?: boolean | null;
    es_practica?: boolean;
    acierto?: boolean | null;
    created_at: string;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: string[];
    guideImageUrl?: string;
    guideImageCaption?: string;
    guideImageLoading?: boolean;
    guideImageModel?: string;
    guideImageError?: string;
    latexFormula?: string;
    latexExplanation?: string;
    guideTitle?: string;
    guideSteps?: string[];
    timestamp: Date;
    rated?: boolean | null;
    queryId?: number;
    streaming?: boolean;
}

export interface Pregunta {
    id: string;
    texto_base?: string;
    enunciado: string;
    opciones: string[];
    respuesta_correcta: string;
    explicacion: string;
    competencia: string;
    programa: string;
    tipo_ingles?: 'reading' | 'vocabulary' | 'grammar' | string;
    nivel_cefr?: 'A2' | 'B1' | string;
    nivel_dificultad?: 'basico' | 'intermedio' | 'avanzado' | string;
    bloque_id?: string;
    orden_en_bloque?: number;
    preguntas_en_bloque?: number;
}

export interface DashboardMetrics {
    total_consultas: number;
    estudiantes_unicos: number;
    consultas_hoy: number;
    promedio_positivas: number | string;
    total_estudiantes: number;
}

export interface ChartDataPoint {
    programa?: string;
    competencia?: string;
    fecha?: string;
    total: number;
}

export interface PracticeStudentMetric {
    programa: string;
    estudiante: string;
    student_hash: string;
    intentos: number;
    aciertos: number;
    puntaje_promedio: number;
}

export interface PracticeCompetenceMetric {
    programa: string;
    competencia: string;
    intentos: number;
    aciertos: number;
    promedio_competencia: number;
}

export interface LevelProgressPoint {
    fecha: string;
    competencia: string;
    intentos: number;
    aciertos: number;
    tasa_acierto: number;
    nivel_promedio: number;
}

export type Theme = 'dark' | 'light';
