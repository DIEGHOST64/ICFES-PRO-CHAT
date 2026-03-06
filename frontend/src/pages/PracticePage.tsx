import React, { useState } from 'react';
import { CheckCircle, XCircle, ChevronRight, RefreshCw, Trophy, BookOpen, ArrowLeft, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { aiAPI } from '../api/client';
import type { Pregunta } from '../types';

const COMPETENCIAS = ['Lectura Crítica', 'Razonamiento Cuantitativo', 'Comunicación Escrita', 'Inglés', 'Ciudadanas', 'Específica'];

export const PracticePage: React.FC = () => {
    const navigate = useNavigate();
    const { student } = useAuth();
    const [competencia, setCompetencia] = useState('');
    const [preguntas, setPreguntas] = useState<Pregunta[]>([]);
    const [current, setCurrent] = useState(0);
    const [selected, setSelected] = useState<string | null>(null);
    const [revealed, setRevealed] = useState(false);
    const [score, setScore] = useState(0);
    const [done, setDone] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const loadQuestions = async () => {
        setLoading(true); setError(''); setPreguntas([]);
        setCurrent(0); setSelected(null); setRevealed(false); setScore(0); setDone(false);
        try {
            const res = await aiAPI.sugerencias({
                programa: student!.programa,
                competencia: competencia || undefined,
                cantidad: 10,
            });
            if (res.data.length === 0) { setError('No hay preguntas disponibles para esos filtros.'); }
            else setPreguntas(res.data);
        } catch { setError('Error al cargar preguntas. Verifica la conexión.'); }
        finally { setLoading(false); }
    };

    const q = preguntas[current];
    const tieneOpciones = (q?.opciones?.length ?? 0) > 0;
    // Número de preguntas con opciones (para el marcador)
    const totalConOpciones = preguntas.filter(p => p.opciones.length > 0).length;

    const handleSelect = (opcion: string) => {
        if (revealed) return;
        setSelected(opcion);
        setRevealed(true);
        if (opcion === q.respuesta_correcta) setScore(s => s + 1);
    };

    const handleNext = () => {
        if (current + 1 >= preguntas.length) { setDone(true); return; }
        setSelected(null); setRevealed(false); setCurrent(c => c + 1);
    };

    const handleContinueFragment = () => {
        // Avanza sin modificar el score (fragmento de lectura)
        handleNext();
    };

    const getOptionStyle = (opcion: string): React.CSSProperties => {
        if (!revealed) return {};
        if (opcion === q.respuesta_correcta)
            return { background: 'rgba(16,185,129,0.15)', borderColor: 'var(--accent)', color: 'var(--accent)' };
        if (opcion === selected)
            return { background: 'rgba(239,68,68,0.1)', borderColor: 'var(--danger)', color: 'var(--danger)' };
        return { opacity: 0.45 };
    };

    // ── Pantalla de resultados ─────────────────────────
    if (done) {
        const pct = Math.round((score / preguntas.length) * 100);
        return (
            <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-lg)' }}>
                <div className="card animate-scale-in" style={{ maxWidth: '440px', width: '100%', textAlign: 'center', padding: 'var(--space-2xl)' }}>
                    <Trophy size={56} color={pct >= 70 ? 'var(--accent)' : 'var(--warning)'} style={{ margin: '0 auto var(--space-lg)' }} />
                    <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>{pct}%</h1>
                    <p style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-xl)' }}>
                        {totalConOpciones > 0
                            ? `${score} de ${totalConOpciones} correctas${pct >= 70 ? ' · ¡Excelente trabajo!' : ' · ¡Sigue practicando!'}`
                            : `${preguntas.length} fragmentos revisados · ¡Buen repaso!`
                        }
                    </p>
                    <div style={{ display: 'flex', gap: 'var(--space-sm)', justifyContent: 'center' }}>
                        <button className="btn btn-primary" onClick={loadQuestions}><RefreshCw size={15} /> Otra ronda</button>
                        <button className="btn btn-ghost" onClick={() => navigate('/chat')}><BookOpen size={15} /> Ir al chat</button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: 'var(--space-lg)' }}>
            <div style={{ maxWidth: '680px', margin: '0 auto' }}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', marginBottom: 'var(--space-xl)' }}>
                    <button className="btn-icon" onClick={() => navigate('/chat')} aria-label="Volver al chat"><ArrowLeft size={16} /></button>
                    <div>
                        <h1 style={{ fontSize: '22px' }}>Preguntas de Práctica</h1>
                        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{student?.programa}</p>
                    </div>
                </div>

                {/* Filtros */}
                {preguntas.length === 0 && !loading && (
                    <div className="card animate-fade-up">
                        <h2 style={{ fontSize: '17px', marginBottom: 'var(--space-md)' }}>Configura tu sesión</h2>
                        <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                            Competencia (opcional)
                        </label>
                        <select className="input" style={{ marginBottom: 'var(--space-lg)' }}
                            value={competencia} onChange={e => setCompetencia(e.target.value)}>
                            <option value="">Todas las competencias</option>
                            {COMPETENCIAS.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                        {error && <p style={{ color: 'var(--danger)', fontSize: '13px', marginBottom: 'var(--space-md)' }}>{error}</p>}
                        <button className="btn btn-primary" onClick={loadQuestions} style={{ width: '100%', justifyContent: 'center', height: '44px' }}>
                            Comenzar práctica
                        </button>
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div style={{ textAlign: 'center', padding: 'var(--space-2xl)' }}>
                        <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)', margin: '0 auto' }} />
                        <p style={{ color: 'var(--text-muted)', marginTop: 'var(--space-md)' }}>Cargando preguntas…</p>
                    </div>
                )}

                {/* Quiz */}
                {q && !loading && (
                    <>
                        {/* Progress */}
                        <div style={{ marginBottom: 'var(--space-lg)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Pregunta {current + 1} de {preguntas.length}</span>
                                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--accent)' }}>{score} correctas</span>
                            </div>
                            <div style={{ height: '6px', background: 'var(--surface-2)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%', borderRadius: 'var(--radius-full)', background: 'var(--primary)',
                                    width: `${((current + 1) / preguntas.length) * 100}%`, transition: 'var(--t-slow)'
                                }} />
                            </div>
                        </div>

                        {/* Pregunta */}
                        <div className="card animate-fade-up" style={{ marginBottom: 'var(--space-md)' }}>
                            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
                                <span className="badge badge-primary">{q.competencia}</span>
                            </div>
                            <p style={{ fontSize: '16px', lineHeight: '1.65', fontWeight: 500 }}>{q.enunciado}</p>
                        </div>

                        {/* Opciones — solo si la pregunta es estructurada */}
                        {tieneOpciones && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginBottom: 'var(--space-lg)' }}>
                                {q.opciones.map((op, i) => (
                                    <button key={i} onClick={() => handleSelect(op)}
                                        className="card animate-fade-up"
                                        style={{
                                            textAlign: 'left', cursor: revealed ? 'default' : 'pointer',
                                            padding: 'var(--space-md)', transition: 'var(--t-base)',
                                            display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
                                            animationDelay: `${i * 60}ms`,
                                            ...getOptionStyle(op),
                                        }}>
                                        <span style={{
                                            width: '28px', height: '28px', borderRadius: 'var(--radius-full)',
                                            border: '1.5px solid var(--border)', display: 'flex', alignItems: 'center',
                                            justifyContent: 'center', fontSize: '12px', fontWeight: 700, flexShrink: 0
                                        }}>
                                            {['A', 'B', 'C', 'D'][i]}
                                        </span>
                                        <span style={{ fontSize: '14px' }}>{op}</span>
                                        {revealed && op === q.respuesta_correcta && <CheckCircle size={16} style={{ marginLeft: 'auto', color: 'var(--accent)' }} />}
                                        {revealed && op === selected && op !== q.respuesta_correcta && <XCircle size={16} style={{ marginLeft: 'auto', color: 'var(--danger)' }} />}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Modo lectura — fragmento PDF sin opciones */}
                        {!tieneOpciones && (
                            <div className="card animate-fade-up" style={{ marginBottom: 'var(--space-lg)', borderColor: 'var(--primary)', opacity: 0.9 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: '10px' }}>
                                    <BookOpen size={16} color="var(--primary)" />
                                    <strong style={{ fontSize: '13px', color: 'var(--primary)' }}>Fragmento del cuadernillo oficial ICFES</strong>
                                </div>
                                <p style={{ fontSize: '13px', lineHeight: '1.65', color: 'var(--text-muted)', marginBottom: 'var(--space-md)' }}>
                                    Lee el fragmento y reflexiona sobre las ideas principales antes de continuar.
                                </p>
                                <button className="btn btn-primary" onClick={handleContinueFragment}>
                                    {current + 1 >= preguntas.length ? <><Trophy size={15} /> Ver resultados</> : <>Continuar <ChevronRight size={15} /></>}
                                </button>
                            </div>
                        )}

                        {/* Retroalimentación — solo para preguntas estructuradas con opciones */}
                        {tieneOpciones && revealed && (
                            <div className="card animate-fade-up" style={{ borderColor: selected === q.respuesta_correcta ? 'var(--accent)' : 'var(--danger)', marginBottom: 'var(--space-lg)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: '8px' }}>
                                    {selected === q.respuesta_correcta
                                        ? <CheckCircle size={18} color="var(--accent)" />
                                        : <XCircle size={18} color="var(--danger)" />}
                                    <strong style={{ color: selected === q.respuesta_correcta ? 'var(--accent)' : 'var(--danger)' }}>
                                        {selected === q.respuesta_correcta ? '¡Correcto!' : 'Incorrecto'}
                                    </strong>
                                </div>
                                <p style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)' }}>{q.explicacion}</p>
                                <button className="btn btn-primary" onClick={handleNext} style={{ marginTop: 'var(--space-md)' }}>
                                    {current + 1 >= preguntas.length ? <><Trophy size={15} /> Ver resultados</> : <>Siguiente <ChevronRight size={15} /></>}
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};
