import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8080/api',
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
        axios.post(`${import.meta.env.VITE_AI_URL ?? 'http://localhost:8000'}/consultar`, data),
    sugerencias: (params: { programa: string; competencia?: string; cantidad?: number }) =>
        axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://localhost:8000'}/sugerencias`, { params }),
    exportExcel: (params: Record<string, string>) => {
        const token = localStorage.getItem('sp_token');
        return axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://localhost:8000'}/reportes/excel`, {
            params, responseType: 'blob',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
    },
    exportPDF: (params: Record<string, string>) => {
        const token = localStorage.getItem('sp_token');
        return axios.get(`${import.meta.env.VITE_AI_URL ?? 'http://localhost:8000'}/reportes/pdf`, {
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
    programs: () => api.get('/students/programs'),
    metrics: (params?: object) => api.get('/dashboard/metrics', { params }),
    byProgram: (params?: object) => api.get('/dashboard/by-program', { params }),
    trend: (params?: object) => api.get('/dashboard/trend', { params }),
    topTopics: (params?: object) => api.get('/dashboard/top-topics', { params }),
};
