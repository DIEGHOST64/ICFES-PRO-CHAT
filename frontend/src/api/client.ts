import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8080/api',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    timeout: 10000,
});

// Incrustar token automáticamente en cada request
api.interceptors.request.use(config => {
    const token = localStorage.getItem('sp_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// Manejo de 401 — token expirado
api.interceptors.response.use(
    res => res,
    err => {
        if (err.response?.status === 401) {
            const currentToken = localStorage.getItem('sp_token');
            const authHeader = err?.config?.headers?.Authorization || err?.config?.headers?.authorization;
            const requestToken = typeof authHeader === 'string' && authHeader.startsWith('Bearer ')
                ? authHeader.slice(7)
                : null;

            // Ignorar 401 de requests sin token o de sesiones viejas (race tras relogin).
            if (!requestToken || (currentToken && requestToken !== currentToken)) {
                return Promise.reject(err);
            }

            ['sp_token', 'sp_role', 'sp_student', 'sp_coordinator'].forEach(k => localStorage.removeItem(k));
            window.location.href = '/login';
        }
        return Promise.reject(err);
    }
);

export default api;

// ── Endpoints tipados ──────────────────────────────────

export const authAPI = {
    registerStudent: (data: { cedula: string; nombre: string; programa: string; clave_secreta: string }) =>
        api.post('/auth/register', data),
    loginStudent: (data: { cedula: string; clave_secreta: string }) =>
        api.post('/auth/login', data),
    loginCoordinator: (data: { email: string; password: string }) =>
        api.post('/auth/coordinator/login', data),
    logout: () => api.post('/auth/logout'),
};

export const aiAPI = {
    consultar: (data: { pregunta: string; programa: string }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/consultar`, data),
    guiaImagen: (data: { pregunta: string; respuesta: string; programa: string }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/consultar/guia-imagen`, data),
    sugerencias: (params: { programa: string; competencia?: string; cantidad?: number; nivel_objetivo?: 'A2' | 'B1'; dificultad_objetivo?: 'basico' | 'intermedio' | 'avanzado' }) =>
        axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/sugerencias`, { params }),
    datosCuriosos: (data: { programa: string; competencia: string; cantidad?: number }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/sugerencias/datos-curiosos`, data),
    apoyoPregunta: (data: { programa: string; competencia: string; enunciado: string; texto_base?: string; opciones?: string[]; explicacion?: string }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/sugerencias/apoyo-pregunta`, data),
    evaluarEnsayo: (data: { tema: string; ensayo: string }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/sugerencias/evaluar-ensayo`, data),
    adminAnalisis: (data: { task: string; analytics_context: Record<string, unknown> }) =>
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/sugerencias/admin-analisis`, data),
    exportExcel: (params: Record<string, string>) => {
        const token = localStorage.getItem('sp_token');
        return axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/reportes/excel`, {
            params, responseType: 'blob',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
    },
    exportPDF: (params: Record<string, string>) => {
        const token = localStorage.getItem('sp_token');
        return axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000'}/reportes/pdf`, {
            params, responseType: 'blob',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
    },
};

export const queriesAPI = {
    save: (data: object) => api.post('/queries', data),
    history: () => api.get('/queries/history'),
    rate: (id: number, util: boolean) => api.patch(`/queries/${id}/rate`, { util }),
};

export const coordinatorAPI = {
    students: (params?: { programa?: string }) => api.get('/students', { params }),
    programs: () => api.get('/dashboard/programs'),
    metrics: (params?: object) => api.get('/dashboard/metrics', { params }),
    byProgram: (params?: object) => api.get('/dashboard/by-program', { params }),
    trend: (params?: object) => api.get('/dashboard/trend', { params }),
    topTopics: (params?: object) => api.get('/dashboard/top-topics', { params }),
    practiceStudents: (params?: object) => api.get('/dashboard/practice-students', { params }),
    practiceCompetencies: (params?: object) => api.get('/dashboard/practice-competencies', { params }),
    levelProgression: (params?: object) => api.get('/dashboard/level-progression', { params }),
};
