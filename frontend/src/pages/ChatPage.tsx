import React, { useState, useRef, useEffect, useMemo } from 'react';
import { BlockMath } from 'react-katex';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Barbell, ClockCounterClockwise } from '@phosphor-icons/react';
import {
    Send, ThumbsUp, ThumbsDown, Brain,
    Sun, Moon, LogOut, Loader2, ChevronDown, Trash2, FolderPlus, Plus, MessageSquarePlus, Menu, X
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { aiAPI, queriesAPI } from '../api/client';
import type { ChatMessage, QueryRecord } from '../types';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';
import { useVisualMood } from '../context/VisualMoodContext';
import { InstitutionalLogo } from '../components/InstitutionalLogo';

const CHAT_VISUAL_HISTORY_PREFIX = 'sp_chat_visual_history_cutoff_v1';
const CHAT_STUDY_FOLDERS_PREFIX = 'sp_chat_study_folders_v1';
const CHAT_STUDY_FOLDER_MAP_PREFIX = 'sp_chat_study_folder_map_v1';
const CHAT_STUDY_FOLDER_CHATS_PREFIX = 'sp_chat_study_folder_chats_v1';

const getStudentHistoryStorageKey = (nombre?: string, programa?: string) => {
    const safeNombre = (nombre || 'anon').trim().toLowerCase().replace(/\s+/g, '_');
    const safePrograma = (programa || 'general').trim().toLowerCase().replace(/\s+/g, '_');
    return `${CHAT_VISUAL_HISTORY_PREFIX}:${safeNombre}:${safePrograma}`;
};

const getStudentStudyFoldersKey = (nombre?: string, programa?: string) => {
    const safeNombre = (nombre || 'anon').trim().toLowerCase().replace(/\s+/g, '_');
    const safePrograma = (programa || 'general').trim().toLowerCase().replace(/\s+/g, '_');
    return `${CHAT_STUDY_FOLDERS_PREFIX}:${safeNombre}:${safePrograma}`;
};

const getStudentStudyFolderMapKey = (nombre?: string, programa?: string) => {
    const safeNombre = (nombre || 'anon').trim().toLowerCase().replace(/\s+/g, '_');
    const safePrograma = (programa || 'general').trim().toLowerCase().replace(/\s+/g, '_');
    return `${CHAT_STUDY_FOLDER_MAP_PREFIX}:${safeNombre}:${safePrograma}`;
};

const getStudentStudyFolderChatsKey = (nombre?: string, programa?: string) => {
    const safeNombre = (nombre || 'anon').trim().toLowerCase().replace(/\s+/g, '_');
    const safePrograma = (programa || 'general').trim().toLowerCase().replace(/\s+/g, '_');
    return `${CHAT_STUDY_FOLDER_CHATS_PREFIX}:${safeNombre}:${safePrograma}`;
};

type StudyFolder = {
    id: string;
    name: string;
    createdAt: string;
};

type StudyFolderChat = {
    id: string;
    folderId: string;
    title: string;
    createdAt: string;
    updatedAt: string;
    messages: ChatMessage[];
};

type StoredChatMessage = Omit<ChatMessage, 'timestamp'> & { timestamp: string };
type StoredStudyFolderChat = Omit<StudyFolderChat, 'messages'> & { messages: StoredChatMessage[] };

const serializeChatMessages = (messages: ChatMessage[]): StoredChatMessage[] =>
    messages.map((m) => ({ ...m, timestamp: m.timestamp.toISOString() }));

const deserializeChatMessages = (messages: StoredChatMessage[]): ChatMessage[] =>
    messages.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }));

const deriveChatTitle = (messages: ChatMessage[]) => {
    const firstUserMessage = messages.find((m) => m.role === 'user')?.content?.trim();
    if (!firstUserMessage) return 'Nuevo chat';
    return firstUserMessage.length > 42 ? `${firstUserMessage.slice(0, 42)}...` : firstUserMessage;
};

const buildWelcomeMessage = (studentName?: string): ChatMessage => ({
    id: 'welcome',
    role: 'assistant',
    content: `¡Hola ${studentName?.split(' ')[0] ?? ''}! 👋 Estoy aquí para ayudarte a practicar y mejorar en Saber Pro. ¿Qué tema quieres repasar hoy?`,
    timestamp: new Date(),
    rated: null,
});

const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

const groupHistoryByDate = (items: QueryRecord[]) => {
    const now = new Date();
    const todayStart = startOfDay(now).getTime();
    const oneDayMs = 24 * 60 * 60 * 1000;

    const groups: Array<{ key: string; label: string; items: QueryRecord[] }> = [
        { key: 'hoy', label: 'Hoy', items: [] },
        { key: 'ayer', label: 'Ayer', items: [] },
        { key: 'semana', label: 'Esta semana', items: [] },
        { key: 'anteriores', label: 'Anteriores', items: [] },
    ];

    for (const q of items) {
        const createdAt = new Date(q.created_at);
        if (Number.isNaN(createdAt.getTime())) {
            groups[3].items.push(q);
            continue;
        }

        const itemDayStart = startOfDay(createdAt).getTime();
        const dayDiff = Math.floor((todayStart - itemDayStart) / oneDayMs);

        if (dayDiff <= 0) groups[0].items.push(q);
        else if (dayDiff === 1) groups[1].items.push(q);
        else if (dayDiff <= 7) groups[2].items.push(q);
        else groups[3].items.push(q);
    }

    return groups.filter(g => g.items.length > 0);
};

type PromptTheme = 'lectura' | 'cuantitativo' | 'ingles' | 'ciudadanas' | 'escrita' | 'general';

const detectPromptTheme = (record: QueryRecord): PromptTheme => {
    const text = `${record.competencia || ''} ${record.pregunta || ''} ${record.respuesta || ''}`.toLowerCase();

    if (text.includes('lectura') || text.includes('critica') || text.includes('comprension')) return 'lectura';
    if (text.includes('cuantit') || text.includes('matematic') || text.includes('algebra') || text.includes('estadistica')) return 'cuantitativo';
    if (text.includes('ingles') || text.includes('english') || text.includes('grammar') || text.includes('vocabulary') || text.includes('reading')) return 'ingles';
    if (text.includes('ciudadana') || text.includes('etica') || text.includes('constitucion') || text.includes('social')) return 'ciudadanas';
    if (text.includes('escrita') || text.includes('redaccion') || text.includes('argumentativa')) return 'escrita';
    return 'general';
};

const THEME_LABELS: Record<PromptTheme, string> = {
    lectura: 'lectura critica',
    cuantitativo: 'razonamiento cuantitativo',
    ingles: 'ingles',
    ciudadanas: 'competencias ciudadanas',
    escrita: 'comunicacion escrita',
    general: 'repaso general',
};

const estimateLevelFromPractice = (items: QueryRecord[]): 'basico' | 'intermedio' | 'avanzado' => {
    const practice = items
        .filter((q) => q.es_practica && q.acierto !== null && q.acierto !== undefined)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 16);

    if (!practice.length) return 'intermedio';

    const hits = practice.filter((p) => p.acierto).length;
    const ratio = hits / practice.length;

    if (ratio >= 0.72) return 'avanzado';
    if (ratio >= 0.45) return 'intermedio';
    return 'basico';
};

