import React, { useRef, useState, useEffect, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import {
    Users, MessageSquare, TrendingUp, ThumbsUp, Filter,
    BarChart2, Sun, Moon, LogOut, Brain, Loader2, CalendarDays, RotateCcw, CheckCircle2, AlertTriangle, X, FileSpreadsheet, FileText,
    PieChart, Activity, Gauge, Clock, Award, Send, MessageSquarePlus
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import api, { coordinatorAPI, aiAPI } from '../api/client';
import type { DashboardMetrics, ChartDataPoint, PracticeStudentMetric, PracticeCompetenceMetric, LevelProgressPoint } from '../types';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';

const COORD_WHITE_LOGO_SRC = '/assets/logo-blanco-coordinador.png';

const adminChatMarkdownComponents = {
    p: ({ children }: { children?: React.ReactNode }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
    ul: ({ children }: { children?: React.ReactNode }) => <ul style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ul>,
    ol: ({ children }: { children?: React.ReactNode }) => <ol style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ol>,
    li: ({ children }: { children?: React.ReactNode }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
    strong: ({ children }: { children?: React.ReactNode }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
    em: ({ children }: { children?: React.ReactNode }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
    code: ({ children }: { children?: React.ReactNode }) => (
        <code style={{ background: 'rgba(15, 23, 42, 0.08)', borderRadius: '6px', padding: '1px 6px', fontSize: '13px' }}>
            {children}
        </code>
    ),
    pre: ({ children }: { children?: React.ReactNode }) => (
        <pre style={{
            margin: '0 0 8px 0',
            overflowX: 'auto',
            background: 'rgba(15, 23, 42, 0.08)',
            borderRadius: '8px',
            padding: '10px',
            fontSize: '13px',
        }}>
            {children}
        </pre>
    ),
} as const;

type AdminChatMessage = { role: 'user' | 'assistant'; content: string };

const AnimatedNumber: React.FC<{ value: number; suffix?: string; duration?: number }> = ({ value, suffix = '', duration = 900 }) => {
    const [display, setDisplay] = useState(0);

    useEffect(() => {
        const target = Number.isFinite(value) ? value : 0;
        const start = performance.now();
        let raf = 0;

        const tick = (now: number) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplay(Math.round(target * eased));
            if (progress < 1) raf = requestAnimationFrame(tick);
        };

        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [value, duration]);

    return <>{display}{suffix}</>;
};

const KPICard: React.FC<{ icon: React.ReactNode; label: string; value: number; color?: string; suffix?: string; delay?: number }> = ({ icon, label, value, color, suffix = '', delay = 0 }) => (
    <div className="card card-hover" style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        border: '1px solid var(--border)',
        background: 'var(--grad-card)',
        boxShadow: 'var(--shadow-md)',
        animation: `dash-pop 380ms ease ${delay}ms both`,
        transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1), border-color 200ms ease',
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-3px) scale(1.015)'; e.currentTarget.style.boxShadow = 'var(--shadow-lg)'; }}
    onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
            <div style={{ color: color ?? 'var(--primary)', background: 'var(--primary-glow)', padding: '8px', borderRadius: 'var(--radius-md)' }}>{icon}</div>
            <span style={{
                fontSize: '11px',
                color: 'var(--text-hint)',
                padding: '3px 8px',
                borderRadius: 'var(--radius-full)',
                border: '1px solid var(--border)',
                background: 'var(--surface-2)',
                whiteSpace: 'nowrap',
            }}>
                Actualizado
            </span>
        </div>
        <p style={{
            fontSize: '30px',
            fontFamily: 'var(--font-heading)',
            fontWeight: 800,
            lineHeight: 1.05,
            color: color ?? 'var(--text)',
            wordBreak: 'break-word',
        }}>
            <AnimatedNumber value={value} suffix={suffix} />
        </p>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.35, overflowWrap: 'anywhere' }}>{label}</p>
    </div>
);

export const DashboardPage: React.FC = () => {
    const pageRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();
    const { coordinator, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();

    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [byProgram, setByProgram] = useState<ChartDataPoint[]>([]);
    const [trend, setTrend] = useState<ChartDataPoint[]>([]);
    const [topics, setTopics] = useState<ChartDataPoint[]>([]);
    const [practiceStudents, setPracticeStudents] = useState<PracticeStudentMetric[]>([]);
    const [practiceCompetencies, setPracticeCompetencies] = useState<PracticeCompetenceMetric[]>([]);
    const [levelProgression, setLevelProgression] = useState<LevelProgressPoint[]>([]);
    const [difficultyDist, setDifficultyDist] = useState<Array<{ competencia: string; nivel_pregunta: string; total: number; tasa_acierto: number }>>([]);
    const [englishParts, setEnglishParts] = useState<Array<{ tipo_pregunta: string; total: number; estudiantes: number; tasa_acierto: number; tiempo_promedio_seg: number }>>([]);
    const [responseTime, setResponseTime] = useState<Array<{ competencia: string; tiempo_promedio_seg: number; tiempo_acierto_seg: number; tiempo_error_seg: number; total: number }>>([]);
    const [programs, setPrograms] = useState<string[]>([]);
    const [allStudents, setAllStudents] = useState<Array<{ cedula: string; nombre: string; email: string; programa: string }>>([]);
    const [progFilter, setProgFilter] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [exportLoading, setExLoad] = useState(false);
    const [exportType, setExportType] = useState<'excel' | 'pdf' | null>(null);
    const [dataLoading, setDataLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshTick, setRefreshTick] = useState(0);
    const [aiMode, setAiMode] = useState(true);

    const [plotResetVersion, setPlotResetVersion] = useState<Record<string, number>>({});
    const [quickRange, setQuickRange] = useState<'7d' | '30d' | '90d' | ''>('');
    const [exportNotice, setExportNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
    const [chatMessages, setChatMessages] = useState<AdminChatMessage[]>([{
        role: 'assistant',
        content: 'Hola, soy tu consultor de datos. Preguntame sobre metricas, programas, estudiantes o cualquier dato del dashboard.',
    }]);
    const [chatInput, setChatInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const chatBottomRef = useRef<HTMLDivElement>(null);

    const headerParticles = useMemo(() => (
        Array.from({ length: 20 }).map((_, i) => ({
            left: 4 + Math.random() * 92,
            top: 8 + Math.random() * 76,
            size: 3 + Math.random() * 6,
            opacity: 0.18 + Math.random() * 0.24,
            duration: 3.8 + Math.random() * 2.6,
            delay: Math.random() * 1.8,
            driftX: -12 + Math.random() * 24,
            driftY: -10 + Math.random() * 20,
            glow: i % 2 === 0,
        }))
    ), []);

    useGsapPageMotion(pageRef);

    const isDark = theme === 'dark';
    const plotBg = isDark ? '#18181B' : '#FFFFFF';
    const plotFont = isDark ? '#FAFAFA' : '#0F172A';
    const plotGrid = isDark ? '#3F3F46' : '#E2E8F0';
    const interactivePlotConfig = {
        displayModeBar: true,
        responsive: true,
        scrollZoom: true,
        displaylogo: false,
    } as const;

    const resetPlotView = (plotId: string) => {
        setPlotResetVersion(prev => ({
            ...prev,
            [plotId]: (prev[plotId] ?? 0) + 1,
        }));
    };

    const getPlotKey = (plotId: string) => `${plotId}-${plotResetVersion[plotId] ?? 0}`;

    const formatInputDate = (date: Date) => {
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    };

    const applyQuickRange = (days: 7 | 30 | 90) => {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - (days - 1));
        setDateFrom(formatInputDate(start));
        setDateTo(formatInputDate(end));
        setQuickRange(`${days}d` as '7d' | '30d' | '90d');
    };

    const clearFilters = () => {
        setProgFilter('');
        setDateFrom('');
        setDateTo('');
        setQuickRange('');
    };

    const hasActiveFilters = Boolean(progFilter || dateFrom || dateTo);

    useEffect(() => {
        if (!exportNotice) return;
        const timer = window.setTimeout(() => setExportNotice(null), 2600);
        return () => window.clearTimeout(timer);
    }, [exportNotice]);

    const loadData = async () => {
        setDataLoading(true);
        setError(null);
        try {
            const params = { programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo };
            const [m, bp, tr, tp, ps, pc, lp, pr, dd, ep, rt] = await Promise.all([
                coordinatorAPI.metrics(params),
                coordinatorAPI.byProgram(params),
                coordinatorAPI.trend(params),
                coordinatorAPI.topTopics(params),
                coordinatorAPI.practiceStudents(params),
                coordinatorAPI.practiceCompetencies(params),
                coordinatorAPI.levelProgression(params),
                coordinatorAPI.programs(),
                api.get('/dashboard/difficulty-distribution', { params }),
                api.get('/dashboard/english-parts', { params }),
                api.get('/dashboard/response-time', { params }),
            ]);
            setMetrics(m.data);
            setByProgram(bp.data);
            setTrend(tr.data);
            setTopics(tp.data);
            setPracticeStudents(ps.data);
            setPracticeCompetencies(pc.data);
            setLevelProgression(lp.data);
            setPrograms(pr.data);
            setDifficultyDist(dd.data ?? []);
            setEnglishParts(ep.data ?? []);
            setResponseTime(rt.data ?? []);
            try { const st = await coordinatorAPI.students(); setAllStudents(st.data?.data ?? st.data ?? []); } catch {}
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message;
            setError(msg || 'Error cargando datos del dashboard. Verifica tu sesión.');
        } finally {
            setDataLoading(false);
            setRefreshTick(t => t + 1);
        }
    };

    useEffect(() => { loadData(); }, [progFilter, dateFrom, dateTo]);

    useEffect(() => {
        chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages, chatLoading]);

    const clearAdminChat = () => {
        setChatMessages([{
            role: 'assistant',
            content: 'Hola, soy tu consultor de datos. Preguntame sobre metricas, programas, estudiantes o cualquier dato del dashboard.',
        }]);
    };

    const handleAdminChatSend = async () => {
        if (!chatInput.trim() || chatLoading) return;
        const pregunta = chatInput.trim();
        setChatInput('');
        setChatLoading(true);

        const userMsg: AdminChatMessage = { role: 'user', content: pregunta };
        const updatedHistory = [...chatMessages, userMsg];
        setChatMessages(updatedHistory);

        try {
            const res = await aiAPI.adminChat({
                pregunta,
                dashboard_data: buildAnalyticsContext(),
                historial: updatedHistory.map(m => ({ role: m.role, content: m.content })),
            });
            const respuesta = res?.data?.respuesta?.trim() || 'No se pudo generar respuesta en este momento.';
            setChatMessages(prev => [...prev, { role: 'assistant', content: respuesta }]);
        } catch {
            setChatMessages(prev => [...prev, { role: 'assistant', content: 'Error al consultar el chat. Intenta de nuevo.' }]);
        } finally {
            setChatLoading(false);
        }
    };

    const handleChatKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleAdminChatSend();
        }
    };

    const downloadBlob = (blob: Blob, filename: string) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
    };

    const exportExcel = async () => {
        setExportType('excel');
        setExLoad(true);
        try {
            const res = await aiAPI.exportExcel({ programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo });
            downloadBlob(res.data, `reporte_saberpro_${Date.now()}.xlsx`);
            setExportNotice({ type: 'success', message: 'Excel generado correctamente.' });
        } catch {
            setExportNotice({ type: 'error', message: 'Error generando el Excel. Intenta de nuevo.' });
        } finally {
            setExLoad(false);
            setExportType(null);
        }
    };

    const exportPDF = async () => {
        setExportType('pdf');
        setExLoad(true);
        try {
            const res = await aiAPI.exportPDF({ programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo });
            downloadBlob(res.data, `reporte_saberpro_${Date.now()}.pdf`);
            setExportNotice({ type: 'success', message: 'PDF generado correctamente.' });
        } catch {
            setExportNotice({ type: 'error', message: 'Error generando el PDF. Intenta de nuevo.' });
        } finally {
            setExLoad(false);
            setExportType(null);
        }
    };

    const parsePositiveRate = (value: unknown): number => {
        if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
        if (typeof value === 'string') {
            const normalized = value.replace('%', '').replace(',', '.').trim();
            const parsed = Number(normalized);
            return Number.isFinite(parsed) ? parsed : 0;
        }
        return 0;
    };

    const metricValues = {
        totalConsultas: Number(metrics?.total_consultas ?? 0),
        estudiantesUnicos: Number(metrics?.estudiantes_unicos ?? 0),
        consultasHoy: Number(metrics?.consultas_hoy ?? 0),
        promedioPositivas: parsePositiveRate(metrics?.promedio_positivas),
        totalEstudiantes: Number(metrics?.total_estudiantes ?? 0),
    };

    const adoptionRate = useMemo(() => {
        if (metricValues.totalEstudiantes <= 0) return 0;
        return (metricValues.estudiantesUnicos / metricValues.totalEstudiantes) * 100;
    }, [metricValues.estudiantesUnicos, metricValues.totalEstudiantes]);

    const topPracticeStudentsChart = useMemo(() => {
        const sorted = [...practiceStudents]
            .filter(s => {
                const name = String(s.estudiante || '').toLowerCase();
                return !name.includes('coordinador') && !name.includes('coordinator');
            })
            .sort((a, b) => {
                const scoreDiff = Number(b.puntaje_promedio ?? 0) - Number(a.puntaje_promedio ?? 0);
                if (scoreDiff !== 0) return scoreDiff;
                return Number(b.intentos ?? 0) - Number(a.intentos ?? 0);
            })
            .slice(0, 12);

        return {
            labels: sorted.map(s => String(s.estudiante || 'N/A')),
            values: sorted.map(s => Number(s.puntaje_promedio ?? 0)),
            programs: sorted.map(s => String(s.programa || 'N/A')),
        };
    }, [practiceStudents]);

    const practiceComparisonChart = useMemo(() => {
        if (!practiceCompetencies.length) return { competencias: [] as string[], traces: [] as object[] };

        const normalizeKey = (value: string) => value
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .replace(/\s+/g, ' ')
            .trim();

        const aggregate = new Map<string, { programa: string; competencia: string; intentos: number; aciertos: number }>();
        for (const row of practiceCompetencies) {
            const programa = String(row.programa || '').trim();
            const competencia = String(row.competencia || '').trim();
            if (!programa || !competencia) continue;

            const key = `${normalizeKey(programa)}__${normalizeKey(competencia)}`;
            const existing = aggregate.get(key);
            if (!existing) {
                aggregate.set(key, {
                    programa,
                    competencia,
                    intentos: Number(row.intentos ?? 0),
                    aciertos: Number(row.aciertos ?? 0),
                });
            } else {
                existing.intentos += Number(row.intentos ?? 0);
                existing.aciertos += Number(row.aciertos ?? 0);
            }
        }

        const aggregatedRows = Array.from(aggregate.values());
        const competencias = Array.from(new Set(aggregatedRows.map(r => r.competencia))).sort((a, b) => a.localeCompare(b));
        const programas = Array.from(new Set(aggregatedRows.map(r => r.programa))).sort((a, b) => a.localeCompare(b));

        const valueMap = new Map<string, number>();
        const statsMap = new Map<string, { intentos: number; aciertos: number }>();
        for (const row of aggregatedRows) {
            const key = `${normalizeKey(row.programa)}__${normalizeKey(row.competencia)}`;
            const promedio = row.intentos > 0 ? (row.aciertos / row.intentos) * 100 : 0;
            valueMap.set(key, Number(promedio.toFixed(1)));
            statsMap.set(key, { intentos: row.intentos, aciertos: row.aciertos });
        }

        const traces = programas.flatMap((programa, index) => {
            const color = [
                '#4a6f65', '#587c73', '#3f627b', '#6d7f53',
                '#8f7b54', '#586a87', '#507b9a', '#6f8b84',
            ][index % 8];

            const yValues = competencias.map(c => valueMap.get(`${normalizeKey(programa)}__${normalizeKey(c)}`) ?? 0);
            const customdata = competencias.map(c => {
                const stats = statsMap.get(`${normalizeKey(programa)}__${normalizeKey(c)}`);
                return [stats?.intentos ?? 0, stats?.aciertos ?? 0];
            });

            const barTrace = {
                type: 'bar',
                name: programa,
                x: competencias,
                y: yValues,
                customdata,
                hovertemplate: '<b>%{x}</b><br>Programa: ' + programa + '<br>Promedio: %{y:.1f}%<br>Intentos: %{customdata[0]}<br>Aciertos: %{customdata[1]}<extra></extra>',
                marker: {
                    opacity: 0.88,
                    color,
                },
            };

            const zeroMarkers = {
                type: 'scatter',
                mode: 'markers',
                name: `${programa} (0%)`,
                showlegend: false,
                x: competencias,
                // Dibujar un poco arriba del eje para hacer visible participación con 0%.
                y: yValues.map(v => (v === 0 ? 1.2 : null)),
                customdata,
                hovertemplate: '<b>%{x}</b><br>Programa: ' + programa + '<br>Promedio: 0.0%<br>Intentos: %{customdata[0]}<br>Aciertos: %{customdata[1]}<extra></extra>',
                marker: {
                    size: 8,
                    color,
                    symbol: 'circle-open',
                    line: { width: 1.6, color },
                },
            };

            return [barTrace, zeroMarkers];
        });

        return { competencias, traces };
    }, [practiceCompetencies]);

    const levelProgressCharts = useMemo(() => {
        if (!levelProgression.length) {
            return {
                englishCards: [] as Array<{ competencia: string; trace: object; points: number }>,
                generalCards: [] as Array<{ competencia: string; trace: object; points: number }>,
            };
        }

        const formatDateLabel = (isoDate: string) => {
            const d = new Date(`${String(isoDate).slice(0, 10)}T12:00:00`);
            if (Number.isNaN(d.getTime())) return String(isoDate);
            return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
        };

        const normalize = (value: string) => value
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();

        const isEnglishCompetency = (competencia: string) => {
            const c = normalize(competencia);
            return c.includes('ingles') || c.includes('english');
        };

        const generalPalette = ['#3f7f66', '#4f6d9a', '#8a6b3f', '#6e5b9a', '#2f8f85', '#7a4f66', '#5d7f44', '#3f6f7f'];
        const englishPalette = ['#2b8a78', '#1f7aa6', '#2f6db3', '#4b79c9', '#2f8c9d', '#3d7fa8'];

        const getStableColor = (key: string, palette: string[]) => {
            let hash = 0;
            for (let i = 0; i < key.length; i += 1) {
                hash = ((hash << 5) - hash) + key.charCodeAt(i);
                hash |= 0;
            }
            return palette[Math.abs(hash) % palette.length];
        };

        const buildCard = (comp: string, rows: LevelProgressPoint[], palette: string[]) => {
            const sortedRows = [...rows]
                .sort((a, b) => String(a.fecha).localeCompare(String(b.fecha)));

            const color = getStableColor(comp, palette);

            return {
                competencia: comp,
                points: sortedRows.length,
                trace: {
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: comp,
                    x: sortedRows.map(r => formatDateLabel(String(r.fecha))),
                    y: sortedRows.map(r => Number(r.nivel_promedio ?? 0)),
                    text: sortedRows.map(r => `Intentos: ${r.intentos} | Acierto: ${Number(r.tasa_acierto ?? 0).toFixed(1)}%`),
                    hovertemplate: '%{x}<br>Nivel promedio: %{y:.2f}<br>%{text}<extra></extra>',
                    line: { width: 2.6, color },
                    marker: { size: 7, color },
                },
            };
        };

        const allCompetencies = Array.from(new Set(levelProgression.map(r => String(r.competencia || '').trim()).filter(Boolean)));

        const englishCards = allCompetencies
            .filter(isEnglishCompetency)
            .map((comp) => {
                const rows = levelProgression.filter(r => String(r.competencia || '').trim() === comp);
                return buildCard(comp, rows, englishPalette);
            })
            .sort((a, b) => a.competencia.localeCompare(b.competencia));

        const generalCards = allCompetencies
            .filter(c => !isEnglishCompetency(c))
            .map((comp) => {
                const rows = levelProgression.filter(r => String(r.competencia || '').trim() === comp);
                return buildCard(comp, rows, generalPalette);
            })
            .sort((a, b) => a.competencia.localeCompare(b.competencia));

        return {
            englishCards,
            generalCards,
        };
    }, [levelProgression]);

    const difficultyDistributionChart = useMemo(() => {
        if (!difficultyDist.length) return { competencias: [] as string[], traces: [] as object[] };

        const competencias = Array.from(new Set(difficultyDist.map(d => d.competencia))).sort((a, b) => a.localeCompare(b));
        const niveles = ['basico', 'intermedio', 'avanzado'] as const;
        const colors: Record<string, string> = { basico: '#22c55e', intermedio: '#f97316', avanzado: '#ef4444' };

        const traces = niveles.map(nivel => ({
            type: 'bar',
            name: nivel.charAt(0).toUpperCase() + nivel.slice(1),
            x: competencias,
            y: competencias.map(comp => {
                const row = difficultyDist.find(d => d.competencia === comp && d.nivel_pregunta === nivel);
                return row ? row.total : 0;
            }),
            marker: { color: colors[nivel], opacity: 0.85 },
            hovertemplate: '<b>%{x}</b><br>' + nivel + ': %{y}<extra></extra>',
        }));

        return { competencias, traces };
    }, [difficultyDist]);

    const englishPartsChart = useMemo(() => {
        if (!englishParts.length) return { labels: [] as string[], tasaAcierto: [] as number[], totals: [] as number[] };

        const sorted = [...englishParts].sort((a, b) => a.tipo_pregunta.localeCompare(b.tipo_pregunta));

        return {
            labels: sorted.map(e => e.tipo_pregunta),
            tasaAcierto: sorted.map(e => Number(e.tasa_acierto ?? 0)),
            totals: sorted.map(e => Number(e.total ?? 0)),
        };
    }, [englishParts]);

    const responseTimeChart = useMemo(() => {
        if (!responseTime.length) return { competencias: [] as string[], traces: [] as object[] };

        const competencias = responseTime.map(d => d.competencia);

        const correctoTrace = {
            type: 'bar',
            name: 'Correcto',
            x: competencias,
            y: responseTime.map(d => Number(d.tiempo_acierto_seg ?? 0)),
            marker: { color: '#22c55e', opacity: 0.85 },
            hovertemplate: '<b>%{x}</b><br>Correcto: %{y:.1f}s<extra></extra>',
        };

        const incorrectoTrace = {
            type: 'bar',
            name: 'Incorrecto',
            x: competencias,
            y: responseTime.map(d => Number(d.tiempo_error_seg ?? 0)),
            marker: { color: '#ef4444', opacity: 0.85 },
            hovertemplate: '<b>%{x}</b><br>Incorrecto: %{y:.1f}s<extra></extra>',
        };

        return { competencias, traces: [correctoTrace, incorrectoTrace] };
    }, [responseTime]);

    const buildAnalyticsContext = () => {
        return {
            _contexto: {
                fuente: 'dashboard_coordinador',
                incluir_todo_dataset: true,
                generado_en: new Date().toISOString(),
            },
            filtros: {
                programa: progFilter || 'Todos los programas',
                fecha_inicio: dateFrom || 'sin filtro',
                fecha_fin: dateTo || 'sin filtro',
            },
            metricas: metricValues,
            programas: byProgram,
            tendencia: trend,
            temas_top: topics,
            todos_estudiantes: allStudents.filter(s => s.cedula !== '123456789'),
            resultados_practicas: practiceStudents,
            promedio_competencias: practiceCompetencies,
            evolucion_nivel: levelProgression,
            distribucion_dificultad: difficultyDist,
            desglose_ingles: englishParts,
            tiempo_respuesta: responseTime,
            cobertura_dataset: {
                total_programas: byProgram.length,
                total_puntos_tendencia: trend.length,
                total_temas: topics.length,
                total_registros_practica: practiceStudents.length,
                total_competencias_practica: practiceCompetencies.length,
                total_puntos_nivel: levelProgression.length,
                total_dificultades: difficultyDist.length,
                total_partes_ingles: englishParts.length,
                total_tiempos: responseTime.length,
            },
        };
    };



    return (
        <div ref={pageRef} style={{
            minHeight: '100dvh',
            background: 'var(--grad-hero)',
            backgroundSize: '150% 150%',
            animation: 'dash-bg-shift 16s ease-in-out infinite',
        }}>
            <header style={{
                background: 'linear-gradient(180deg, #2a3e4d 0%, #1f313e 100%)',
                backdropFilter: 'blur(10px)',
                borderBottom: '1px solid rgba(255,255,255,0.12)',
                padding: 'var(--space-md) var(--space-xl)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 'var(--space-md)',
                position: 'sticky',
                top: 0,
                zIndex: 20,
                overflow: 'hidden',
            }}>
                <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                    {headerParticles.map((p, i) => (
                        <span
                            key={`dashboard-header-particle-${i}`}
                            style={{
                                position: 'absolute',
                                left: `${p.left}%`,
                                top: `${p.top}%`,
                                width: `${p.size}px`,
                                height: `${p.size}px`,
                                borderRadius: '999px',
                                opacity: p.opacity,
                                background: p.glow ? 'rgba(165, 217, 248, 0.72)' : 'rgba(166, 216, 193, 0.68)',
                                boxShadow: p.glow ? '0 0 9px rgba(138, 201, 241, 0.34)' : '0 0 9px rgba(143, 221, 185, 0.32)',
                                animation: `dashboard-header-particle-float ${p.duration}s ease-in-out ${p.delay}s infinite alternate`,
                                ['--driftX' as any]: `${p.driftX}px`,
                                ['--driftY' as any]: `${p.driftY}px`,
                            }}
                        />
                    ))}
                </div>

                <div data-motion="headline" style={{ display: 'flex', alignItems: 'center', gap: '12px', position: 'relative', zIndex: 2 }}>
                    <img
                        src={COORD_WHITE_LOGO_SRC}
                        alt="Logo institucional blanco"
                        style={{ width: '74px', height: '74px', objectFit: 'contain', opacity: 0.96 }}
                    />
                    <div>
                        <h1 style={{ fontSize: '20px', fontFamily: 'var(--font-heading)', color: '#f2f8fc' }}>Dashboard — Ascenso Pro</h1>
                        <p style={{ fontSize: '13px', color: 'rgba(230,240,247,0.84)' }}>{coordinator?.nombre} · UCundinamarca Fusagasugá</p>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center', position: 'relative', zIndex: 2 }}>
                    <button
                        className="btn btn-secondary"
                        onClick={() => setAiMode(v => !v)}
                        style={{
                            gap: '6px',
                            animation: 'dash-fade-in 260ms ease 20ms both',
                            background: aiMode ? 'rgba(143, 208, 178, 0.2)' : 'rgba(255,255,255,0.1)',
                            color: '#f2f8fc',
                            border: aiMode ? '1px solid rgba(143, 208, 178, 0.45)' : '1px solid rgba(255,255,255,0.24)',
                        }}
                    >
                        <Brain size={14} /> Modo IA {aiMode ? 'ON' : 'OFF'}
                    </button>
                    <button className="btn btn-secondary" onClick={exportExcel} disabled={exportLoading} style={{ gap: '6px', animation: 'dash-fade-in 260ms ease 40ms both', background: exportType === 'excel' ? 'rgba(130, 204, 168, 0.24)' : 'rgba(255,255,255,0.12)', color: '#f2f8fc', border: exportType === 'excel' ? '1px solid rgba(130, 204, 168, 0.65)' : '1px solid rgba(255,255,255,0.24)' }}>
                        {exportType === 'excel' ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <FileSpreadsheet size={14} />} {exportType === 'excel' ? 'Generando Excel...' : 'Excel'}
                    </button>
                    <button className="btn btn-secondary" onClick={exportPDF} disabled={exportLoading} style={{ gap: '6px', animation: 'dash-fade-in 260ms ease 85ms both', background: exportType === 'pdf' ? 'rgba(130, 179, 232, 0.24)' : 'rgba(255,255,255,0.12)', color: '#f2f8fc', border: exportType === 'pdf' ? '1px solid rgba(130, 179, 232, 0.65)' : '1px solid rgba(255,255,255,0.24)' }}>
                        {exportType === 'pdf' ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <FileText size={14} />} {exportType === 'pdf' ? 'Generando PDF...' : 'PDF'}
                    </button>
                    <button className="btn-icon" onClick={toggleTheme} aria-label="Cambiar tema" style={{ animation: 'dash-fade-in 260ms ease 130ms both', color: '#eaf3f9', borderColor: 'rgba(255,255,255,0.24)', background: 'rgba(255,255,255,0.08)' }}>{isDark ? <Sun size={15} /> : <Moon size={15} />}</button>
                    <button className="btn-icon" onClick={() => { logout(); navigate('/coordinador'); }} aria-label="Cerrar sesión" style={{ color: '#ffb7b7', animation: 'dash-fade-in 260ms ease 175ms both', borderColor: 'rgba(255,255,255,0.24)', background: 'rgba(255,255,255,0.08)' }}><LogOut size={15} /></button>
                </div>
                {(dataLoading || exportLoading) && (
                    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '2px', overflow: 'hidden', zIndex: 3 }}>
                        <div style={{
                            height: '100%',
                            width: '35%',
                            background: exportLoading
                                ? 'linear-gradient(90deg, transparent 0%, #9fc5e6 42%, #8fd0b1 100%)'
                                : 'linear-gradient(90deg, transparent 0%, var(--primary) 40%, var(--accent) 100%)',
                            animation: 'dash-loader 1.05s ease-in-out infinite',
                        }} />
                    </div>
                )}
            </header>

            <div style={{ padding: '20px', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
                {exportNotice && (
                    <div style={{
                        marginBottom: 'var(--space-md)',
                        borderRadius: '12px',
                        border: exportNotice.type === 'success' ? '1px solid rgba(78, 176, 130, 0.45)' : '1px solid rgba(226, 111, 103, 0.45)',
                        background: exportNotice.type === 'success'
                            ? 'linear-gradient(120deg, rgba(219, 248, 231, 0.85) 0%, rgba(236, 253, 245, 0.92) 100%)'
                            : 'linear-gradient(120deg, rgba(254, 226, 226, 0.86) 0%, rgba(255, 241, 242, 0.92) 100%)',
                        color: exportNotice.type === 'success' ? '#1e6c4e' : '#a13a36',
                        boxShadow: '0 10px 24px rgba(0,0,0,0.08)',
                        padding: '10px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '10px',
                        animation: 'dash-slide-up 240ms ease both',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 700 }}>
                            {exportNotice.type === 'success' ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}
                            {exportNotice.message}
                        </div>
                        <button
                            type="button"
                            aria-label="Cerrar notificación"
                            onClick={() => setExportNotice(null)}
                            style={{
                                border: 'none',
                                background: 'transparent',
                                color: 'inherit',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: 0,
                            }}
                        >
                            <X size={14} />
                        </button>
                    </div>
                )}

                {error && (
                    <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', marginBottom: 'var(--space-lg)', color: '#DC2626', fontSize: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>⚠️ {error}</span>
                        <button onClick={loadData} style={{ background: '#DC2626', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '4px 12px', cursor: 'pointer', fontSize: '12px' }}>Reintentar</button>
                    </div>
                )}
                {dataLoading && !metrics && (
                    <div style={{ textAlign: 'center', padding: 'var(--space-xl)', color: 'var(--text-muted)' }}>
                        Cargando datos del dashboard…
                    </div>
                )}

                {aiMode && (
                    <>
                    {/* ── Admin Chat Panel ── */}
                    <section data-motion="panel" className="animate-fade-up" style={{
                        marginBottom: 'var(--space-lg)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--border)',
                        boxShadow: 'var(--shadow-md)',
                        background: 'var(--grad-card)',
                        padding: '16px',
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '12px', flexWrap: 'wrap' }}>
                            <h2 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <MessageSquare size={16} color="var(--accent)" /> Consultor de Datos IA
                            </h2>
                            <button
                                className="btn btn-secondary"
                                onClick={clearAdminChat}
                                disabled={chatLoading}
                                style={{ gap: '6px', fontSize: '12px' }}
                            >
                                <MessageSquarePlus size={14} /> Nueva conversacion
                            </button>
                        </div>

                        <div style={{
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            background: 'var(--surface)',
                            display: 'flex',
                            flexDirection: 'column',
                            height: '380px',
                        }}>
                            <div style={{
                                flex: 1,
                                overflowY: 'auto',
                                padding: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '10px',
                            }}>
                                {chatMessages.map((msg, idx) => {
                                    const isUser = msg.role === 'user';
                                    return (
                                        <div key={idx} style={{
                                            display: 'flex',
                                            flexDirection: isUser ? 'row-reverse' : 'row',
                                            gap: '8px',
                                            alignItems: 'flex-end',
                                        }}>
                                            {!isUser && (
                                                <div style={{
                                                    width: '28px',
                                                    height: '28px',
                                                    borderRadius: 'var(--radius-full)',
                                                    background: 'linear-gradient(120deg, #2f4c61, #3e6a5a)',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    flexShrink: 0,
                                                }}>
                                                    <Brain size={13} color="#fff" />
                                                </div>
                                            )}
                                            <div style={{ maxWidth: '78%' }}>
                                                <div style={{
                                                    padding: '10px 14px',
                                                    borderRadius: isUser
                                                        ? 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)'
                                                        : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
                                                    background: isUser ? 'linear-gradient(120deg, #2f4c61, #3e6a5a)' : 'rgba(30,40,55,0.92)',
                                                    color: isUser ? '#fff' : '#e0e8ef',
                                                    border: isUser ? 'none' : '1px solid rgba(255,255,255,0.08)',
                                                    fontSize: '13px',
                                                    lineHeight: '1.55',
                                                    wordBreak: 'break-word',
                                                }}>
                                                    {isUser ? (
                                                        msg.content
                                                    ) : (
                                                        <ReactMarkdown
                                                            remarkPlugins={[remarkGfm, remarkMath]}
                                                            rehypePlugins={[rehypeKatex]}
                                                            components={adminChatMarkdownComponents}
                                                        >
                                                            {msg.content || ''}
                                                        </ReactMarkdown>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                                {chatLoading && (
                                    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
                                        <div style={{
                                            width: '28px',
                                            height: '28px',
                                            borderRadius: 'var(--radius-full)',
                                            background: 'linear-gradient(120deg, #2f4c61, #3e6a5a)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            flexShrink: 0,
                                        }}>
                                            <Brain size={13} color="#fff" />
                                        </div>
                                        <div style={{
                                            background: 'rgba(30,40,55,0.92)',
                                            border: '1px solid rgba(255,255,255,0.08)',
                                            borderRadius: 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
                                            padding: '10px 14px',
                                            display: 'flex',
                                            gap: '5px',
                                            alignItems: 'center',
                                        }}>
                                            {[0, 1, 2].map(i => <span key={i} className="typing-dot" style={{ animationDelay: `${i * 0.16}s` }} />)}
                                        </div>
                                    </div>
                                )}
                                <div ref={chatBottomRef} />
                            </div>

                            <div style={{
                                borderTop: '1px solid var(--border)',
                                padding: '8px 10px',
                                display: 'flex',
                                gap: '8px',
                                alignItems: 'flex-end',
                            }}>
                                <textarea
                                    className="input"
                                    value={chatInput}
                                    onChange={e => setChatInput(e.target.value)}
                                    onKeyDown={handleChatKeyDown}
                                    placeholder="Pregunta sobre metricas, programas, estudiantes..."
                                    disabled={chatLoading}
                                    style={{
                                        flex: 1,
                                        minHeight: '38px',
                                        maxHeight: '100px',
                                        resize: 'none',
                                        fontSize: '13px',
                                        lineHeight: '1.45',
                                    }}
                                    rows={1}
                                />
                                <button
                                    className="btn"
                                    onClick={handleAdminChatSend}
                                    disabled={chatLoading || !chatInput.trim()}
                                    style={{
                                        height: '38px',
                                        width: '38px',
                                        padding: 0,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: 'linear-gradient(120deg, #2f4c61, #3e6a5a)',
                                        color: '#fff',
                                        border: '1px solid rgba(255,255,255,0.2)',
                                        borderRadius: 'var(--radius-md)',
                                        opacity: chatLoading || !chatInput.trim() ? 0.5 : 1,
                                        cursor: chatLoading || !chatInput.trim() ? 'not-allowed' : 'pointer',
                                    }}
                                >
                                    {chatLoading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={15} />}
                                </button>
                            </div>
                        </div>
                    </section>

                    </>
                )}

                <section data-motion="panel" key={`filters-${refreshTick}`} className="animate-fade-up dashboard-filters-panel" style={{
                    marginBottom: 'var(--space-lg)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-md)',
                    background: isDark
                        ? 'linear-gradient(140deg, rgba(24,24,27,0.92) 0%, rgba(32,40,52,0.88) 100%)'
                        : 'linear-gradient(140deg, rgba(255,255,255,0.98) 0%, rgba(241,248,255,0.95) 100%)',
                    padding: '16px',
                    animation: 'dash-slide-up 280ms ease both',
                    position: 'relative',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        position: 'absolute',
                        right: '-30px',
                        top: '-30px',
                        width: '120px',
                        height: '120px',
                        borderRadius: '999px',
                        background: isDark
                            ? 'radial-gradient(circle, rgba(80,140,175,0.2) 0%, rgba(80,140,175,0) 70%)'
                            : 'radial-gradient(circle, rgba(113,172,214,0.2) 0%, rgba(113,172,214,0) 72%)',
                        animation: 'dash-soft-pulse 3.4s ease-in-out infinite',
                        pointerEvents: 'none',
                    }} />
                    <div style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-md)', marginBottom: '10px', flexWrap: 'wrap', position: 'relative', zIndex: 1
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <span style={{
                                width: '32px',
                                height: '32px',
                                borderRadius: '999px',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                background: isDark ? 'rgba(67, 133, 176, 0.22)' : 'rgba(67, 133, 176, 0.14)',
                                border: '1px solid rgba(95, 150, 184, 0.35)',
                            }}>
                                <Filter size={15} color={isDark ? '#9ed1f0' : '#3f7ea5'} />
                            </span>
                            <div>
                                <h2 style={{ margin: 0, fontSize: '15px', letterSpacing: '0.02em', color: 'var(--text)' }}>Filtros de analitica</h2>
                                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>Refina programa y rango temporal para una lectura precisa.</p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                            <span className="badge badge-primary" style={{ fontSize: '11px', animation: 'dash-soft-pulse 2.4s ease-in-out infinite' }}>Vista homogénea</span>
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={clearFilters}
                                disabled={!hasActiveFilters}
                                style={{ padding: '5px 10px', fontSize: '11px', gap: '6px' }}
                            >
                                <RotateCcw size={12} /> Limpiar
                            </button>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px', position: 'relative', zIndex: 1 }}>
                        {([
                            { id: '7d', label: 'Ultimos 7 dias', days: 7 },
                            { id: '30d', label: 'Ultimos 30 dias', days: 30 },
                            { id: '90d', label: 'Ultimos 90 dias', days: 90 },
                        ] as const).map(chip => (
                            <button
                                key={chip.id}
                                type="button"
                                onClick={() => applyQuickRange(chip.days)}
                                className="dashboard-filter-chip"
                                data-active={quickRange === chip.id ? 'true' : 'false'}
                                style={{
                                    borderRadius: '999px',
                                    border: quickRange === chip.id ? '1px solid rgba(72,130,168,0.55)' : '1px solid var(--border)',
                                    background: quickRange === chip.id
                                        ? (isDark ? 'rgba(72,130,168,0.30)' : 'rgba(72,130,168,0.16)')
                                        : 'var(--surface)',
                                    color: quickRange === chip.id ? (isDark ? '#c9e7fb' : '#2e5f80') : 'var(--text-muted)',
                                    fontWeight: 700,
                                    fontSize: '11px',
                                    padding: '6px 11px',
                                    cursor: 'pointer',
                                    transition: 'var(--t-fast)',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                }}
                            >
                                <CalendarDays size={12} /> {chip.label}
                            </button>
                        ))}
                    </div>

                    <div style={{ display: 'grid', gap: 'var(--space-md)', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', alignItems: 'flex-end', position: 'relative', zIndex: 1 }}>
                        <div className="dashboard-filter-field" style={{ animationDelay: '0ms' }}>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>Programa</label>
                            <select
                                className="input dashboard-filter-input"
                                value={progFilter}
                                onChange={e => setProgFilter(e.target.value)}
                                style={{ boxShadow: 'inset 0 0 0 1px transparent' }}
                            >
                                <option value="">Todos los programas</option>
                                {programs.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                        </div>
                        <div className="dashboard-filter-field" style={{ animationDelay: '70ms' }}>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>Desde</label>
                            <input
                                className="input dashboard-filter-input"
                                type="date"
                                value={dateFrom}
                                onChange={e => {
                                    setDateFrom(e.target.value);
                                    setQuickRange('');
                                }}
                            />
                        </div>
                        <div className="dashboard-filter-field" style={{ animationDelay: '140ms' }}>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '5px' }}>Hasta</label>
                            <input
                                className="input dashboard-filter-input"
                                type="date"
                                value={dateTo}
                                onChange={e => {
                                    setDateTo(e.target.value);
                                    setQuickRange('');
                                }}
                            />
                        </div>
                    </div>

                    <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', flexWrap: 'wrap', position: 'relative', zIndex: 1 }}>
                        <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-hint)' }}>
                            Los cambios se aplican automáticamente y actualizan todas las gráficas.
                        </p>
                        <span style={{
                            fontSize: '11px',
                            color: hasActiveFilters ? 'var(--accent)' : 'var(--text-hint)',
                            fontWeight: 700,
                            transition: 'var(--t-fast)',
                        }}>
                            {hasActiveFilters ? 'Filtros activos' : 'Sin filtros activos'}
                        </span>
                    </div>

                    {dataLoading && (
                        <div style={{
                            position: 'absolute',
                            inset: 0,
                            background: 'linear-gradient(100deg, transparent 0%, color-mix(in srgb, var(--surface) 52%, transparent) 45%, transparent 100%)',
                            animation: 'dash-shimmer 1.15s linear infinite',
                            pointerEvents: 'none',
                            zIndex: 0,
                        }} />
                    )}
                </section>

                <div key={`kpis-${refreshTick}`} style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                    gap: 'var(--space-md)',
                    marginBottom: 'var(--space-lg)',
                }}>
                    <div data-motion="card"><KPICard icon={<MessageSquare size={18} />} label="Total de consultas realizadas" value={metricValues.totalConsultas} delay={0} /></div>
                    <div data-motion="card"><KPICard icon={<Users size={18} />} label="Creadores de oportunidades unicos activos" value={metricValues.estudiantesUnicos} color="var(--accent)" delay={60} /></div>
                    <div data-motion="card"><KPICard icon={<TrendingUp size={18} />} label="Consultas registradas hoy" value={metricValues.consultasHoy} color="var(--warning)" delay={120} /></div>
                    <div data-motion="card"><KPICard icon={<ThumbsUp size={18} />} label="Calificaciones positivas" value={metricValues.promedioPositivas} color="var(--primary)" suffix="%" delay={180} /></div>
                    <div data-motion="card"><KPICard icon={<Users size={18} />} label="Total de creadores de oportunidades" value={metricValues.totalEstudiantes} delay={240} /></div>
                </div>

                <div key={`charts-${refreshTick}`} className="dash-chart-grid" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <Gauge size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Cobertura de Adopcion</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Porcentaje de creadores que han interactuado con el asistente.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('adoption')}>Reset vista</button>
                        </div>
                        <Plot
                            key={getPlotKey('adoption')}
                            data={[{
                                type: 'indicator',
                                mode: 'gauge+number',
                                value: Number(adoptionRate.toFixed(1)),
                                number: { suffix: '%', font: { size: 34, color: plotFont } },
                                gauge: {
                                    axis: { range: [0, 100], tickcolor: plotFont },
                                    bar: { color: isDark ? '#8ec5a8' : '#3f7f66' },
                                    bgcolor: isDark ? '#2A2A30' : '#F8FAFC',
                                    bordercolor: isDark ? '#3F3F46' : '#E2E8F0',
                                    steps: [
                                        { range: [0, 40], color: isDark ? '#3d2a2a' : '#fee2e2' },
                                        { range: [40, 70], color: isDark ? '#3b3526' : '#fef3c7' },
                                        { range: [70, 100], color: isDark ? '#1f3a31' : '#dcfce7' },
                                    ],
                                },
                            }]}
                            layout={{
                                paper_bgcolor: plotBg,
                                font: { color: plotFont, size: 12 },
                                margin: { t: 10, b: 20, l: 20, r: 20 },
                                height: 300,
                            }}
                            config={interactivePlotConfig}
                            style={{ width: '100%' }}
                        />
                        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                            {metricValues.estudiantesUnicos} de {metricValues.totalEstudiantes} creadores de oportunidades han usado el asistente con los filtros actuales.
                        </p>
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <Award size={17} color="var(--accent)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Ranking de Creadores de Oportunidades (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Top de creadores por puntaje promedio en practicas.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('ranking')}>Reset vista</button>
                        </div>
                        {topPracticeStudentsChart.labels.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Aun no hay datos de practica para construir el ranking.
                            </p>
                        ) : (
                            <Plot
                                key={getPlotKey('ranking')}
                                data={[{
                                    type: 'bar',
                                    orientation: 'h',
                                    y: topPracticeStudentsChart.labels,
                                    x: topPracticeStudentsChart.values,
                                    text: topPracticeStudentsChart.programs,
                                    hovertemplate: '<b>%{y}</b><br>Programa: %{text}<br>Puntaje: %{x:.1f}%<extra></extra>',
                                    marker: {
                                        color: isDark ? '#a78bfa' : '#7c3aed',
                                        opacity: 0.9,
                                    },
                                }]}
                                layout={{
                                    paper_bgcolor: plotBg,
                                    plot_bgcolor: plotBg,
                                    font: { color: plotFont, size: 12 },
                                    margin: { t: 10, b: 35, l: 170, r: 10 },
                                    height: 360,
                                    dragmode: 'pan',
                                    xaxis: { gridcolor: plotGrid, range: [0, 100], title: { text: 'Puntaje %' } },
                                    yaxis: { gridcolor: plotGrid, automargin: true, tickfont: { size: 11 } },
                                }}
                                config={interactivePlotConfig}
                                style={{ width: '100%' }}
                            />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', position: 'relative', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <BarChart2 size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Consultas por Programa</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Distribucion de consultas academicas por programa.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('programs')}>Reset vista</button>
                        </div>
                        <Plot
                            key={getPlotKey('programs')}
                            data={[{
                                type: 'bar',
                                y: byProgram.map(d => d.programa as string),
                                x: byProgram.map(d => d.total),
                                orientation: 'h',
                                marker: { color: isDark ? '#7f9db3' : '#4a6f65', opacity: 0.85 },
                            }]}
                            layout={{
                                paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: { color: plotFont, size: 12 },
                                margin: { t: 10, b: 40, l: 145, r: 10 }, height: 320,
                                dragmode: 'pan',
                                xaxis: { gridcolor: plotGrid, automargin: true },
                                yaxis: { gridcolor: plotGrid, automargin: true, tickfont: { size: 11 } },
                            }}
                            config={interactivePlotConfig}
                            style={{ width: '100%' }}
                        />
                        {dataLoading && (
                            <div style={{
                                position: 'absolute',
                                inset: 0,
                                background: 'linear-gradient(100deg, transparent 0%, color-mix(in srgb, var(--surface) 55%, transparent) 45%, transparent 100%)',
                                animation: 'dash-shimmer 1.2s linear infinite',
                                pointerEvents: 'none',
                            }} />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', position: 'relative', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <TrendingUp size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Tendencia de Uso</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Evolucion temporal de consultas en el periodo seleccionado.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('trend')}>Reset vista</button>
                        </div>
                        <Plot
                            key={getPlotKey('trend')}
                            data={[{
                                type: 'scatter', mode: 'lines+markers',
                                x: trend.map(d => d.fecha as string),
                                y: trend.map(d => d.total),
                                line: { color: isDark ? '#7f9db3' : '#4a6f65', width: 2.5, shape: 'spline' },
                                marker: { color: isDark ? '#7f9db3' : '#4a6f65', size: 7 },
                                fill: 'tozeroy',
                                fillcolor: isDark ? 'rgba(127,157,179,0.12)' : 'rgba(74,111,101,0.10)',
                            }]}
                            layout={{
                                paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: { color: plotFont, size: 12 },
                                margin: { t: 10, b: 40, l: 40, r: 10 }, height: 280,
                                dragmode: 'pan',
                                xaxis: { gridcolor: plotGrid },
                                yaxis: { gridcolor: plotGrid },
                            }}
                            config={interactivePlotConfig}
                            style={{ width: '100%' }}
                        />
                        {dataLoading && (
                            <div style={{
                                position: 'absolute',
                                inset: 0,
                                background: 'linear-gradient(100deg, transparent 0%, color-mix(in srgb, var(--surface) 55%, transparent) 45%, transparent 100%)',
                                animation: 'dash-shimmer 1.2s linear infinite',
                                pointerEvents: 'none',
                            }} />
                        )}
                    </div>
                </div>

                <div data-motion="panel" key={`table-${refreshTick}`} className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <BarChart2 size={17} color="var(--primary)" />
                        <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Temas mas Consultados</h3>
                    </div>
                    <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Ranking de competencias mas populares entre los creadores de oportunidades.</p>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '680px' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid var(--tabler-header-border, var(--border-h))', background: 'var(--surface-2)' }}>
                                    {['#', 'Competencia', 'Programa', 'Consultas'].map(h => (
                                        <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {topics.map((t, i) => (
                                    <tr
                                        data-motion="row"
                                        key={`${refreshTick}-${i}`}
                                        style={{
                                            borderBottom: '1px solid var(--border)',
                                            transition: 'var(--t-fast)',
                                            animation: `dash-row-in 260ms ease ${Math.min(i * 45, 320)}ms both`,
                                            background: i % 2 === 0 ? 'transparent' : 'var(--surface-2)',
                                        }}
                                        onMouseOver={e => (e.currentTarget.style.background = 'var(--surface-3)')}
                                        onMouseOut={e => (e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : 'var(--surface-2)')}
                                    >
                                        <td style={{ padding: '10px 12px', fontSize: '13px', color: 'var(--text-muted)' }}>{i + 1}</td>
                                        <td style={{ padding: '10px 12px', fontSize: '14px', fontWeight: 500, whiteSpace: 'normal', overflowWrap: 'anywhere' }}>{t.competencia}</td>
                                        <td style={{ padding: '10px 12px', whiteSpace: 'normal', overflowWrap: 'anywhere' }}><span className="badge badge-primary" style={{ fontSize: '11px' }}>{t.programa}</span></td>
                                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-heading)', fontWeight: 700, color: 'var(--primary)' }}>
                                            <AnimatedNumber value={Number(t.total ?? 0)} duration={760} />
                                        </td>
                                    </tr>
                                ))}
                                {topics.length === 0 && (
                                    <tr>
                                        <td colSpan={4} style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-hint)', animation: 'dash-fade-in 260ms ease both' }}>
                                            Sin datos para los filtros seleccionados
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: 'var(--space-lg)' }}>
                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <TrendingUp size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Evolucion por Competencia - Generales (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Progresion de nivel promedio en competencias generales a lo largo del tiempo.</p>
                        <div style={{ display: 'flex', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('general-cards-all')}>Reset vista</button>
                        </div>
                        {levelProgressCharts.generalCards.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Aún no hay suficientes datos de nivel para competencias generales.
                            </p>
                        ) : (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '12px', justifyContent: 'center' }}>
                                {levelProgressCharts.generalCards.map(card => (
                                    <div key={`general-${card.competencia}`} style={{ border: '1px solid var(--border)', borderRadius: '12px', padding: '10px', background: 'var(--surface)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                            <p style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>{card.competencia}</p>
                                            <span className="badge badge-primary" style={{ fontSize: '10px' }}>{card.points} puntos</span>
                                        </div>
                                        <Plot
                                            key={`${getPlotKey(`general-card-${card.competencia}`)}-${plotResetVersion['general-cards-all'] ?? 0}`}
                                            data={[card.trace as any]}
                                            layout={{
                                                showlegend: false,
                                                paper_bgcolor: plotBg,
                                                plot_bgcolor: plotBg,
                                                font: { color: plotFont, size: 11 },
                                                margin: { t: 8, b: 46, l: 96, r: 10 },
                                                height: 250,
                                                dragmode: 'pan',
                                                xaxis: {
                                                    type: 'category',
                                                    gridcolor: plotGrid,
                                                    title: { text: 'Fecha' },
                                                    tickangle: -15,
                                                    automargin: true,
                                                },
                                                yaxis: {
                                                    gridcolor: plotGrid,
                                                    range: [0.8, 3.2],
                                                    tickvals: [1, 2, 3],
                                                    ticktext: ['Basico', 'Intermedio', 'Avanzado'],
                                                    title: { text: 'Nivel' },
                                                    automargin: true,
                                                },
                                            }}
                                            config={interactivePlotConfig}
                                            style={{ width: '100%' }}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <Activity size={17} color="var(--accent)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Evolucion por Competencia - Ingles (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Progresion de nivel CEFR en competencias de ingles a lo largo del tiempo.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('english-cards-all')}>Reset vista</button>
                        </div>
                        {levelProgressCharts.englishCards.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Aún no hay suficientes datos de nivel para Inglés.
                            </p>
                        ) : (
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '12px', justifyContent: 'center' }}>
                                {levelProgressCharts.englishCards.map(card => (
                                    <div key={`english-${card.competencia}`} style={{ border: '1px solid var(--border)', borderRadius: '12px', padding: '10px', background: 'var(--surface)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                                            <p style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>{card.competencia}</p>
                                            <span className="badge badge-accent" style={{ fontSize: '10px' }}>{card.points} puntos</span>
                                        </div>
                                        <Plot
                                            key={`${getPlotKey(`english-card-${card.competencia}`)}-${plotResetVersion['english-cards-all'] ?? 0}`}
                                            data={[card.trace as any]}
                                            layout={{
                                                showlegend: false,
                                                paper_bgcolor: plotBg,
                                                plot_bgcolor: plotBg,
                                                font: { color: plotFont, size: 11 },
                                                margin: { t: 8, b: 46, l: 96, r: 10 },
                                                height: 250,
                                                dragmode: 'pan',
                                                xaxis: {
                                                    type: 'category',
                                                    gridcolor: plotGrid,
                                                    title: { text: 'Fecha' },
                                                    tickangle: -15,
                                                    automargin: true,
                                                },
                                                yaxis: {
                                                    gridcolor: plotGrid,
                                                    range: [1.8, 3.2],
                                                    tickvals: [2, 3],
                                                    ticktext: ['A2', 'B1'],
                                                    title: { text: 'Nivel CEFR' },
                                                    automargin: true,
                                                },
                                            }}
                                            config={interactivePlotConfig}
                                            style={{ width: '100%' }}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <PieChart size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Distribucion por Dificultad (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Cantidad de preguntas por competencia segun nivel de dificultad.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('difficulty')}>Reset vista</button>
                        </div>
                        {difficultyDistributionChart.traces.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Sin datos de distribucion por dificultad.
                            </p>
                        ) : (
                            <Plot
                                key={getPlotKey('difficulty')}
                                data={difficultyDistributionChart.traces as any}
                                layout={{
                                    barmode: 'stack',
                                    paper_bgcolor: plotBg,
                                    plot_bgcolor: plotBg,
                                    font: { color: plotFont, size: 12 },
                                    margin: { t: 12, b: 70, l: 42, r: 10 },
                                    height: 380,
                                    dragmode: 'pan',
                                    xaxis: { gridcolor: plotGrid, automargin: true, tickangle: -18, title: { text: 'Competencia' } },
                                    yaxis: { gridcolor: plotGrid, title: { text: 'Total Preguntas' } },
                                    legend: { orientation: 'h', y: 1.14, x: 0 },
                                }}
                                config={interactivePlotConfig}
                                style={{ width: '100%' }}
                            />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <FileText size={17} color="var(--accent)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Ingles — Desglose por Tipo de Pregunta</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Tasa de acierto y volumen por tipo de pregunta en la seccion de ingles.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('english-parts')}>Reset vista</button>
                        </div>
                        {englishPartsChart.labels.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Sin datos de desglose por tipo de pregunta en Ingles.
                            </p>
                        ) : (
                            <Plot
                                key={getPlotKey('english-parts')}
                                data={[{
                                    type: 'bar',
                                    x: englishPartsChart.labels,
                                    y: englishPartsChart.tasaAcierto,
                                    text: englishPartsChart.totals.map(t => `Total: ${t}`),
                                    textposition: 'outside',
                                    marker: { color: isDark ? '#8ec5a8' : '#3f7f66', opacity: 0.88 },
                                    hovertemplate: '<b>%{x}</b><br>Tasa Acierto: %{y:.1f}%<br>%{text}<extra></extra>',
                                }]}
                                layout={{
                                    paper_bgcolor: plotBg,
                                    plot_bgcolor: plotBg,
                                    font: { color: plotFont, size: 12 },
                                    margin: { t: 12, b: 70, l: 50, r: 10 },
                                    height: 360,
                                    dragmode: 'pan',
                                    xaxis: { gridcolor: plotGrid, automargin: true, tickangle: -18, title: { text: 'Tipo de Pregunta' } },
                                    yaxis: { gridcolor: plotGrid, range: [0, 100], title: { text: 'Tasa de Acierto %' } },
                                }}
                                config={interactivePlotConfig}
                                style={{ width: '100%' }}
                            />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <Clock size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Tiempo de Respuesta Promedio (segundos)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Comparativa de tiempo de respuesta entre aciertos y errores por competencia.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('response-time')}>Reset vista</button>
                        </div>
                        {responseTimeChart.traces.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Sin datos de tiempo de respuesta.
                            </p>
                        ) : (
                            <Plot
                                key={getPlotKey('response-time')}
                                data={responseTimeChart.traces as any}
                                layout={{
                                    barmode: 'group',
                                    paper_bgcolor: plotBg,
                                    plot_bgcolor: plotBg,
                                    font: { color: plotFont, size: 12 },
                                    margin: { t: 12, b: 70, l: 50, r: 10 },
                                    height: 360,
                                    dragmode: 'pan',
                                    xaxis: { gridcolor: plotGrid, automargin: true, tickangle: -18, title: { text: 'Competencia' } },
                                    yaxis: { gridcolor: plotGrid, title: { text: 'Tiempo (segundos)' } },
                                    legend: { orientation: 'h', y: 1.14, x: 0 },
                                }}
                                config={interactivePlotConfig}
                                style={{ width: '100%' }}
                            />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <BarChart2 size={17} color="var(--accent)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Comparativa por Programa y Competencia (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Promedio de aciertos por programa y competencia en practicas.</p>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
                            <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '11px' }} onClick={() => resetPlotView('comparison')}>Reset vista</button>
                        </div>
                        {practiceComparisonChart.traces.length === 0 ? (
                            <p style={{ margin: 0, color: 'var(--text-hint)', fontSize: '13px' }}>
                                Aún no hay datos suficientes de práctica para construir la comparativa.
                            </p>
                        ) : (
                            <Plot
                                key={getPlotKey('comparison')}
                                data={practiceComparisonChart.traces as any}
                                layout={{
                                    barmode: 'group',
                                    paper_bgcolor: plotBg,
                                    plot_bgcolor: plotBg,
                                    font: { color: plotFont, size: 12 },
                                    margin: { t: 12, b: 70, l: 42, r: 10 },
                                    height: 360,
                                    dragmode: 'pan',
                                    xaxis: { gridcolor: plotGrid, automargin: true, tickangle: -18 },
                                    yaxis: { gridcolor: plotGrid, range: [0, 100], title: { text: 'Promedio %' } },
                                    legend: { orientation: 'h', y: 1.14, x: 0 },
                                }}
                                config={interactivePlotConfig}
                                style={{ width: '100%' }}
                            />
                        )}
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <Users size={17} color="var(--primary)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Puntaje por Creador de Oportunidades (Practica)</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Detalle individual de intentos, aciertos y puntaje promedio por creador.</p>
                        <div style={{ overflowX: 'auto', maxHeight: '360px' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '720px' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid var(--tabler-header-border, var(--border-h))', background: 'var(--surface-2)' }}>
                                        {['#', 'Creador de Oportunidades', 'Programa', 'Intentos', 'Aciertos', 'Puntaje %'].map(h => (
                                            <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {practiceStudents.slice(0, 60).map((row, i) => (
                                        <tr key={`${row.student_hash}-${i}`} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'var(--surface-2)' }}>
                                            <td style={{ padding: '10px 12px', fontSize: '13px', color: 'var(--text-muted)' }}>{i + 1}</td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px', fontWeight: 500 }}>{row.estudiante}</td>
                                            <td style={{ padding: '10px 12px' }}><span className="badge badge-primary" style={{ fontSize: '11px' }}>{row.programa}</span></td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px' }}>{row.intentos}</td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px' }}>{row.aciertos}</td>
                                            <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--primary)' }}>{Number(row.puntaje_promedio ?? 0).toFixed(1)}%</td>
                                        </tr>
                                    ))}
                                    {practiceStudents.length === 0 && (
                                        <tr>
                                            <td colSpan={6} style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-hint)' }}>
                                                Sin resultados de práctica para los filtros seleccionados.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div data-motion="panel" className="card animate-fade-up" style={{ padding: '16px', border: '1px solid var(--border)', background: 'var(--grad-card)', boxShadow: 'var(--shadow-md)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <ThumbsUp size={17} color="var(--accent)" />
                            <h3 style={{ fontSize: '15px', fontFamily: 'var(--font-heading)', margin: 0 }}>Promedio por Competencia y Programa</h3>
                        </div>
                        <p style={{ margin: '0 0 10px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Desglose de intentos, aciertos y promedio por competencia en cada programa.</p>
                        <div style={{ overflowX: 'auto', maxHeight: '360px' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '720px' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid var(--tabler-header-border, var(--border-h))', background: 'var(--surface-2)' }}>
                                        {['#', 'Programa', 'Competencia', 'Intentos', 'Aciertos', 'Promedio %'].map(h => (
                                            <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {practiceCompetencies.slice(0, 80).map((row, i) => (
                                        <tr key={`${row.programa}-${row.competencia}-${i}`} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'var(--surface-2)' }}>
                                            <td style={{ padding: '10px 12px', fontSize: '13px', color: 'var(--text-muted)' }}>{i + 1}</td>
                                            <td style={{ padding: '10px 12px' }}><span className="badge badge-primary" style={{ fontSize: '11px' }}>{row.programa}</span></td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px', fontWeight: 500 }}>{row.competencia}</td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px' }}>{row.intentos}</td>
                                            <td style={{ padding: '10px 12px', fontSize: '13px' }}>{row.aciertos}</td>
                                            <td style={{ padding: '10px 12px', fontWeight: 700, color: 'var(--accent)' }}>{Number(row.promedio_competencia ?? 0).toFixed(1)}%</td>
                                        </tr>
                                    ))}
                                    {practiceCompetencies.length === 0 && (
                                        <tr>
                                            <td colSpan={6} style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-hint)' }}>
                                                Sin promedio por competencia para los filtros seleccionados.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes dash-pop {
                    from {
                        opacity: 0;
                        transform: translateY(10px) scale(0.98);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0) scale(1);
                    }
                }
                @keyframes dash-slide-up {
                    from {
                        opacity: 0;
                        transform: translateY(14px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                @keyframes dash-loader {
                    0% { transform: translateX(-120%); }
                    100% { transform: translateX(340%); }
                }
                @keyframes dashboard-header-particle-float {
                    0% {
                        transform: translate3d(0, 0, 0) scale(0.92);
                        opacity: 0.2;
                    }
                    50% {
                        transform: translate3d(calc(var(--driftX) * 0.9), calc(var(--driftY) * -0.55), 0) scale(1.08);
                        opacity: 0.44;
                    }
                    100% {
                        transform: translate3d(calc(var(--driftX) * -1.05), calc(var(--driftY) * 0.9), 0) scale(0.98);
                        opacity: 0.24;
                    }
                }
                @keyframes dash-shimmer {
                    from { transform: translateX(-120%); }
                    to { transform: translateX(120%); }
                }
                @keyframes dash-row-in {
                    from {
                        opacity: 0;
                        transform: translateY(8px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                @keyframes dash-bg-shift {
                    0%, 100% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                }
                @keyframes dash-fade-in {
                    from {
                        opacity: 0;
                        transform: translateY(6px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                @keyframes dash-soft-pulse {
                    0%, 100% {
                        box-shadow: 0 0 0 0 color-mix(in srgb, var(--primary) 25%, transparent);
                    }
                    50% {
                        box-shadow: 0 0 0 8px transparent;
                    }
                }
                @media (prefers-reduced-motion: reduce) {
                    * {
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                        scroll-behavior: auto !important;
                    }
                }
                .dash-chart-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }
                @media (max-width: 768px) {
                    .dash-chart-grid {
                        grid-template-columns: 1fr;
                    }
                }
                .dash-card-section {
                    padding: 16px;
                    border: 1px solid var(--border);
                    background: var(--grad-card);
                    box-shadow: var(--shadow-md);
                    border-radius: var(--radius-lg);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .dash-chart-wrapper {
                    width: 100%;
                    display: flex;
                    justify-content: center;
                }
            `}</style>
        </div>
    );
};
