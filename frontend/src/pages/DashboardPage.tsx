import React, { useState, useEffect } from 'react';
import {
    Users, MessageSquare, TrendingUp, Star, Download, Filter,
    BarChart2, Sun, Moon, LogOut
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { coordinatorAPI, aiAPI } from '../api/client';
import type { DashboardMetrics, ChartDataPoint } from '../types';

const KPICard: React.FC<{ icon: React.ReactNode; label: string; value: string | number; color?: string }> = ({ icon, label, value, color }) => (
    <div className="card card-hover animate-fade-up" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ color: color ?? 'var(--primary)', background: 'var(--primary-glow)', padding: '8px', borderRadius: 'var(--radius-md)' }}>{icon}</div>
        </div>
        <p style={{ fontSize: '28px', fontFamily: 'var(--font-heading)', fontWeight: 800, lineHeight: 1, color: color ?? 'var(--text)' }}>{value}</p>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{label}</p>
    </div>
);

export const DashboardPage: React.FC = () => {
    const navigate = useNavigate();
    const { coordinator, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();

    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [byProgram, setByProgram] = useState<ChartDataPoint[]>([]);
    const [trend, setTrend] = useState<ChartDataPoint[]>([]);
    const [topics, setTopics] = useState<ChartDataPoint[]>([]);
    const [programs, setPrograms] = useState<string[]>([]);
    const [progFilter, setProgFilter] = useState('');
    const [dateFrom, setDateFrom] = useState('');
    const [dateTo, setDateTo] = useState('');
    const [exportLoading, setExLoad] = useState(false);
    const [dataLoading, setDataLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const isDark = theme === 'dark';
    const plotBg = isDark ? '#18181B' : '#FFFFFF';
    const plotFont = isDark ? '#FAFAFA' : '#0F172A';
    const plotGrid = isDark ? '#3F3F46' : '#E2E8F0';

    const loadData = async () => {
        setDataLoading(true);
        setError(null);
        try {
            const params = { programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo };
            const [m, bp, tr, tp, pr] = await Promise.all([
                coordinatorAPI.metrics(params),
                coordinatorAPI.byProgram(params),
                coordinatorAPI.trend(params),
                coordinatorAPI.topTopics(params),
                coordinatorAPI.programs(),
            ]);
            setMetrics(m.data);
            setByProgram(bp.data);
            setTrend(tr.data);
            setTopics(tp.data);
            setPrograms(pr.data);
        } catch (e: unknown) {
            const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message;
            setError(msg || 'Error cargando datos del dashboard. Verifica tu sesión.');
        } finally {
            setDataLoading(false);
        }
    };

    useEffect(() => { loadData(); }, [progFilter, dateFrom, dateTo]);

    const downloadBlob = (blob: Blob, filename: string) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
    };

    const exportExcel = async () => {
        setExLoad(true);
        try {
            const res = await aiAPI.exportExcel({ programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo });
            downloadBlob(res.data, `reporte_saberpro_${Date.now()}.xlsx`);
        } catch {
            alert('Error generando el Excel. Intenta de nuevo.');
        } finally {
            setExLoad(false);
        }
    };

    const exportPDF = async () => {
        setExLoad(true);
        try {
            const res = await aiAPI.exportPDF({ programa: progFilter, fecha_inicio: dateFrom, fecha_fin: dateTo });
            downloadBlob(res.data, `reporte_saberpro_${Date.now()}.pdf`);
        } catch {
            alert('Error generando el PDF. Intenta de nuevo.');
        } finally {
            setExLoad(false);
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <header style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)', padding: 'var(--space-md) var(--space-xl)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
                <div>
                    <h1 style={{ fontSize: '20px', fontFamily: 'var(--font-heading)' }}>Dashboard — Asistente Saber Pro</h1>
                    <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{coordinator?.nombre} · UCundinamarca Fusagasugá</p>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
                    <button className="btn btn-secondary" onClick={exportExcel} disabled={exportLoading} style={{ gap: '6px' }}>
                        <Download size={14} /> Excel
                    </button>
                    <button className="btn btn-secondary" onClick={exportPDF} disabled={exportLoading} style={{ gap: '6px' }}>
                        <Download size={14} /> PDF
                    </button>
                    <button className="btn-icon" onClick={toggleTheme} aria-label="Cambiar tema">{isDark ? <Sun size={15} /> : <Moon size={15} />}</button>
                    <button className="btn-icon" onClick={() => { logout(); navigate('/coordinador'); }} aria-label="Cerrar sesión" style={{ color: 'var(--danger)' }}><LogOut size={15} /></button>
                </div>
            </header>

            <div style={{ flex: 1, padding: 'var(--space-xl)', maxWidth: '1400px', margin: '0 auto', width: '100%' }}>
                {/* Banner de error */}
                {error && (
                    <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', marginBottom: 'var(--space-lg)', color: '#DC2626', fontSize: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>⚠️ {error}</span>
                        <button onClick={loadData} style={{ background: '#DC2626', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '4px 12px', cursor: 'pointer', fontSize: '12px' }}>Reintentar</button>
                    </div>
                )}
                {/* Loading skeleton */}
                {dataLoading && !metrics && (
                    <div style={{ textAlign: 'center', padding: 'var(--space-xl)', color: 'var(--text-muted)' }}>
                        Cargando datos del dashboard…
                    </div>
                )}
                {/* Filtros */}
                <div className="card animate-fade-up" style={{ marginBottom: 'var(--space-lg)', display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <Filter size={16} style={{ color: 'var(--text-muted)', alignSelf: 'center' }} />
                    <div style={{ flex: 1, minWidth: '180px' }}>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Programa</label>
                        <select className="input" value={progFilter} onChange={e => setProgFilter(e.target.value)}>
                            <option value="">Todos los programas</option>
                            {programs.map(p => <option key={p} value={p}>{p}</option>)}
                        </select>
                    </div>
                    <div style={{ flex: 1, minWidth: '150px' }}>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Desde</label>
                        <input className="input" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                    </div>
                    <div style={{ flex: 1, minWidth: '150px' }}>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>Hasta</label>
                        <input className="input" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
                    </div>
                </div>

                {/* KPIs */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
                    <KPICard icon={<MessageSquare size={18} />} label="Total Consultas" value={metrics?.total_consultas ?? '—'} />
                    <KPICard icon={<Users size={18} />} label="Estudiantes Únicos" value={metrics?.estudiantes_unicos ?? '—'} color="var(--accent)" />
                    <KPICard icon={<TrendingUp size={18} />} label="Consultas Hoy" value={metrics?.consultas_hoy ?? '—'} color="var(--warning)" />
                    <KPICard icon={<Star size={18} />} label="Calificaciones +" value={metrics?.promedio_positivas ?? '—'} color="var(--primary)" />
                    <KPICard icon={<Users size={18} />} label="Total Estudiantes" value={metrics?.total_estudiantes ?? '—'} />
                </div>

                {/* Gráficos */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 'var(--space-lg)', marginBottom: 'var(--space-lg)' }}>
                    <div className="card animate-fade-up">
                        <h3 style={{ fontSize: '15px', marginBottom: 'var(--space-md)', fontFamily: 'var(--font-heading)' }}>Consultas por Programa</h3>
                        <Plot
                            data={[{
                                type: 'bar',
                                x: byProgram.map(d => d.programa as string),
                                y: byProgram.map(d => d.total),
                                marker: { color: isDark ? '#6366F1' : '#059669', opacity: 0.85 },
                            }]}
                            layout={{
                                paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: { color: plotFont, size: 12 },
                                margin: { t: 10, b: 60, l: 40, r: 10 }, height: 280,
                                xaxis: { gridcolor: plotGrid, tickangle: -30 },
                                yaxis: { gridcolor: plotGrid },
                            }}
                            config={{ displayModeBar: false, responsive: true }}
                            style={{ width: '100%' }}
                        />
                    </div>

                    <div className="card animate-fade-up">
                        <h3 style={{ fontSize: '15px', marginBottom: 'var(--space-md)', fontFamily: 'var(--font-heading)' }}>Tendencia de Uso</h3>
                        <Plot
                            data={[{
                                type: 'scatter', mode: 'lines+markers',
                                x: trend.map(d => d.fecha as string),
                                y: trend.map(d => d.total),
                                line: { color: isDark ? '#6366F1' : '#059669', width: 2.5, shape: 'spline' },
                                marker: { color: isDark ? '#6366F1' : '#059669', size: 7 },
                                fill: 'tozeroy',
                                fillcolor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(5,150,105,0.08)',
                            }]}
                            layout={{
                                paper_bgcolor: plotBg, plot_bgcolor: plotBg, font: { color: plotFont, size: 12 },
                                margin: { t: 10, b: 40, l: 40, r: 10 }, height: 280,
                                xaxis: { gridcolor: plotGrid },
                                yaxis: { gridcolor: plotGrid },
                            }}
                            config={{ displayModeBar: false, responsive: true }}
                            style={{ width: '100%' }}
                        />
                    </div>
                </div>

                {/* Tabla de temas */}
                <div className="card animate-fade-up">
                    <h3 style={{ fontSize: '15px', marginBottom: 'var(--space-md)', fontFamily: 'var(--font-heading)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <BarChart2 size={16} color="var(--primary)" /> Temas más Consultados
                    </h3>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                                    {['#', 'Competencia', 'Programa', 'Consultas'].map(h => (
                                        <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {topics.map((t, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid var(--border)', transition: 'var(--t-fast)' }}
                                        onMouseOver={e => (e.currentTarget.style.background = 'var(--surface-2)')}
                                        onMouseOut={e => (e.currentTarget.style.background = 'transparent')}>
                                        <td style={{ padding: '10px 12px', fontSize: '13px', color: 'var(--text-muted)' }}>{i + 1}</td>
                                        <td style={{ padding: '10px 12px', fontSize: '14px', fontWeight: 500 }}>{t.competencia}</td>
                                        <td style={{ padding: '10px 12px' }}><span className="badge badge-primary" style={{ fontSize: '11px' }}>{t.programa}</span></td>
                                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-heading)', fontWeight: 700, color: 'var(--primary)' }}>{t.total}</td>
                                    </tr>
                                ))}
                                {topics.length === 0 && (
                                    <tr><td colSpan={4} style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-hint)' }}>Sin datos para los filtros seleccionados</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};
