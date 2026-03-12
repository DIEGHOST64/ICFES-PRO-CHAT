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
    created_at: string;
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: string[];
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
}

export interface DashboardMetrics {
    total_consultas: number;
    estudiantes_unicos: number;
    consultas_hoy: number;
    promedio_positivas: string;
    total_estudiantes: number;
}

export interface ChartDataPoint {
    programa?: string;
    competencia?: string;
    fecha?: string;
    total: number;
}

export type Theme = 'dark' | 'light';
