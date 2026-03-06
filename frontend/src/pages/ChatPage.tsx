import React, { useState, useRef, useEffect } from 'react';
import {
    Send, ThumbsUp, ThumbsDown, BookOpen, History, Dumbbell,
    Sun, Moon, LogOut, Loader2, ChevronDown
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { aiAPI, queriesAPI } from '../api/client';
import type { ChatMessage, QueryRecord } from '../types';


// Typing indicator animado
const TypingIndicator: React.FC = () => (
    <div style={{ display: 'flex', gap: '5px', padding: '14px 18px', alignItems: 'center' }}>
        {[0, 1, 2].map(i => (
            <span key={i} className="typing-dot" style={{ animationDelay: `${i * 0.16}s` }} />
        ))}
    </div>
);

// Burbuja de mensaje
const MessageBubble: React.FC<{
    msg: ChatMessage;
    onRate: (id: number, util: boolean) => void;
}> = ({ msg, onRate }) => {
    const isUser = msg.role === 'user';
    return (
        <div className="animate-fade-up" style={{
            display: 'flex', flexDirection: isUser ? 'row-reverse' : 'row',
            gap: 'var(--space-sm)', marginBottom: 'var(--space-md)',
            alignItems: 'flex-end',
        }}>
            {/* Avatar */}
            {!isUser && (
                <div style={{
                    width: '32px', height: '32px', borderRadius: 'var(--radius-full)',
                    background: 'var(--primary)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', flexShrink: 0, boxShadow: 'var(--shadow-glow)',
                }}>
                    <BookOpen size={15} color="#fff" />
                </div>
            )}

            <div style={{ maxWidth: '72%' }}>
                {/* Burbuja */}
                <div style={{
                    padding: '12px 16px',
                    borderRadius: isUser
                        ? 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)'
                        : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
                    background: isUser ? 'var(--primary)' : 'var(--surface)',
                    color: isUser ? '#fff' : 'var(--text)',
                    border: isUser ? 'none' : '1px solid var(--border)',
                    fontSize: '14px', lineHeight: '1.6',
                    boxShadow: isUser ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
                }}>
                    {msg.content}
                </div>

                {/* Fuentes + Acciones (solo asistente) */}
                {!isUser && (
                    <div style={{ marginTop: '6px', display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                        {msg.sources && msg.sources.length > 0 && msg.sources.map(s => (
                            <span key={s} className="badge badge-accent" style={{ fontSize: '11px' }}>{s}</span>
                        ))}
                        {msg.queryId && msg.rated === null && (
                            <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
                                <button className="btn-icon" style={{ width: '28px', height: '28px', color: 'var(--accent)' }}
                                    onClick={() => onRate(msg.queryId!, true)} aria-label="Respuesta útil">
                                    <ThumbsUp size={13} />
                                </button>
                                <button className="btn-icon" style={{ width: '28px', height: '28px', color: 'var(--danger)' }}
                                    onClick={() => onRate(msg.queryId!, false)} aria-label="Respuesta no útil">
                                    <ThumbsDown size={13} />
                                </button>
                            </div>
                        )}
                        {msg.rated !== null && msg.rated !== undefined && (
                            <span className={`badge ${msg.rated ? 'badge-accent' : 'badge-danger'}`} style={{ fontSize: '11px', marginLeft: 'auto' }}>
                                {msg.rated ? '👍 Útil' : '👎 No útil'}
                            </span>
                        )}
                    </div>
                )}

                {/* Timestamp */}
                <p style={{
                    fontSize: '11px', color: 'var(--text-hint)', marginTop: '4px',
                    textAlign: isUser ? 'right' : 'left'
                }}>
                    {new Date(msg.timestamp).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                </p>
            </div>
        </div>
    );
};

export const ChatPage: React.FC = () => {
    const navigate = useNavigate();
    const { student, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();

    const [messages, setMessages] = useState<ChatMessage[]>([{
        id: 'welcome',
        role: 'assistant',
        content: `¡Hola ${student?.nombre?.split(' ')[0] ?? ''}! 👋 Soy tu asistente para las pruebas Saber Pro de **${student?.programa}**. Puedes preguntarme sobre los módulos genéricos o específicos de tu programa. ¿En qué te ayudo hoy?`,
        timestamp: new Date(),
        rated: null,
    }]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [historyOpen, setHistOpen] = useState(false);
    const [history, setHistory] = useState<QueryRecord[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Scroll al fondo cuando llega nuevo mensaje
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    // Cargar historial
    useEffect(() => {
        if (historyOpen && history.length === 0) {
            queriesAPI.history().then(r => setHistory(r.data)).catch(() => { });
        }
    }, [historyOpen]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;
        if (input.trim().length < 2) return;

        const pregunta = input.trim();
        const programa = student?.programa || 'General';
        setInput('');
        setLoading(true);

        // Mensaje del usuario
        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user', content: pregunta, timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMsg]);

        try {
            const res = await aiAPI.consultar({ pregunta, programa });
            const { respuesta, fuentes, tiempo_ms } = res.data;

            // Guardar en Laravel
            const saveRes = await queriesAPI.save({
                programa,
                pregunta, respuesta,
                tiempo_respuesta_ms: tiempo_ms,
            });

            const aiMsg: ChatMessage = {
                id: Date.now().toString() + '_ai',
                role: 'assistant', content: respuesta,
                sources: fuentes, timestamp: new Date(),
                rated: null, queryId: saveRes.data.id,
            };
            setMessages(prev => [...prev, aiMsg]);
        } catch {
            setMessages(prev => [...prev, {
                id: Date.now().toString() + '_err',
                role: 'assistant',
                content: 'Hubo un problema al procesar tu pregunta. Por favor intenta de nuevo.',
                timestamp: new Date(), rated: null,
            }]);
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleRate = async (queryId: number, util: boolean) => {
        await queriesAPI.rate(queryId, util).catch(() => { });
        setMessages(prev => prev.map(m =>
            m.queryId === queryId ? { ...m, rated: util } : m
        ));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', background: 'var(--bg)', overflow: 'hidden' }}>
            {/* ── Sidebar ──────────────────────────────────── */}
            <aside style={{
                width: '260px', flexShrink: 0,
                background: 'var(--surface)', borderRight: '1px solid var(--border)',
                display: 'flex', flexDirection: 'column', padding: 'var(--space-md)',
            }}>
                {/* Logo */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: 'var(--space-xl)', padding: '4px 0' }}>
                    <div style={{ background: 'var(--primary)', borderRadius: 'var(--radius-md)', padding: '8px', boxShadow: 'var(--shadow-glow)' }}>
                        <BookOpen size={18} color="#fff" />
                    </div>
                    <div>
                        <p style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '15px', lineHeight: 1 }}>Saber Pro</p>
                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>Asistente IA</p>
                    </div>
                </div>

                {/* Info estudiante */}
                <div style={{ background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', padding: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
                    <p style={{ fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{student?.nombre}</p>
                    <span className="badge badge-primary" style={{ fontSize: '11px' }}>{student?.programa}</span>
                </div>

                {/* Nav Buttons */}
                <button onClick={() => navigate('/practica')}
                    className="btn btn-secondary" style={{ marginBottom: 'var(--space-sm)', justifyContent: 'flex-start', gap: 'var(--space-sm)' }}>
                    <Dumbbell size={16} /> Preguntas de Práctica
                </button>

                <button onClick={() => setHistOpen(o => !o)}
                    className="btn btn-secondary" style={{ marginBottom: 'var(--space-sm)', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                        <History size={16} /> Historial
                    </span>
                    <ChevronDown size={14} style={{ transform: historyOpen ? 'rotate(180deg)' : 'none', transition: 'var(--t-fast)' }} />
                </button>

                {/* Historial panel */}
                {historyOpen && (
                    <div className="animate-fade-up" style={{
                        background: 'var(--surface-2)', borderRadius: 'var(--radius-md)',
                        padding: 'var(--space-sm)', marginBottom: 'var(--space-sm)',
                        maxHeight: '200px', overflowY: 'auto',
                    }}>
                        {history.length === 0
                            ? <p style={{ fontSize: '12px', color: 'var(--text-hint)', padding: '8px', textAlign: 'center' }}>Sin historial reciente</p>
                            : history.map(q => (
                                <div key={q.id} style={{ padding: '8px', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                                    onClick={() => {
                                        setMessages(prev => [...prev, { id: q.id.toString(), role: 'user', content: q.pregunta, timestamp: new Date(q.created_at) },
                                        { id: q.id.toString() + '_a', role: 'assistant', content: q.respuesta, timestamp: new Date(q.created_at), rated: q.calificacion, queryId: q.id }]);
                                        setHistOpen(false);
                                    }}>
                                    <p style={{ fontSize: '12px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.pregunta}</p>
                                </div>
                            ))
                        }
                    </div>
                )}

                <div style={{ marginTop: 'auto', display: 'flex', gap: 'var(--space-sm)' }}>
                    <button className="btn-icon" onClick={toggleTheme} aria-label="Cambiar tema" style={{ flex: 1, width: 'auto', height: '36px' }}>
                        {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                    </button>
                    <button className="btn-icon" onClick={() => { logout(); navigate('/login'); }}
                        aria-label="Cerrar sesión" style={{ flex: 1, width: 'auto', height: '36px', color: 'var(--danger)' }}>
                        <LogOut size={15} />
                    </button>
                </div>
            </aside>

            {/* ── Chat Area ──────────────────────────────────── */}
            <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {/* Header */}
                <header style={{
                    padding: 'var(--space-md) var(--space-xl)',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--surface)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                    <div>
                        <h2 style={{ fontSize: '18px', fontFamily: 'var(--font-heading)' }}>Chat con el Asistente</h2>
                        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Respuestas basadas en guías oficiales del ICFES</p>
                    </div>
                    <span className="badge badge-accent" style={{ fontSize: '12px' }}>
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
                        IA Activa
                    </span>
                </header>

                {/* Messages */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-xl)' }}>
                    {messages.map(msg => (
                        <MessageBubble key={msg.id} msg={msg} onRate={handleRate} />
                    ))}
                    {loading && (
                        <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'flex-end', marginBottom: 'var(--space-md)' }}>
                            <div style={{ width: '32px', height: '32px', borderRadius: 'var(--radius-full)', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'var(--shadow-glow)' }}>
                                <BookOpen size={15} color="#fff" />
                            </div>
                            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)', boxShadow: 'var(--shadow-sm)' }}>
                                <TypingIndicator />
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Input */}
                <div style={{
                    padding: 'var(--space-md) var(--space-xl)',
                    borderTop: '1px solid var(--border)',
                    background: 'var(--surface)',
                }}>
                    <div style={{
                        display: 'flex', gap: 'var(--space-sm)', alignItems: 'flex-end',
                        background: 'var(--surface-2)', borderRadius: 'var(--radius-lg)',
                        border: '1.5px solid var(--border)', padding: '8px 8px 8px 16px',
                        transition: 'var(--t-fast)',
                    }}>
                        <textarea ref={inputRef} className="input"
                            style={{
                                flex: 1, border: 'none', background: 'transparent', resize: 'none',
                                minHeight: '24px', maxHeight: '120px', padding: 0, boxShadow: 'none',
                                fontSize: '15px', lineHeight: '1.5',
                            }}
                            placeholder="Pregunta sobre Saber Pro… (Enter para enviar)"
                            value={input} onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown} rows={1} disabled={loading} />
                        <button className="btn btn-primary" onClick={handleSend} disabled={!input.trim() || loading}
                            style={{ height: '38px', padding: '0 16px', flexShrink: 0 }}
                            aria-label="Enviar pregunta">
                            {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
                        </button>
                    </div>
                    <p style={{ fontSize: '11px', color: 'var(--text-hint)', marginTop: '8px', textAlign: 'center' }}>
                        Shift+Enter para nueva línea · Las respuestas se basan en documentos oficiales del ICFES
                    </p>
                </div>
            </main>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};