const buildPersonalizedPrompts = (items: QueryRecord[]): string[] => {
    if (!items.length) {
        return [
            'Parcero, hagamos 3 preguntas de lectura critica para calentar.',
            'Explicame razonamiento cuantitativo en version facil y rapida.',
            'Quiero practicar ingles tipo Saber Pro con truquitos utiles.',
        ];
    }

    const counts: Record<PromptTheme, number> = {
        lectura: 0,
        cuantitativo: 0,
        ingles: 0,
        ciudadanas: 0,
        escrita: 0,
        general: 0,
    };
    const attempts: Record<PromptTheme, number> = {
        lectura: 0,
        cuantitativo: 0,
        ingles: 0,
        ciudadanas: 0,
        escrita: 0,
        general: 0,
    };
    const hits: Record<PromptTheme, number> = {
        lectura: 0,
        cuantitativo: 0,
        ingles: 0,
        ciudadanas: 0,
        escrita: 0,
        general: 0,
    };

    items.forEach((q) => {
        const theme = detectPromptTheme(q);
        counts[theme] += 1;
        if (q.es_practica && q.acierto !== null && q.acierto !== undefined) {
            attempts[theme] += 1;
            if (q.acierto) hits[theme] += 1;
        }
    });

    const themeList = (Object.keys(counts) as PromptTheme[]).filter(t => t !== 'general');

    const mostUsedTheme = themeList.reduce((best, t) => (counts[t] > counts[best] ? t : best), 'lectura' as PromptTheme);

    const weakestByPractice = themeList
        .filter(t => attempts[t] > 0)
        .sort((a, b) => {
            const ra = hits[a] / attempts[a];
            const rb = hits[b] / attempts[b];
            return ra - rb;
        })[0];

    const recent = [...items]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 6)
        .map(detectPromptTheme)
        .find(t => t !== 'general') || mostUsedTheme;

    const reinforcementTheme = weakestByPractice || mostUsedTheme;
    const estimatedLevel = estimateLevelFromPractice(items);

    const suggestions = [
        `Con base en mi historial, quiero reforzar ${THEME_LABELS[reinforcementTheme]} en nivel ${estimatedLevel} con 4 preguntas guiadas.`,
        `Dame un mini simulacro de ${THEME_LABELS[mostUsedTheme]} en nivel ${estimatedLevel} con dificultad progresiva y feedback corto.`,
        `Sigamos con ${THEME_LABELS[recent]} tipo Saber Pro, adaptado a mi nivel ${estimatedLevel} y con explicacion paso a paso.`,
    ];

    return Array.from(new Set(suggestions)).slice(0, 3);
};

const markdownComponents = {
    p: ({ children }: { children?: React.ReactNode }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
    ul: ({ children }: { children?: React.ReactNode }) => <ul style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ul>,
    ol: ({ children }: { children?: React.ReactNode }) => <ol style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ol>,
    li: ({ children }: { children?: React.ReactNode }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
    strong: ({ children }: { children?: React.ReactNode }) => <strong style={{ fontWeight: 700, color: 'inherit' }}>{children}</strong>,
    em: ({ children }: { children?: React.ReactNode }) => <em style={{ fontStyle: 'italic', color: 'inherit' }}>{children}</em>,
    code: ({ children }: { children?: React.ReactNode }) => (
        <code style={{ background: 'rgba(15, 23, 42, 0.08)', borderRadius: '6px', padding: '1px 6px', fontSize: '13px', color: 'inherit' }}>
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
            color: 'inherit',
        }}>
            {children}
        </pre>
    ),
};

const MessageBubble: React.FC<{
    msg: ChatMessage;
    onRate: (id: number, util: boolean) => void;
}> = ({ msg, onRate }) => {
    const isUser = msg.role === 'user';

    return (
        <div className="animate-fade-up" style={{
            display: 'flex',
            flexDirection: isUser ? 'row-reverse' : 'row',
            gap: 'var(--space-sm)',
            marginBottom: 'var(--space-md)',
            alignItems: 'flex-end',
        }}>
            {!isUser && (
                <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                }}>
                    <Brain size={15} color="#fff" />
                </div>
            )}

            <div className={`chat-msg-bubble-${isUser ? 'user' : 'ai'}`} style={{ maxWidth: '72%' }}>
                <div style={{
                    padding: '12px 16px',
                    borderRadius: isUser
                        ? 'var(--radius-lg) var(--radius-lg) var(--radius-sm) var(--radius-lg)'
                        : 'var(--radius-lg) var(--radius-lg) var(--radius-lg) var(--radius-sm)',
                    background: isUser ? 'var(--primary)' : 'var(--surface)',
                    color: isUser ? '#fff' : 'var(--text)',
                    border: isUser ? 'none' : '1px solid var(--border)',
                    boxShadow: isUser ? '0 10px 20px rgba(0,0,0,0.20)' : '0 8px 18px rgba(0,0,0,0.10)',
                    fontSize: '14px',
                    lineHeight: '1.6',
                }}>
                    {msg.streaming && !msg.content
                        ? <div style={{ display: 'flex', gap: '5px', alignItems: 'center', padding: '2px 0' }}>
                            {[0, 1, 2].map(i => <span key={i} className="typing-dot" style={{ animationDelay: `${i * 0.16}s` }} />)}
                          </div>
                        : isUser
                            ? <>{msg.content}{msg.streaming && <span className="streaming-cursor" />}</>
                            : <div style={{ display: 'grid', gap: '2px' }}>
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm, remarkMath]}
                                    rehypePlugins={[[rehypeKatex, { throwOnError: false, strict: false }]]}
                                    components={markdownComponents}
                                >
                                    {msg.content || ''}
                                </ReactMarkdown>
                                {msg.streaming && <span className="streaming-cursor" />}
                              </div>}
                                </div>

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

                {!isUser && (msg.guideImageLoading || msg.guideImageUrl) && (
                    <div style={{ marginTop: '10px' }}>
                        {msg.guideImageLoading && !msg.guideImageUrl && (
                            <div style={{
                                borderRadius: '12px',
                                border: '1px solid var(--border)',
                                background: 'linear-gradient(120deg, #eef4f8 0%, #e7f0f8 45%, #eef4f8 100%)',
                                backgroundSize: '200% 100%',
                                animation: 'guide-shimmer 1.2s linear infinite',
                                padding: '12px',
                                fontSize: '12px',
                                color: 'var(--text-muted)',
                            }}>
                                Generando guia visual...
                            </div>
                        )}
                        {msg.guideImageUrl && (
                            <figure style={{
                                borderRadius: '12px',
                                overflow: 'hidden',
                                border: '1px solid var(--border)',
                                background: 'var(--surface)',
                                boxShadow: '0 8px 20px rgba(0,0,0,0.08)',
                            }}>
                                <img
                                    src={msg.guideImageUrl}
                                    alt={msg.guideImageCaption ?? 'Guia visual'}
                                    style={{ width: '100%', maxWidth: '420px', display: 'block' }}
                                />
                                {msg.guideImageCaption && (
                                    <figcaption style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '8px 10px' }}>
                                        {msg.guideImageCaption}
                                    </figcaption>
                                )}
                            </figure>
                        )}
                        {!msg.guideImageLoading && !msg.guideImageUrl && msg.guideImageError && (
                            <p style={{ fontSize: '11px', color: 'var(--text-hint)', marginTop: '6px' }}>
                                No se pudo generar imagen en este turno ({msg.guideImageModel || 'sin modelo'}).
                            </p>
                        )}
                    </div>
                )}

                {!isUser && msg.latexFormula && (
                    <div style={{
                        marginTop: '10px',
                        border: '1px solid var(--border)',
                        borderRadius: '12px',
                        background: 'var(--surface)',
                        padding: '10px 12px',
                        boxShadow: '0 6px 14px rgba(0,0,0,0.06)',
                    }}>
                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 700 }}>Formula guia (LaTeX)</p>
                        <div style={{ overflowX: 'auto' }}>
                            <BlockMath math={msg.latexFormula} errorColor="#dc2626" />
                        </div>
                        {msg.latexExplanation && (
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>{msg.latexExplanation}</p>
                        )}
                    </div>
                )}

                {!isUser && msg.guideSteps && msg.guideSteps.length > 0 && (
                    <div style={{
                        marginTop: '10px',
                        border: '1px solid var(--border)',
                        borderRadius: '12px',
                        background: 'var(--surface)',
                        padding: '10px 12px',
                    }}>
                        <p style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text)', marginBottom: '8px' }}>{msg.guideTitle || 'Guia visual paso a paso'}</p>
                        <ol style={{ paddingLeft: '18px', margin: 0, display: 'grid', gap: '6px' }}>
                            {msg.guideSteps.map((step, idx) => (
                                <li key={`${idx}-${step}`} style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.45 }}>{step}</li>
                            ))}
                        </ol>
                    </div>
                )}

                <p style={{
                    fontSize: '11px',
                    color: 'var(--text-hint)',
                    marginTop: '4px',
                    textAlign: isUser ? 'right' : 'left',
                }}>
                    {new Date(msg.timestamp).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                </p>
            </div>
        </div>
    );
};

export const ChatPage: React.FC = () => {
    const pageRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();
    const { student, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const practiceNavTimerRef = useRef<number | null>(null);
    const loadedFoldersKeyRef = useRef<string | null>(null);
    const loadedFolderMapKeyRef = useRef<string | null>(null);
    const loadedFolderChatsKeyRef = useRef<string | null>(null);
    const skipNextFoldersPersistRef = useRef(false);
    const skipNextFolderMapPersistRef = useRef(false);
    const skipNextFolderChatsPersistRef = useRef(false);
    const abortRef = useRef<AbortController | null>(null);

    const [messages, setMessages] = useState<ChatMessage[]>([buildWelcomeMessage(student?.nombre)]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState<QueryRecord[]>([]);
    const [historyVisualCutoffMs, setHistoryVisualCutoffMs] = useState<number | null>(null);
    const [studyFolders, setStudyFolders] = useState<StudyFolder[]>([]);
    const [historyFolderMap, setHistoryFolderMap] = useState<Record<string, string>>({});
    const [folderChats, setFolderChats] = useState<StudyFolderChat[]>([]);
    const [folderDraft, setFolderDraft] = useState('');
    const [selectedHistoryFolderId, setSelectedHistoryFolderId] = useState<string>('all');
    const [activeWorkspaceFolderId, setActiveWorkspaceFolderId] = useState<string | null>(null);
    const [activeFolderChatId, setActiveFolderChatId] = useState<string | null>(null);
    const [practiceTransitioning, setPracticeTransitioning] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [isDesktop, setIsDesktop] = useState(window.innerWidth >= 769);

    useEffect(() => {
        const mq = window.matchMedia('(min-width: 769px)');
        const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
        setIsDesktop(mq.matches);
        mq.addEventListener('change', handler);
        return () => mq.removeEventListener('change', handler);
    }, []);

    const quickPrompts = useMemo(() => buildPersonalizedPrompts(history), [history]);
    const chatHistoryOnly = useMemo(() => history.filter((q) => !q.es_practica), [history]);

    const sidebarParticles = useMemo(() => (
        Array.from({ length: 24 }).map((_, i) => ({
            left: 4 + Math.random() * 90,
            top: 4 + Math.random() * 90,
            size: 3 + Math.random() * 6,
            opacity: 0.22 + Math.random() * 0.28,
            duration: 3.1 + Math.random() * 2.4,
            delay: Math.random() * 2.2,
            driftX: -18 + Math.random() * 36,
            driftY: -22 + Math.random() * 44,
            glow: i % 2 === 0,
        }))
    ), []);

    const bottomRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const historyStorageKey = useMemo(
        () => getStudentHistoryStorageKey(student?.nombre, student?.programa),
        [student?.nombre, student?.programa]
    );
    const studyFoldersStorageKey = useMemo(
        () => getStudentStudyFoldersKey(student?.nombre, student?.programa),
        [student?.nombre, student?.programa]
    );
    const studyFolderMapStorageKey = useMemo(
        () => getStudentStudyFolderMapKey(student?.nombre, student?.programa),
        [student?.nombre, student?.programa]
    );
    const studyFolderChatsStorageKey = useMemo(
        () => getStudentStudyFolderChatsKey(student?.nombre, student?.programa),
        [student?.nombre, student?.programa]
    );

    const visibleHistory = useMemo(() => {
        const cutoffFiltered = chatHistoryOnly.filter((q) => {
            const created = new Date(q.created_at).getTime();
            if (!Number.isFinite(created)) return false;
            if (!historyVisualCutoffMs) return true;
            return created >= historyVisualCutoffMs;
        });
        if (selectedHistoryFolderId === 'all') return cutoffFiltered;
        if (selectedHistoryFolderId === 'unassigned') {
            return cutoffFiltered.filter((q) => !historyFolderMap[String(q.id)]);
        }
        return cutoffFiltered.filter((q) => historyFolderMap[String(q.id)] === selectedHistoryFolderId);
    }, [chatHistoryOnly, historyVisualCutoffMs, selectedHistoryFolderId, historyFolderMap]);

    const historyGroups = useMemo(() => groupHistoryByDate(visibleHistory), [visibleHistory]);

    const workspaceFolderChats = useMemo(() => {
        if (!activeWorkspaceFolderId) return [];
        return folderChats
            .filter((c) => c.folderId === activeWorkspaceFolderId)
            .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    }, [folderChats, activeWorkspaceFolderId]);

    const getFolderNameById = (folderId?: string) => {
        if (!folderId) return 'Sin carpeta';
        return studyFolders.find((f) => f.id === folderId)?.name || 'Sin carpeta';
    };

    const { setMood } = useVisualMood();

    useGsapPageMotion(pageRef);

    // Set visual mood to authenticated on mount, reset on unmount
    useEffect(() => {
        setMood('authenticated');
        return () => setMood('idle');
    }, [setMood]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    useEffect(() => {
        queriesAPI.history().then(r => setHistory(r.data)).catch(() => {
            toast.error('No se pudo cargar el historial');
        });
    }, []);

    useEffect(() => {
        return () => {
            if (practiceNavTimerRef.current !== null) {
                window.clearTimeout(practiceNavTimerRef.current);
            }
        };
    }, []);

    useEffect(() => {
        const raw = localStorage.getItem(historyStorageKey);
        if (!raw) {
            setHistoryVisualCutoffMs(null);
            return;
        }
        const parsed = Number(raw);
        setHistoryVisualCutoffMs(Number.isFinite(parsed) ? parsed : null);
    }, [historyStorageKey]);

    useEffect(() => {
        loadedFoldersKeyRef.current = null;
        skipNextFoldersPersistRef.current = true;
        const raw = localStorage.getItem(studyFoldersStorageKey);
        if (!raw) {
            setStudyFolders([]);
            loadedFoldersKeyRef.current = studyFoldersStorageKey;
            return;
        }
        try {
            const parsed = JSON.parse(raw) as StudyFolder[];
            setStudyFolders(Array.isArray(parsed) ? parsed : []);
        } catch {
            setStudyFolders([]);
        }
        loadedFoldersKeyRef.current = studyFoldersStorageKey;
    }, [studyFoldersStorageKey]);

    useEffect(() => {
        loadedFolderMapKeyRef.current = null;
        skipNextFolderMapPersistRef.current = true;
        const raw = localStorage.getItem(studyFolderMapStorageKey);
        if (!raw) {
            setHistoryFolderMap({});
            loadedFolderMapKeyRef.current = studyFolderMapStorageKey;
            return;
        }
        try {
            const parsed = JSON.parse(raw) as Record<string, string>;
            setHistoryFolderMap(parsed && typeof parsed === 'object' ? parsed : {});
        } catch {
            setHistoryFolderMap({});
        }
        loadedFolderMapKeyRef.current = studyFolderMapStorageKey;
    }, [studyFolderMapStorageKey]);

    useEffect(() => {
        loadedFolderChatsKeyRef.current = null;
        skipNextFolderChatsPersistRef.current = true;
        const raw = localStorage.getItem(studyFolderChatsStorageKey);
        if (!raw) {
            setFolderChats([]);
            loadedFolderChatsKeyRef.current = studyFolderChatsStorageKey;
            return;
        }
        try {
            const parsed = JSON.parse(raw) as StoredStudyFolderChat[];
            const hydrated = Array.isArray(parsed)
                ? parsed.map((c) => ({ ...c, messages: deserializeChatMessages(c.messages) }))
                : [];
            setFolderChats(hydrated);
        } catch {
            setFolderChats([]);
        }
        loadedFolderChatsKeyRef.current = studyFolderChatsStorageKey;
    }, [studyFolderChatsStorageKey]);

    useEffect(() => {
        if (loadedFoldersKeyRef.current !== studyFoldersStorageKey) return;
        if (skipNextFoldersPersistRef.current) {
            skipNextFoldersPersistRef.current = false;
            return;
        }
        localStorage.setItem(studyFoldersStorageKey, JSON.stringify(studyFolders));
    }, [studyFolders, studyFoldersStorageKey]);

    useEffect(() => {
        if (loadedFolderMapKeyRef.current !== studyFolderMapStorageKey) return;
        if (skipNextFolderMapPersistRef.current) {
            skipNextFolderMapPersistRef.current = false;
            return;
        }
        localStorage.setItem(studyFolderMapStorageKey, JSON.stringify(historyFolderMap));
    }, [historyFolderMap, studyFolderMapStorageKey]);

    useEffect(() => {
        if (loadedFolderChatsKeyRef.current !== studyFolderChatsStorageKey) return;
        if (skipNextFolderChatsPersistRef.current) {
            skipNextFolderChatsPersistRef.current = false;
            return;
        }
        const serializable: StoredStudyFolderChat[] = folderChats.map((c) => ({
            ...c,
            messages: serializeChatMessages(c.messages),
        }));
        localStorage.setItem(studyFolderChatsStorageKey, JSON.stringify(serializable));
    }, [folderChats, studyFolderChatsStorageKey]);

    // Only set active folder when user explicitly selects one — no auto-assignment

    useEffect(() => {
        if (!activeFolderChatId) return;
        const chat = folderChats.find((c) => c.id === activeFolderChatId);
        if (!chat) return;
        setMessages(chat.messages);
    }, [activeFolderChatId, folderChats]);

    useEffect(() => {
        if (!activeFolderChatId) return;
        const cleanMessages = messages.map(m => ({ ...m, streaming: false }));
        setFolderChats((prev) => prev.map((chat) => {
            if (chat.id !== activeFolderChatId) return chat;
            if (chat.messages === cleanMessages) return chat;
            return {
                ...chat,
                messages: cleanMessages,
                updatedAt: new Date().toISOString(),
                title: deriveChatTitle(cleanMessages),
            };
        }));
    }, [messages, activeFolderChatId]);

    const clearHistoryVisualOnly = () => {
        const cutoff = Date.now();
        setHistoryVisualCutoffMs(cutoff);
        localStorage.setItem(historyStorageKey, String(cutoff));
        setMessages([buildWelcomeMessage(student?.nombre)]);
    };

    const createChatInFolder = (folderId: string) => {
        const now = new Date().toISOString();
        const chatId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const welcome = [buildWelcomeMessage(student?.nombre)];
        const newChat: StudyFolderChat = {
            id: chatId,
            folderId,
            title: 'Nuevo chat',
            createdAt: now,
            updatedAt: now,
            messages: welcome,
        };
        setFolderChats((prev) => [newChat, ...prev]);
        setActiveWorkspaceFolderId(folderId);
        setActiveFolderChatId(chatId);
        setMessages(welcome);
        setInput('');
    };

    const openFolderChat = (chatId: string) => {
        const target = folderChats.find((c) => c.id === chatId);
        if (!target) return;
        setActiveWorkspaceFolderId(target.folderId);
        setActiveFolderChatId(chatId);
        setMessages(target.messages);
        setInput('');
    };

    const startNewChat = () => {
        if (activeWorkspaceFolderId) {
            createChatInFolder(activeWorkspaceFolderId);
            return;
        }
        setActiveFolderChatId(null);
        setMessages([buildWelcomeMessage(student?.nombre)]);
        setInput('');
        inputRef.current?.focus();
    };

    const createStudyFolder = () => {
        const name = folderDraft.trim();
        if (!name) return;
        const folder: StudyFolder = {
            id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            name,
            createdAt: new Date().toISOString(),
        };
        setStudyFolders((prev) => [folder, ...prev]);
        setFolderDraft('');
        setActiveWorkspaceFolderId(folder.id);
        setSelectedHistoryFolderId(folder.id);
    };

    const deleteFolderChat = (chatId: string) => {
        setFolderChats((prev) => prev.filter((c) => c.id !== chatId));
        if (activeFolderChatId === chatId) {
            setActiveFolderChatId(null);
            setMessages([buildWelcomeMessage(student?.nombre)]);
        }
    };

    const deleteStudyFolder = (folderId: string) => {
        setStudyFolders((prev) => prev.filter((f) => f.id !== folderId));
        setFolderChats((prev) => prev.filter((c) => c.folderId !== folderId));
        setHistoryFolderMap((prev) => {
            const next: Record<string, string> = {};
            Object.entries(prev).forEach(([k, v]) => {
                if (v !== folderId) next[k] = v;
            });
            return next;
        });

        if (activeWorkspaceFolderId === folderId) {
            setActiveWorkspaceFolderId(null);
            setActiveFolderChatId(null);
            setMessages([buildWelcomeMessage(student?.nombre)]);
        }
        if (selectedHistoryFolderId === folderId) {
            setSelectedHistoryFolderId('all');
        }
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const pregunta = input.trim();
        const programa = student?.programa || 'General';
        const nombre = student?.nombre?.split(' ')[0] || '';
        const historial = messages
            .filter(m => !m.streaming && m.id !== 'welcome')
            .slice(-6)
            .map(m => ({ role: m.role, content: m.content }));

        setInput('');
        setLoading(true);
        setMood('processing');

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: pregunta,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, userMsg]);

        const aiMsgId = Date.now().toString() + '_ai';
        setMessages(prev => [...prev, {
            id: aiMsgId,
            role: 'assistant',
            content: '',
            timestamp: new Date(),
            rated: null,
            streaming: true,
        }]);

        let fullText = '';
        let fuentes: string[] = [];

        abortRef.current?.abort();
        const controller = new AbortController();
        abortRef.current = controller;
        const timeoutId = setTimeout(() => controller.abort(), 45000);

        try {
            const AI_URL = import.meta.env.VITE_AI_URL ?? 'http://127.0.0.1:8000';
            const res = await fetch(`${AI_URL}/consultar/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pregunta, programa, nombre_estudiante: nombre, historial }),
                signal: controller.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const reader = res.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const processSseLine = (line: string): boolean => {
                if (!line.startsWith('data: ')) return false;
                const raw = line.slice(6).trim();
                if (raw === '[DONE]') return true;

                try {
                    const parsed = JSON.parse(raw);
                    if (parsed.fuentes) {
                        fuentes = parsed.fuentes;
                    } else if (parsed.chunk) {
                        fullText += parsed.chunk;
                        setMessages(prev => prev.map(m =>
                            m.id === aiMsgId ? { ...m, content: fullText } : m
                        ));
                    } else if (parsed.error) {
                        fullText = fullText || 'No pude obtener respuesta. Intenta de nuevo.';
                    }
                } catch {
                    // Ignorar eventos parciales.
                }

                return false;
            };

            outer: while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    // Procesar cualquier remanente para no perder el último chunk.
                    if (buffer.trim()) {
                        const pending = buffer.split('\n').map(l => l.trim()).filter(Boolean);
                        for (const line of pending) {
                            if (processSseLine(line)) break;
                        }
                    }
                    break;
                }
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() ?? '';
                for (const line of lines) {
                    if (processSseLine(line.trim())) { reader.cancel(); break outer; }
                }
            }
        } catch (err: any) {
            if (err?.name === 'AbortError') {
                fullText = fullText || 'La conexión se interrumpió. Intenta de nuevo.';
            } else {
                fullText = fullText || 'Hubo un problema al procesar tu pregunta. Intenta de nuevo.';
            }
        } finally {
            clearTimeout(timeoutId);
            if (abortRef.current === controller) abortRef.current = null;
        }

        let queryId: number | undefined;
        if (fullText) {
            try {
                const saveRes = await queriesAPI.save({
                    programa,
                    pregunta,
                    respuesta: fullText,
                    tiempo_respuesta_ms: 0,
                });
                queryId = saveRes.data.id;
                setHistory(prev => [{
                    id: saveRes.data.id,
                    pregunta,
                    respuesta: fullText,
                    competencia: saveRes.data.competencia,
                    calificacion: null,
                    created_at: saveRes.data.created_at ?? new Date().toISOString(),
                }, ...prev].slice(0, 80));

                if (activeWorkspaceFolderId) {
                    setHistoryFolderMap((prev) => ({ ...prev, [String(saveRes.data.id)]: activeWorkspaceFolderId }));
                }
            } catch {
                toast.error('No se pudo guardar la consulta');
            }
        }

        setMessages(prev => prev.map(m =>
            m.id === aiMsgId
                ? { ...m, content: fullText, sources: fuentes, streaming: false, rated: null, queryId, guideImageLoading: !!fullText }
                : m
        ));

        if (fullText) {
            aiAPI.guiaImagen({ pregunta, respuesta: fullText, programa })
                .then((r) => {
                    const imageDataUrl = r.data?.image_data_url;
                    const caption = r.data?.caption;
                    const imageModel = r.data?.image_model_used;
                    const imageError = r.data?.image_error;
                    const latexFormula = r.data?.latex_formula;
                    const latexExplanation = r.data?.latex_explanation;
                    const guideTitle = r.data?.guide_title;
                    const guideSteps = Array.isArray(r.data?.guide_steps) ? r.data.guide_steps : [];
                    setMessages(prev => prev.map(m =>
                        m.id === aiMsgId
                            ? {
                                ...m,
                                guideImageLoading: false,
                                guideImageUrl: imageDataUrl || undefined,
                                guideImageCaption: caption || undefined,
                                guideImageModel: imageModel || undefined,
                                guideImageError: imageError || undefined,
                                latexFormula: latexFormula || undefined,
                                latexExplanation: latexExplanation || undefined,
                                guideTitle: guideTitle || undefined,
                                guideSteps: guideSteps.length ? guideSteps : undefined,
                            }
                            : m
                    ));
                    // Persistir datos visuales en el backend
                    if (queryId) {
                        const visual = JSON.stringify({
                            guideImageUrl: imageDataUrl, guideImageCaption: caption,
                            guideImageModel: imageModel, guideImageError: imageError,
                            latexFormula, latexExplanation, guideTitle, guideSteps,
                        });
                        queriesAPI.updateVisual(queryId, visual).catch(() => {});
                    }
                })
                .catch(() => {
                    setMessages(prev => prev.map(m =>
                        m.id === aiMsgId ? { ...m, guideImageLoading: false } : m
                    ));
                });
        }

        setLoading(false);
        setMood('authenticated');
        inputRef.current?.focus();
    };

    const handleRate = async (queryId: number, util: boolean) => {
        await queriesAPI.rate(queryId, util).catch(() => {
            toast.error('No se pudo guardar la calificación');
        });
        setMessages(prev => prev.map(m =>
            m.queryId === queryId ? { ...m, rated: util } : m
        ));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleQuickPrompt = (text: string) => {
        setInput(text);
        inputRef.current?.focus();
    };

    const handleGoPractice = () => {
        if (practiceTransitioning) return;
        setPracticeTransitioning(true);
        practiceNavTimerRef.current = window.setTimeout(() => {
            navigate('/practica');
        }, 2000);
    };

    return (
        <div id="chat-root" ref={pageRef} style={{
            position: 'fixed',
            inset: 0,
            display: 'grid',
            gridTemplateColumns: '320px 1fr',
            background: 'transparent',
            overflow: 'hidden',
        }}>
            {!isDesktop && sidebarOpen && (
                <div style={{ position: 'fixed', inset: 0, zIndex: 99, background: 'rgba(0,0,0,0.45)' }} onClick={() => setSidebarOpen(false)} />
            )}
            <aside data-motion="panel" className="glass-panel" style={{
                background: 'var(--surface)',
                color: 'var(--text)',
                padding: '20px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                borderRight: '1px solid var(--border)',
                overflow: 'hidden',
                ...(isDesktop
                    ? { position: 'relative', zIndex: 1 }
                    : { position: 'fixed', zIndex: 100, left: 0, top: 0, bottom: 0, width: 280, transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)', transition: 'transform 0.25s ease' }
                ),
            }}>
                <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
                    {sidebarParticles.map((p, i) => (
                        <span
                            key={`sidebar-particle-${i}`}
                            style={{
                                position: 'absolute',
                                left: `${p.left}%`,
                                top: `${p.top}%`,
                                width: `${p.size}px`,
                                height: `${p.size}px`,
                                borderRadius: '999px',
                                opacity: p.opacity,
                                background: p.glow ? 'rgba(165, 217, 248, 0.72)' : 'rgba(166, 216, 193, 0.68)',
                                boxShadow: p.glow ? '0 0 9px rgba(138, 201, 241, 0.36)' : '0 0 9px rgba(143, 221, 185, 0.32)',
                                animation: `sidebar-particle-float ${p.duration}s ease-in-out ${p.delay}s infinite alternate`,
                                ['--driftX' as any]: `${p.driftX}px`,
                                ['--driftY' as any]: `${p.driftY}px`,
                            }}
                        />
                    ))}
                </div>

                <div style={{ position: 'relative', zIndex: 2, display: 'flex', flexDirection: 'column', gap: '16px', minHeight: '100%' }}>
                <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '14px', textAlign: 'center' }}>
                    <div style={{
                        marginBottom: '12px',
                        display: 'flex',
                        justifyContent: 'center',
                        position: 'relative',
                    }}>
                        <InstitutionalLogo size={96} />
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-hint)' }}>ASCENSO PRO</p>
                    <h2 style={{ fontSize: '22px', fontFamily: 'var(--font-heading)', color: 'var(--text)' }}>Sala de Estudio</h2>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{student?.nombre}</p>
                </div>

                <button onClick={handleGoPractice} className="btn" disabled={practiceTransitioning} style={{
                    width: '100%', justifyContent: 'space-between', height: '44px',
                    background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)',
                    opacity: practiceTransitioning ? 0.75 : 1,
                }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Barbell size={16} weight="duotone" /> Ir a práctica</span>
                    <ChevronDown size={14} style={{ transform: 'rotate(-90deg)' }} />
                </button>

                <div style={{
                    background: 'color-mix(in srgb, var(--surface) 40%, transparent)', border: '1px solid var(--border)',
                    borderRadius: '12px', padding: '10px', maxHeight: '245px', overflowY: 'auto'
                }}>
                    <p style={{
                        display: 'flex', alignItems: 'center', gap: '8px',
                        fontSize: '12px', fontWeight: 700, color: 'var(--text)', marginBottom: '8px'
                    }}>
                        <FolderPlus size={15} /> Carpetas de estudio
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '6px', marginBottom: '8px' }}>
                        <input
                            value={folderDraft}
                            onChange={(e) => setFolderDraft(e.target.value)}
                            placeholder="Nueva carpeta"
                            style={{
                                height: '30px',
                                borderRadius: '8px',
                                border: '1px solid rgba(255,255,255,0.2)',
                                background: 'rgba(255,255,255,0.08)',
                                color: '#eaf1f5',
                                padding: '0 8px',
                                fontSize: '11px',
                            }}
                        />
                        <button
                            onClick={createStudyFolder}
                            style={{
                                height: '30px',
                                borderRadius: '8px',
                                border: '1px solid var(--border)',
                                background: 'var(--surface)',
                                color: 'var(--text)',
                                padding: '0 8px',
                                fontSize: '11px',
                                fontWeight: 700,
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                                cursor: 'pointer',
                            }}
                        >
                            <Plus size={12} /> Crear
                        </button>
                    </div>

                    <div style={{ display: 'grid', gap: '6px' }}>
                        {studyFolders.length === 0 && (
                            <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)' }}>Crea una carpeta para iniciar chats temáticos.</p>
                        )}
                        {studyFolders.map((folder) => (
                            <div key={folder.id} style={{
                                border: activeWorkspaceFolderId === folder.id ? '1px solid var(--primary)' : '1px solid var(--border)',
                                background: activeWorkspaceFolderId === folder.id ? 'color-mix(in srgb, var(--primary) 16%, transparent)' : 'var(--surface)',
                                borderRadius: '8px',
                                padding: '6px',
                                display: 'grid',
                                gap: '6px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                    <button
                                        onClick={() => { setActiveWorkspaceFolderId(folder.id); setSelectedHistoryFolderId(folder.id); }}
                                        style={{
                                            flex: 1,
                                            textAlign: 'left',
                                            border: 'none',
                                            background: 'transparent',
                                            color: 'var(--text)',
                                            fontSize: '11px',
                                            fontWeight: 700,
                                            cursor: 'pointer',
                                            padding: 0,
                                        }}
                                    >
                                        {folder.name}
                                    </button>
                                    <button
                                        onClick={() => deleteStudyFolder(folder.id)}
                                        title="Eliminar carpeta"
                                        style={{
                                            height: '24px',
                                            width: '24px',
                                            borderRadius: '6px',
                                            border: '1px solid var(--border)',
                                            background: 'var(--surface)',
                                            color: 'var(--danger)',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        <Trash2 size={11} />
                                    </button>
                                    <button
                                        onClick={() => createChatInFolder(folder.id)}
                                        style={{
                                            height: '24px',
                                            borderRadius: '6px',
                                            border: '1px solid var(--border)',
                                            background: 'var(--surface)',
                                            color: 'var(--text)',
                                            padding: '0 6px',
                                            fontSize: '10px',
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '4px',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        <MessageSquarePlus size={11} /> Chat
                                    </button>
                                </div>

                                {activeWorkspaceFolderId === folder.id && (
                                    <div style={{ display: 'grid', gap: '4px' }}>
                                        {workspaceFolderChats.filter((c) => c.folderId === folder.id).length === 0 && (
                                            <p style={{ margin: 0, fontSize: '10px', color: 'rgba(214, 227, 236, 0.68)' }}>Sin chats en esta carpeta.</p>
                                        )}
                                        {workspaceFolderChats.filter((c) => c.folderId === folder.id).map((chat) => (
                                            <div key={chat.id} style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                                                <button
                                                    onClick={() => openFolderChat(chat.id)}
                                                    style={{
                                                        flex: 1,
                                                        textAlign: 'left',
                                                        borderRadius: '6px',
                                                        border: activeFolderChatId === chat.id ? '1px solid rgba(148, 211, 255, 0.6)' : '1px solid rgba(255,255,255,0.16)',
                                                        background: activeFolderChatId === chat.id ? 'rgba(148, 211, 255, 0.14)' : 'rgba(255,255,255,0.06)',
                                                        color: '#dce8f0',
                                                        fontSize: '10px',
                                                        padding: '5px 6px',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    {chat.title}
                                                </button>
                                                <button
                                                    onClick={() => deleteFolderChat(chat.id)}
                                                    title="Eliminar chat"
                                                    style={{
                                                        height: '24px',
                                                        width: '24px',
                                                        borderRadius: '6px',
                                                        border: '1px solid rgba(255,255,255,0.2)',
                                                        background: 'rgba(255,255,255,0.08)',
                                                        color: '#ffb8b8',
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        cursor: 'pointer',
                                                    }}
                                                >
                                                    <Trash2 size={11} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div style={{
                    background: 'color-mix(in srgb, var(--surface) 40%, transparent)', border: '1px solid var(--border)',
                    borderRadius: '12px', padding: '10px', maxHeight: '280px', overflowY: 'auto'
                }}>
                    <p style={{
                        display: 'flex', alignItems: 'center', gap: '8px',
                        fontSize: '12px', fontWeight: 700, color: 'var(--text)', marginBottom: '8px'
                    }}>
                        <ClockCounterClockwise size={16} weight="duotone" /> Historial
                    </p>
                    <div style={{ display: 'grid', gap: '8px', marginBottom: '8px' }}>
                        <button
                            onClick={clearHistoryVisualOnly}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '6px',
                                height: '30px',
                                borderRadius: '8px',
                                border: '1px solid var(--border)',
                                background: 'var(--surface)',
                                color: 'var(--text-muted)',
                                fontSize: '11px',
                                fontWeight: 700,
                                cursor: 'pointer',
                            }}
                            title="Oculta el historial solo para tu vista. No elimina datos del sistema"
                        >
                            <Trash2 size={12} /> Limpiar vista
                        </button>
                        <div style={{
                            display: 'flex',
                            gap: '6px',
                            overflowX: 'auto',
                            paddingBottom: '2px',
                            scrollbarWidth: 'thin',
                        }}>
                            {[
                                { id: 'all', label: 'Todo' },
                                { id: 'unassigned', label: 'Sin carpeta' },
                                ...studyFolders.map((f) => ({ id: f.id, label: f.name })),
                            ].map((opt) => {
                                const active = selectedHistoryFolderId === opt.id;
                                return (
                                    <button
                                        key={opt.id}
                                        className={`history-filter-chip ${active ? 'active' : ''}`}
                                        onClick={() => setSelectedHistoryFolderId(opt.id)}
                                        style={{
                                            flexShrink: 0,
                                            height: '30px',
                                            borderRadius: '999px',
                                            border: active ? '1px solid var(--primary)' : '1px solid var(--border)',
                                            background: active
                                                ? 'color-mix(in srgb, var(--primary) 20%, transparent)'
                                                : 'var(--surface)',
                                            color: active ? 'var(--text)' : 'var(--text-muted)',
                                            padding: '0 10px',
                                            fontSize: '11px',
                                            fontWeight: active ? 700 : 600,
                                            cursor: 'pointer',
                                            boxShadow: active ? '0 6px 14px rgba(84, 150, 194, 0.24)' : 'none',
                                            whiteSpace: 'nowrap',
                                            transition: 'transform 180ms ease, box-shadow 180ms ease, filter 180ms ease',
                                        }}
                                        title={opt.label}
                                    >
                                        {opt.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                    {visibleHistory.length === 0
                        ? <p style={{ fontSize: '12px', opacity: 0.8, textAlign: 'center', padding: '8px', color: 'var(--text-muted)' }}>Sin historial</p>
                        : historyGroups.map(group => (
                            <div key={group.key} style={{ marginBottom: '8px' }}>
                                <p style={{
                                    margin: '6px 0 4px',
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    letterSpacing: '0.03em',
                                    textTransform: 'uppercase',
                                    color: 'var(--text-hint)',
                                }}>
                                    {group.label}
                                </p>
                                {group.items.map((q, idx) => {
                                    const isLast = idx === group.items.length - 1;
                                    const createdAt = new Date(q.created_at);
                                    const timeLabel = group.key === 'anteriores'
                                        ? createdAt.toLocaleString('es-CO', {
                                            day: '2-digit',
                                            month: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        }).replace(',', ' ·')
                                        : createdAt.toLocaleTimeString('es-CO', {
                                            hour: '2-digit',
                                            minute: '2-digit',
                                        });
                                    return (
                                        <div
                                            key={`${group.key}-${q.id}-${idx}`}
                                            style={{
                                                padding: '8px',
                                                borderBottom: isLast ? 'none' : '1px solid var(--border)',
                                                cursor: 'pointer',
                                            }}
                                            onClick={() => {
                                                const stamp = `${q.id}_${Date.now()}`;
                                                let visual = {};
                                                try {
                                                    if (q.respuesta_visual) {
                                                        const v = JSON.parse(q.respuesta_visual);
                                                        visual = {
                                                            guideImageUrl: v.guideImageUrl || undefined,
                                                            guideImageCaption: v.guideImageCaption || undefined,
                                                            guideImageModel: v.guideImageModel || undefined,
                                                            guideImageError: v.guideImageError || undefined,
                                                            latexFormula: v.latexFormula || undefined,
                                                            latexExplanation: v.latexExplanation || undefined,
                                                            guideTitle: v.guideTitle || undefined,
                                                            guideSteps: v.guideSteps || undefined,
                                                        };
                                                    }
                                                } catch {}
                                                setMessages(prev => [
                                                    ...prev,
                                                    { id: `${stamp}_q`, role: 'user', content: q.pregunta, timestamp: new Date(q.created_at) },
                                                    { id: `${stamp}_a`, role: 'assistant', content: q.respuesta, timestamp: new Date(q.created_at), rated: q.calificacion, queryId: q.id, ...visual },
                                                ]);
                                            }}
                                        >
                                            <p style={{ fontSize: '12px', color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.pregunta}</p>
                                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px' }}>
                                                <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: 0 }}>{timeLabel}</p>
                                                <span
                                                    style={{
                                                        marginLeft: 'auto',
                                                        height: '20px',
                                                        borderRadius: '6px',
                                                        border: '1px solid var(--border)',
                                                        background: 'var(--surface)',
                                                        color: 'var(--text-muted)',
                                                        fontSize: '10px',
                                                        padding: '0 6px',
                                                        display: 'inline-flex',
                                                        alignItems: 'center',
                                                    }}
                                                >
                                                    {getFolderNameById(historyFolderMap[String(q.id)])}
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ))}
                </div>

                <div style={{ marginTop: 'auto', display: 'flex', gap: '8px' }}>
                    <button className="btn-icon" onClick={toggleTheme} aria-label="Cambiar tema" style={{ flex: 1, width: 'auto', height: '38px', color: 'var(--text)', borderColor: 'var(--border)', background: 'var(--surface)' }}>
                        {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                    </button>
                    <button className="btn-icon" onClick={() => { logout(); navigate('/login'); }} aria-label="Cerrar sesión" style={{ flex: 1, width: 'auto', height: '38px', color: 'var(--danger)', borderColor: 'var(--border)', background: 'var(--surface)' }}>
                        <LogOut size={15} />
                    </button>
                </div>
                </div>
            </aside>

            <main data-motion="headline" style={{ position: 'relative', minWidth: 0, minHeight: 0, overflow: 'hidden' }}>
                <header data-motion="panel" className="chat-header" style={{
                    height: '72px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0 24px',
                    borderBottom: '1px solid var(--border)',
                    background: 'color-mix(in srgb, var(--surface) 80%, transparent)',
                    backdropFilter: 'blur(8px)',
                }}>
                    <div>
                        <h2 style={{ fontSize: '18px', fontFamily: 'var(--font-heading)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {!isDesktop && (
                                <button className="btn-icon" onClick={() => setSidebarOpen(!sidebarOpen)} aria-label="Menú" style={{ width: '36px', height: '36px', borderColor: 'var(--border)', background: 'var(--surface)', flexShrink: 0 }}>
                                    {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
                                </button>
                            )}
                            <Brain size={15} color="#3e6f62" /> Chat de Aprendizaje
                        </h2>
                        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{student?.programa} · Modo motivación ON</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                            className="btn"
                            onClick={startNewChat}
                            style={{
                                height: '30px',
                                padding: '0 10px',
                                fontSize: '12px',
                                borderRadius: '999px',
                                background: 'var(--surface)',
                                border: '1px solid var(--border)',
                                color: 'var(--text)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}
                        >
                            <MessageSquarePlus size={13} /> Nuevo chat
                        </button>
                        <span className="badge badge-accent" style={{ fontSize: '12px', boxShadow: '0 6px 14px rgba(46,126,93,0.24)' }}>En línea</span>
                    </div>
                </header>

                <div data-motion="panel" className="chat-messages" style={{
                    position: 'absolute',
                    top: 72,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    overflowY: 'auto',
                    padding: '24px 24px 160px 24px',
                }}>
                    <div style={{ maxWidth: '980px', margin: '0 auto' }}>
                        {messages.length <= 1 && (
                            <div className="chat-quick-prompts animate-fade-up" style={{
                                marginBottom: '16px',
                                display: 'grid',
                                gap: '8px',
                            }}>
                                <p style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 600 }}>Arranca con una de estas:</p>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                    {quickPrompts.map((qp) => (
                                        <button
                                            key={qp}
                                            onClick={() => handleQuickPrompt(qp)}
                                            style={{
                                                padding: '8px 12px',
                                                borderRadius: '999px',
                                                border: '1px solid var(--border)',
                                                background: 'var(--surface)',
                                                fontSize: '12px',
                                                color: 'var(--text)',
                                                transition: 'var(--t-fast)',
                                            }}
                                            onMouseOver={e => {
                                                e.currentTarget.style.transform = 'translateY(-1px)';
                                                e.currentTarget.style.boxShadow = '0 8px 16px rgba(61,108,140,0.18)';
                                            }}
                                            onMouseOut={e => {
                                                e.currentTarget.style.transform = 'translateY(0)';
                                                e.currentTarget.style.boxShadow = 'none';
                                            }}
                                        >
                                            {qp}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        {messages.map(msg => (
                            <MessageBubble key={msg.id} msg={msg} onRate={handleRate} />
                        ))}
                        <div ref={bottomRef} />
                    </div>
                </div>

                <div data-motion="panel" className="chat-input-area" style={{
                    position: 'absolute',
                    left: '24px',
                    right: '24px',
                    bottom: '20px',
                    background: 'color-mix(in srgb, var(--surface) 90%, transparent)',
                    border: '1px solid var(--border)',
                    borderRadius: '18px',
                    boxShadow: '0 14px 30px rgba(0,0,0,0.14)',
                    backdropFilter: 'blur(10px)',
                    padding: '10px 10px 12px 14px',
                }}>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
                        <textarea
                            ref={inputRef}
                            className="input"
                            style={{
                                flex: 1,
                                border: 'none',
                                background: 'transparent',
                                resize: 'none',
                                minHeight: '24px',
                                maxHeight: '120px',
                                padding: 0,
                                boxShadow: 'none',
                                fontSize: '15px',
                                lineHeight: '1.5',
                            }}
                            placeholder="Escribe tu pregunta..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            rows={1}
                            disabled={loading}
                        />
                        <button className="btn btn-primary" onClick={handleSend} disabled={!input.trim() || loading} style={{ height: '38px', padding: '0 16px', flexShrink: 0 }} aria-label="Enviar pregunta">
                            {loading ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={16} />}
                        </button>
                    </div>
                    <p style={{ fontSize: '11px', color: 'var(--text-hint)', marginTop: '8px', textAlign: 'center' }}>Enter para enviar · Shift+Enter nueva línea</p>
                </div>
            </main>

            {practiceTransitioning && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 120,
                    display: 'grid',
                    placeItems: 'center',
                    background: 'radial-gradient(circle at 22% 24%, rgba(108,153,189,0.34), transparent 44%), radial-gradient(circle at 78% 78%, rgba(113,173,144,0.3), transparent 46%), linear-gradient(145deg, rgba(19,35,47,0.92), rgba(27,47,61,0.9))',
                    backdropFilter: 'blur(4px)',
                    animation: 'practice-transition-fade 2000ms ease forwards',
                }}>
                    <div style={{ textAlign: 'center', color: '#eaf4fb', padding: '16px', position: 'relative' }}>
                        <div style={{
                            width: '88px',
                            height: '88px',
                            margin: '0 auto 14px',
                            borderRadius: '999px',
                            border: '1px solid rgba(255,255,255,0.28)',
                            display: 'grid',
                            placeItems: 'center',
                            background: 'linear-gradient(150deg, rgba(255,255,255,0.16), rgba(177,225,255,0.1))',
                            boxShadow: '0 16px 30px rgba(0,0,0,0.28)',
                        }}>
                            <div style={{ position: 'relative', width: '52px', height: '52px', display: 'grid', placeItems: 'center' }}>
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <span
                                        key={`practice-loader-particle-${i}`}
                                        style={{
                                            position: 'absolute',
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '999px',
                                            background: i % 2 === 0 ? 'rgba(146, 200, 236, 0.88)' : 'rgba(147, 221, 185, 0.84)',
                                            boxShadow: '0 0 8px rgba(255,255,255,0.35)',
                                            animation: `practice-loader-orbit ${1.8 + i * 0.12}s linear ${i * 0.14}s infinite`,
                                        }}
                                    />
                                ))}
                                <span style={{
                                    position: 'absolute',
                                    inset: 0,
                                    borderRadius: '999px',
                                    border: '2px solid rgba(143, 194, 230, 0.28)',
                                    borderTopColor: '#8fbde0',
                                    animation: 'practice-loader-ring 1s linear infinite',
                                }} />
                                <span style={{
                                    position: 'absolute',
                                    inset: '7px',
                                    borderRadius: '999px',
                                    border: '2px solid rgba(146, 212, 184, 0.28)',
                                    borderBottomColor: '#8fd2b8',
                                    animation: 'practice-loader-ring-rev 1.25s linear infinite',
                                }} />
                                <Loader2 size={18} style={{ color: '#def1ff', animation: 'spin 1.3s linear infinite' }} />
                            </div>
                        </div>
                        <h3 style={{ margin: 0, fontSize: '28px', fontFamily: 'var(--font-heading)' }}>Entrando a práctica</h3>
                        <p style={{ margin: '8px 0 0', fontSize: '14px', opacity: 0.9 }}>Preparamos tu sesion de entrenamiento...</p>

                        <div style={{
                            margin: '16px auto 0',
                            width: '260px',
                            height: '5px',
                            borderRadius: '999px',
                            background: 'rgba(255,255,255,0.2)',
                            overflow: 'hidden',
                            border: '1px solid rgba(255,255,255,0.24)',
                        }}>
                            <span style={{
                                display: 'block',
                                height: '100%',
                                width: '100%',
                                borderRadius: '999px',
                                background: 'linear-gradient(90deg, #90c3eb, #8ed8bd)',
                                transformOrigin: 'left center',
                                animation: 'practice-transition-progress 2000ms linear forwards',
                            }} />
                        </div>
                    </div>

                    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
                        {Array.from({ length: 16 }).map((_, i) => (
                            <span
                                key={`practice-transition-particle-${i}`}
                                style={{
                                    position: 'absolute',
                                    left: `${6 + ((i * 6.1) % 88)}%`,
                                    top: `${8 + ((i * 7.7) % 82)}%`,
                                    width: `${6 + (i % 4) * 2}px`,
                                    height: `${6 + (i % 4) * 2}px`,
                                    borderRadius: '999px',
                                    background: i % 2 === 0 ? 'rgba(147,206,245,0.74)' : 'rgba(145,218,184,0.68)',
                                    boxShadow: i % 2 === 0 ? '0 0 14px rgba(121,189,235,0.55)' : '0 0 14px rgba(131,219,180,0.52)',
                                    animation: `practice-transition-particles ${1.6 + (i % 5) * 0.2}s ease-in-out ${i * 0.09}s infinite alternate`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            )}

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
                @keyframes guide-shimmer {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }
                @keyframes sidebar-particle-float {
                    0% {
                        transform: translate3d(0, 0, 0) scale(0.92);
                        opacity: 0.2;
                    }
                    50% {
                        transform: translate3d(calc(var(--driftX) * 0.95), calc(var(--driftY) * -0.6), 0) scale(1.14);
                        opacity: 0.46;
                    }
                    100% {
                        transform: translate3d(calc(var(--driftX) * -1.05), calc(var(--driftY) * 0.92), 0) scale(0.98);
                        opacity: 0.26;
                    }
                }
                @keyframes practice-transition-fade {
                    0% { opacity: 0; }
                    12% { opacity: 1; }
                    88% { opacity: 1; }
                    100% { opacity: 0.94; }
                }
                @keyframes practice-loader-ring {
                    to { transform: rotate(360deg); }
                }
                @keyframes practice-loader-ring-rev {
                    to { transform: rotate(-360deg); }
                }
                @keyframes practice-loader-orbit {
                    0% {
                        transform: rotate(0deg) translateX(30px) scale(0.9);
                        opacity: 0.4;
                    }
                    50% {
                        transform: rotate(180deg) translateX(26px) scale(1.05);
                        opacity: 0.95;
                    }
                    100% {
                        transform: rotate(360deg) translateX(30px) scale(0.9);
                        opacity: 0.4;
                    }
                }
                @keyframes practice-transition-progress {
                    0% { transform: scaleX(0); }
                    100% { transform: scaleX(1); }
                }
                @keyframes practice-transition-particles {
                    0% { transform: translate3d(0, 0, 0) scale(0.88); opacity: 0.4; }
                    100% { transform: translate3d(12px, -18px, 0) scale(1.18); opacity: 1; }
                }
                @media (max-width: 768px) {
                    #chat-root { grid-template-columns: 1fr !important; }
                    .chat-header { padding: 0 12px !important; }
                    .chat-header h2 { font-size: 15px !important; }
                    .chat-header p { font-size: 11px !important; }
                    .chat-header .badge { font-size: 10px !important; }
                    .chat-header .btn { height: 26px !important; font-size: 11px !important; padding: 0 8px !important; }
                    .chat-messages { padding: 16px 12px 140px 12px !important; }
                    .chat-msg-bubble-user { max-width: 88% !important; }
                    .chat-msg-bubble-ai { max-width: 92% !important; }
                    .chat-input-area {
                        left: 8px !important;
                        right: 8px !important;
                        bottom: 8px !important;
                    }
                    .chat-input-area textarea { font-size: 14px !important; }
                    .chat-quick-prompts button { font-size: 11px !important; padding: 6px 10px !important; }
                }
                @media (max-width: 480px) {
                    .chat-header h2 { font-size: 14px !important; }
                    .chat-messages { padding: 12px 8px 130px 8px !important; }
                    .chat-msg-bubble-user { max-width: 92% !important; }
                    .chat-msg-bubble-ai { max-width: 95% !important; }
                }
                .history-filter-chip:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 8px 16px rgba(58, 113, 151, 0.24);
                    filter: saturate(1.08);
                }
                .history-filter-chip:active {
                    transform: translateY(0) scale(0.985);
                }
                .history-filter-chip.active:hover {
                    box-shadow: 0 10px 18px rgba(74, 142, 187, 0.32);
                }
            `}</style>
        </div>
    );
};
