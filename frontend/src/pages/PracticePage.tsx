import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle, XCircle, ChevronRight, RefreshCw, Trophy, BookOpen, ArrowLeft, Loader2, LayoutGrid } from 'lucide-react';
import { BookOpenText, Function, PencilLine, Translate, Scales, SuitcaseSimple } from '@phosphor-icons/react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { aiAPI, queriesAPI } from '../api/client';
import type { Pregunta } from '../types';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';
import { InstitutionalLogo } from '../components/InstitutionalLogo';
import katex from 'katex';
import 'katex/dist/katex.min.css';

const COMPETENCIAS = ['Lectura Crítica', 'Razonamiento Cuantitativo', 'Comunicación Escrita', 'Inglés', 'Ciudadanas', 'Específica'];

const COMPETENCIA_CARDS: Array<{ label: string; icon: React.ReactNode; tint: string; }> = [
    { label: 'Lectura Crítica', icon: <BookOpenText size={16} weight="duotone" />, tint: '#3f6278' },
    { label: 'Razonamiento Cuantitativo', icon: <Function size={16} weight="duotone" />, tint: '#3f6b80' },
    { label: 'Comunicación Escrita', icon: <PencilLine size={16} weight="duotone" />, tint: '#44647d' },
    { label: 'Inglés', icon: <Translate size={16} weight="duotone" />, tint: '#3f7a67' },
    { label: 'Ciudadanas', icon: <Scales size={16} weight="duotone" />, tint: '#4e6b7e' },
    { label: 'Específica', icon: <SuitcaseSimple size={16} weight="duotone" />, tint: '#4f6b5a' },
];

type TrainingLength = 'corto' | 'medio' | 'largo';

const TRAINING_LENGTH_PRESETS: Record<TrainingLength, { label: string; cantidad: number; descripcion: string }> = {
    corto: {
        label: 'Entrenamiento corto',
        cantidad: 15,
        descripcion: 'Sesion rapida para practicar conceptos clave.',
    },
    medio: {
        label: 'Entrenamiento medio',
        cantidad: 22,
        descripcion: 'Cobertura equilibrada para simulacion parcial.',
    },
    largo: {
        label: 'Entrenamiento largo',
        cantidad: 30,
        descripcion: 'Sesion extensa de preparacion tipo prueba.',
    },
};

type CompetenciaIcon = React.ComponentType<{
    size?: number;
    weight?: 'thin' | 'light' | 'regular' | 'bold' | 'fill' | 'duotone';
}>;

const getCompetenciaVisual = (label: string): { colorA: string; colorB: string; Icon: CompetenciaIcon } => {
    switch (label) {
        case 'Lectura Crítica':
            return { colorA: '#456680', colorB: '#5f8ca7', Icon: BookOpenText };
        case 'Razonamiento Cuantitativo':
            return { colorA: '#3f6f8e', colorB: '#5a90b3', Icon: Function };
        case 'Comunicación Escrita':
            return { colorA: '#4a6e88', colorB: '#6a8ea9', Icon: PencilLine };
        case 'Inglés':
            return { colorA: '#3f7a67', colorB: '#5aa188', Icon: Translate };
        case 'Ciudadanas':
            return { colorA: '#516f86', colorB: '#6f90a7', Icon: Scales };
        case 'Específica':
            return { colorA: '#4f6b5a', colorB: '#72917f', Icon: SuitcaseSimple };
        default:
            return { colorA: '#3f6278', colorB: '#6b8ea6', Icon: BookOpenText };
    }
};

const DATOS_CURIOSOS: Record<string, string[]> = {
    'Todas': [
        'Alternar tipos de preguntas mejora la retencion a largo plazo.',
        'Tu cerebro aprende mejor cuando mezclas temas en una misma sesion.',
        'Practicar con variedad reduce la fatiga y aumenta la atencion.',
    ],
    'Lectura Crítica': [
        'Leer primero la pregunta y luego el texto puede acelerar tu respuesta.',
        'Los conectores del texto suelen revelar la intencion del autor.',
        'Una inferencia valida siempre se sostiene con pistas del pasaje.',
    ],
    'Razonamiento Cuantitativo': [
        'Estimar antes de calcular ayuda a detectar errores rapido.',
        'Las unidades correctas suelen indicar si el procedimiento va bien.',
        'Traducir el problema a una ecuacion corta simplifica mucho la solucion.',
    ],
    'Comunicación Escrita': [
        'La claridad pesa mas que usar palabras complejas.',
        'Un buen conector puede mejorar toda la coherencia de un parrafo.',
        'Planear 30 segundos antes de escribir mejora la estructura final.',
    ],
    'Inglés': [
        'El contexto de la frase suele resolver vocabulario desconocido.',
        'Identificar el tiempo verbal primero reduce errores de interpretacion.',
        'Leer el titulo y subtitulos orienta mejor la comprension global.',
    ],
    'Ciudadanas': [
        'Distinguir hecho de opinion es clave en preguntas de ciudadania.',
        'Analizar actores e intereses te ayuda a elegir la mejor decision.',
        'La opcion mas etica suele equilibrar derechos y deberes colectivos.',
    ],
    'Específica': [
        'Relacionar conceptos del programa con casos reales facilita recordar.',
        'Mapear ideas clave en 3 pasos acelera la resolucion de escenarios.',
        'Las preguntas aplicadas premian comprension profunda, no memorizacion.',
    ],
};

const getFactsFallback = (competenciaLabel: string): string[] => {
    const generic = DATOS_CURIOSOS['Todas'] ?? [];
    const specific = DATOS_CURIOSOS[competenciaLabel] ?? [];
    return [...specific, ...generic].filter(Boolean);
};

const normalizeFacts = (facts: string[]): string[] => {
    const clean = facts
        .map(f => f.trim())
        .filter(Boolean);
    return Array.from(new Set(clean));
};

type PracticeSupport = {
    loading?: boolean;
    mostrar_traduccion?: boolean;
    texto_base_es?: string;
    enunciado_es?: string;
    opciones_es?: string[];
    explicacion_es?: string;
    requiere_visual?: boolean;
    visual_descripcion?: string;
    image_data_url?: string | null;
    caption?: string | null;
};

type PracticeResult = {
    competencia: string;
    correcta: boolean;
};

const hasVisualCue = (q: Pregunta | undefined): boolean => {
    if (!q) return false;
    const text = `${q.enunciado || ''} ${q.texto_base || ''}`.toLowerCase();
    return /(grafica|gr[aá]fica|graph|chart|tabla|table|figure|figura|diagrama|diagram)/i.test(text);
};

const englishTypeLabel = (value: string | undefined): string => {
    switch ((value || '').toLowerCase()) {
        case 'reading': return 'Reading';
        case 'vocabulary': return 'Vocabulary';
        case 'grammar': return 'Grammar';
        default: return 'English Skill';
    }
};

const normalizeCompKey = (value: string): string =>
    value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
        .toLowerCase();

const isEnglishComp = (value: string): boolean => /ingles/.test(normalizeCompKey(value));

const isGeneralComp = (value: string): boolean => {
    const key = normalizeCompKey(value);
    return !!key && key !== 'especifica' && key !== 'todas';
};

const inferGeneralDifficulty = (ratio: number): 'basico' | 'intermedio' | 'avanzado' => {
    if (ratio >= 0.8) return 'avanzado';
    if (ratio >= 0.55) return 'intermedio';
    return 'basico';
};

const difficultyLabel = (value: string): string => {
    switch ((value || '').toLowerCase()) {
        case 'basico': return 'Basico';
        case 'intermedio': return 'Intermedio';
        case 'avanzado': return 'Avanzado';
        default: return value;
    }
};

const LATEX_REGEX = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\))/g;

const renderTextWithLatex = (text: string): React.ReactNode => {
    const source = String(text || '');
    const parts = source.split(LATEX_REGEX).filter(Boolean);

    return parts.map((part, idx) => {
        const isDollarBlock = part.startsWith('$$') && part.endsWith('$$');
        const isBracketBlock = part.startsWith('\\[') && part.endsWith('\\]');
        const isParenInline = part.startsWith('\\(') && part.endsWith('\\)');
        const isLatex = isDollarBlock || isBracketBlock || isParenInline;

        if (!isLatex) {
            return <React.Fragment key={`txt-${idx}`}>{part}</React.Fragment>;
        }

        let expr = part;
        let displayMode = false;
        if (isDollarBlock) {
            expr = part.slice(2, -2);
            displayMode = true;
        } else if (isBracketBlock) {
            expr = part.slice(2, -2);
            displayMode = true;
        } else if (isParenInline) {
            expr = part.slice(2, -2);
            displayMode = false;
        }

        const html = katex.renderToString(expr, {
            throwOnError: false,
            displayMode,
            strict: 'ignore',
        });

        if (displayMode) {
            return <div key={`katex-${idx}`} style={{ margin: '8px 0' }} dangerouslySetInnerHTML={{ __html: html }} />;
        }

        return <span key={`katex-${idx}`} dangerouslySetInnerHTML={{ __html: html }} />;
    });
};

export const PracticePage: React.FC = () => {
    const pageRef = useRef<HTMLDivElement>(null);
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
    const [startingSession, setStartingSession] = useState(false);
    const [sessionCompetencia, setSessionCompetencia] = useState('Todas');
    const [sessionLength, setSessionLength] = useState<TrainingLength>('corto');
    const [sessionStep, setSessionStep] = useState<'intro' | 'generating' | 'ready'>('intro');
    const [sessionMessage, setSessionMessage] = useState('');
    const [sessionFact, setSessionFact] = useState('');
    const [sessionFactsPool, setSessionFactsPool] = useState<string[]>([]);
    const [sessionFactIndex, setSessionFactIndex] = useState(0);
    const startTimerRef = useRef<number | null>(null);
    const factCycleRef = useRef<number | null>(null);
    const factSwapTimeoutRef = useRef<number | null>(null);
    const factsPoolRef = useRef<string[]>([]);
    const factIndexRef = useRef(0);
    const [factVisible, setFactVisible] = useState(false);
    const [factX, setFactX] = useState(50);
    const [factY, setFactY] = useState(72);
    const [supportByQuestion, setSupportByQuestion] = useState<Record<string, PracticeSupport>>({});
    const [answerResults, setAnswerResults] = useState<Record<string, PracticeResult>>({});
    const [adaptiveTarget, setAdaptiveTarget] = useState<'A2' | 'B1' | 'basico' | 'intermedio' | 'avanzado'>('intermedio');
    const [adaptiveAnswered, setAdaptiveAnswered] = useState(0);
    const [adaptiveCorrect, setAdaptiveCorrect] = useState(0);
    const sessionQuestionCount = TRAINING_LENGTH_PRESETS[sessionLength].cantidad;
    const sessionLengthLabel = TRAINING_LENGTH_PRESETS[sessionLength].label;
    const particleConfigs = useMemo(() => (
        Array.from({ length: 18 }).map(() => ({
            left: 4 + Math.random() * 92,
            top: 8 + Math.random() * 78,
            size: 7 + Math.random() * 8,
            opacity: 0.5 + Math.random() * 0.42,
            dx1: -16 + Math.random() * 32,
            dy1: -14 + Math.random() * 28,
            dx2: -20 + Math.random() * 40,
            dy2: -18 + Math.random() * 36,
            dx3: -14 + Math.random() * 30,
            dy3: -16 + Math.random() * 34,
            duration: 3.2 + Math.random() * 2,
            delay: Math.random() * 1.8,
        }))
    ), []);

    useGsapPageMotion(pageRef);

    useEffect(() => {
        factsPoolRef.current = sessionFactsPool;
    }, [sessionFactsPool]);

    useEffect(() => {
        factIndexRef.current = sessionFactIndex;
    }, [sessionFactIndex]);

    useEffect(() => {
        return () => {
            if (startTimerRef.current !== null) {
                window.clearTimeout(startTimerRef.current);
            }
            if (factCycleRef.current !== null) {
                window.clearInterval(factCycleRef.current);
            }
            if (factSwapTimeoutRef.current !== null) {
                window.clearTimeout(factSwapTimeoutRef.current);
            }
        };
    }, []);

    useEffect(() => {
        if (!(startingSession && sessionStep === 'generating')) {
            setFactVisible(false);
            if (factCycleRef.current !== null) {
                window.clearInterval(factCycleRef.current);
                factCycleRef.current = null;
            }
            if (factSwapTimeoutRef.current !== null) {
                window.clearTimeout(factSwapTimeoutRef.current);
                factSwapTimeoutRef.current = null;
            }
            return;
        }

        const setRandomFactPosition = () => {
            const safeZones = [
                { x: 18, y: 22 },
                { x: 82, y: 22 },
                { x: 18, y: 78 },
                { x: 82, y: 78 },
            ];
            const zone = safeZones[Math.floor(Math.random() * safeZones.length)];
            const jitterX = -5 + Math.random() * 10;
            const jitterY = -4 + Math.random() * 8;
            setFactX(zone.x + jitterX);
            setFactY(zone.y + jitterY);
        };

        const nextFact = (competenciaLabel: string): string => {
            const source = factsPoolRef.current.length > 0
                ? factsPoolRef.current
                : getFactsFallback(competenciaLabel);

            if (source.length === 0) {
                return 'La practica constante te ayuda a mejorar tu desempeno.';
            }

            const index = factIndexRef.current % source.length;
            const fact = source[index];
            const nextIndex = (index + 1) % source.length;
            factIndexRef.current = nextIndex;
            setSessionFactIndex(nextIndex);
            return fact;
        };

        setSessionFact(nextFact(sessionCompetencia));
        setRandomFactPosition();
        setFactVisible(true);

        factCycleRef.current = window.setInterval(() => {
            setFactVisible(false);
            factSwapTimeoutRef.current = window.setTimeout(() => {
                setSessionFact(nextFact(sessionCompetencia));
                setRandomFactPosition();
                setFactVisible(true);
            }, 380);
        }, 2500);

        return () => {
            if (factCycleRef.current !== null) {
                window.clearInterval(factCycleRef.current);
                factCycleRef.current = null;
            }
            if (factSwapTimeoutRef.current !== null) {
                window.clearTimeout(factSwapTimeoutRef.current);
                factSwapTimeoutRef.current = null;
            }
        };
    }, [startingSession, sessionStep, sessionCompetencia]);

    const loadQuestions = async (fromSessionFlow = false) => {
        setLoading(true); setError(''); setPreguntas([]);
        setCurrent(0); setSelected(null); setRevealed(false); setScore(0); setDone(false);
        setSupportByQuestion({});
        setAnswerResults({});
        try {
            const selectedComp = competencia || '';
            const isEnglishSession = isEnglishComp(selectedComp);
            const isGeneralSession = isGeneralComp(selectedComp);
            const res = await aiAPI.sugerencias({
                programa: student!.programa,
                competencia: competencia || undefined,
                cantidad: sessionQuestionCount,
                nivel_objetivo: isEnglishSession ? (adaptiveTarget === 'A2' || adaptiveTarget === 'B1' ? adaptiveTarget : 'A2') : undefined,
                dificultad_objetivo: (!isEnglishSession && isGeneralSession)
                    ? (adaptiveTarget === 'basico' || adaptiveTarget === 'intermedio' || adaptiveTarget === 'avanzado' ? adaptiveTarget : 'intermedio')
                    : undefined,
            });
            if (res.data.length === 0) { setError('No hay preguntas disponibles para esos filtros.'); }
            else setPreguntas(res.data);
        } catch { setError('Error al cargar preguntas. Verifica la conexión.'); }
        finally {
            setLoading(false);
            if (fromSessionFlow) {
                setSessionStep('ready');
                window.setTimeout(() => {
                    setStartingSession(false);
                    setSessionStep('intro');
                }, 560);
            }
        }
    };

    const q = preguntas[current];
    const tieneOpciones = (q?.opciones?.length ?? 0) > 0;
    const qSupport = q ? supportByQuestion[q.id] : undefined;
    // Número de preguntas con opciones (para el marcador)
    const totalConOpciones = preguntas.filter(p => p.opciones.length > 0).length;

    const handleSelect = (opcion: string) => {
        if (revealed) return;
        setSelected(opcion);
        setRevealed(true);
        const correcta = opcion === q.respuesta_correcta;
        if (correcta) setScore(s => s + 1);
        setAnswerResults(prev => ({
            ...prev,
            [q.id]: {
                competencia: q.competencia || 'General',
                correcta,
            },
        }));

        if (q && isGeneralComp(q.competencia || '')) {
            const currentIsEnglish = isEnglishComp(q.competencia || '');
            setAdaptiveAnswered(prevAnswered => {
                const nextAnswered = prevAnswered + 1;
                setAdaptiveCorrect(prevCorrect => {
                    const nextCorrect = prevCorrect + (correcta ? 1 : 0);
                    if (currentIsEnglish && nextAnswered >= 2) {
                        const ratio = nextCorrect / nextAnswered;
                        setAdaptiveTarget(ratio >= 0.7 ? 'B1' : 'A2');
                    }
                    if (!currentIsEnglish && nextAnswered >= 3) {
                        const ratio = nextCorrect / nextAnswered;
                        setAdaptiveTarget(inferGeneralDifficulty(ratio));
                    }
                    return nextCorrect;
                });
                return nextAnswered;
            });
        }

        // Guardar la respuesta del estudiante en el historial
        queriesAPI.save({
            programa: student!.programa,
            competencia: q.competencia,
            pregunta: q.enunciado,
            respuesta: `Respuesta elegida: ${opcion}\nRespuesta correcta: ${q.respuesta_correcta}\n${q.explicacion}`,
            tiempo_respuesta_ms: 0,
            es_practica: true,
            acierto: correcta,
            nivel_objetivo: adaptiveTarget,
            nivel_pregunta: q.nivel_cefr || q.nivel_dificultad || null,
            tipo_pregunta: q.tipo_ingles || null,
        }).catch(() => { /* no bloquear la UI si falla el guardado */ });
    };

    const handleNext = () => {
        if (current + 1 >= preguntas.length) { setDone(true); return; }
        setSelected(null); setRevealed(false); setCurrent(c => c + 1);
    };

    const handleContinueFragment = () => {
        // Avanza sin modificar el score (fragmento de lectura)
        handleNext();
    };

    const startPracticeSession = () => {
        if (loading || startingSession) return;
        const selected = competencia || 'Todas';
        const firstName = student?.nombre?.split(' ')[0] || 'estudiante';
        const fallbackFacts = normalizeFacts(getFactsFallback(selected));

        setSessionFactsPool(fallbackFacts);
        setSessionFactIndex(0);
        factsPoolRef.current = fallbackFacts;
        factIndexRef.current = 0;

        setSessionCompetencia(selected);
        setSessionMessage(`${firstName}, alista tu enfoque para ${sessionQuestionCount} preguntas.`);
        setSessionFact(fallbackFacts[0] ?? 'La practica constante te ayuda a mejorar tu desempeno.');
        setFactVisible(false);
        setSessionStep('intro');
        setStartingSession(true);

        if (isGeneralComp(selected) && normalizeCompKey(selected) !== 'todas') {
            queriesAPI.history().then((r) => {
                const history = Array.isArray(r.data) ? r.data : [];
                const compKey = normalizeCompKey(selected);
                const compPractice = history.filter((h: any) =>
                    !!h?.es_practica &&
                    normalizeCompKey(String(h?.competencia || '')) === compKey &&
                    h?.acierto !== null && h?.acierto !== undefined
                );

                if (compPractice.length > 0) {
                    const total = compPractice.length;
                    const correct = compPractice.filter((h: any) => h.acierto === true).length;
                    const ratio = correct / total;
                    if (isEnglishComp(selected)) {
                        setAdaptiveTarget(ratio >= 0.7 ? 'B1' : 'A2');
                    } else {
                        setAdaptiveTarget(inferGeneralDifficulty(ratio));
                    }
                    setAdaptiveAnswered(total);
                    setAdaptiveCorrect(correct);
                } else {
                    setAdaptiveTarget(isEnglishComp(selected) ? 'A2' : 'intermedio');
                    setAdaptiveAnswered(0);
                    setAdaptiveCorrect(0);
                }
            }).catch(() => {
                setAdaptiveTarget(isEnglishComp(selected) ? 'A2' : 'intermedio');
                setAdaptiveAnswered(0);
                setAdaptiveCorrect(0);
            });
        } else {
            setAdaptiveTarget('intermedio');
            setAdaptiveAnswered(0);
            setAdaptiveCorrect(0);
        }

        void aiAPI.datosCuriosos({
            programa: student!.programa,
            competencia: selected,
            cantidad: 10,
        }).then((res) => {
            const aiFacts = normalizeFacts(res?.data?.datos ?? []);
            if (aiFacts.length > 0) {
                setSessionFactsPool(aiFacts);
                setSessionFactIndex(0);
                factsPoolRef.current = aiFacts;
                factIndexRef.current = 0;
                setSessionFact(aiFacts[0]);
            }
        }).catch(() => {
            // Mantener fallback local si falla la generacion IA.
        });

        startTimerRef.current = window.setTimeout(async () => {
            setSessionStep('generating');
            setSessionMessage(`${firstName}, espera mientras generamos tu ${sessionLengthLabel.toLowerCase()}...`);
            await loadQuestions(true);
        }, 1100);
    };

    const getOptionStyle = (opcion: string): React.CSSProperties => {
        if (!revealed) return {};
        if (opcion === q.respuesta_correcta)
            return { background: 'rgba(16,185,129,0.15)', borderColor: 'var(--accent)', color: 'var(--accent)' };
        if (opcion === selected)
            return { background: 'rgba(239,68,68,0.1)', borderColor: 'var(--danger)', color: 'var(--danger)' };
        return { opacity: 0.45 };
    };

    useEffect(() => {
        if (!q || loading) return;
        if (supportByQuestion[q.id]) return;

        const needsTranslation = /ingles/i.test(q.competencia || '');
        const needsVisual = hasVisualCue(q);
        if (!needsTranslation && !needsVisual) return;

        setSupportByQuestion(prev => ({ ...prev, [q.id]: { loading: true } }));

        aiAPI.apoyoPregunta({
            programa: student!.programa,
            competencia: q.competencia,
            enunciado: q.enunciado,
            texto_base: q.texto_base,
            opciones: q.opciones,
            explicacion: q.explicacion,
        }).then(res => {
            setSupportByQuestion(prev => ({
                ...prev,
                [q.id]: {
                    loading: false,
                    mostrar_traduccion: !!res.data?.mostrar_traduccion,
                    texto_base_es: res.data?.texto_base_es || '',
                    enunciado_es: res.data?.enunciado_es || '',
                    opciones_es: Array.isArray(res.data?.opciones_es) ? res.data.opciones_es : [],
                    explicacion_es: res.data?.explicacion_es || '',
                    requiere_visual: !!res.data?.requiere_visual,
                    visual_descripcion: res.data?.visual_descripcion || '',
                    image_data_url: res.data?.image_data_url || null,
                    caption: res.data?.caption || null,
                },
            }));
        }).catch(() => {
            setSupportByQuestion(prev => ({ ...prev, [q.id]: { loading: false } }));
        });
    }, [q?.id, loading]);

    // ── Pantalla de resultados ─────────────────────────
    if (done) {
        const baseTotal = totalConOpciones > 0 ? totalConOpciones : preguntas.length;
        const pct = baseTotal > 0 ? Math.round((score / baseTotal) * 100) : 0;

        const statsByCompetencia: Record<string, { total: number; correctas: number }> = {};
        for (const result of Object.values(answerResults)) {
            const comp = (result.competencia || 'General').trim() || 'General';
            if (!statsByCompetencia[comp]) {
                statsByCompetencia[comp] = { total: 0, correctas: 0 };
            }
            statsByCompetencia[comp].total += 1;
            if (result.correcta) {
                statsByCompetencia[comp].correctas += 1;
            }
        }

        const competencyRows = Object.entries(statsByCompetencia)
            .map(([comp, data]) => ({
                competencia: comp,
                total: data.total,
                correctas: data.correctas,
                porcentaje: data.total > 0 ? Math.round((data.correctas / data.total) * 100) : 0,
            }))
            .sort((a, b) => a.competencia.localeCompare(b.competencia));

        return (
            <div ref={pageRef} style={{ minHeight: '100dvh', boxSizing: 'border-box', background: 'var(--grad-hero)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-lg)' }}>
                <div data-motion="panel" className="card animate-scale-in" style={{ maxWidth: '760px', width: '100%', textAlign: 'center', padding: 'var(--space-2xl)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}>
                    <Trophy size={56} color={pct >= 70 ? 'var(--accent)' : 'var(--warning)'} style={{ margin: '0 auto var(--space-lg)' }} />
                    <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>{pct}%</h1>
                    <p style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-xl)' }}>
                        {totalConOpciones > 0
                            ? `${score} de ${totalConOpciones} correctas${pct >= 70 ? ' · ¡Excelente trabajo!' : ' · ¡Sigue practicando!'}`
                            : `${preguntas.length} fragmentos revisados · ¡Buen repaso!`
                        }
                    </p>

                    {competencyRows.length > 0 && (
                        <div style={{ textAlign: 'left', marginBottom: 'var(--space-xl)', display: 'grid', gap: '8px' }}>
                            <p style={{ margin: 0, fontSize: '12px', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                Reporte por competencia
                            </p>
                            {competencyRows.map((row) => (
                                <div key={row.competencia} style={{ border: '1px solid var(--border)', borderRadius: '12px', padding: '10px 12px', background: 'var(--surface-2)' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '6px' }}>
                                        <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text)' }}>{row.competencia}</span>
                                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{row.correctas}/{row.total} · {row.porcentaje}%</span>
                                    </div>
                                    <div style={{ height: '6px', background: 'var(--surface)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                                        <div style={{
                                            height: '100%',
                                            borderRadius: 'var(--radius-full)',
                                            background: row.porcentaje >= 70 ? 'var(--accent)' : 'var(--warning)',
                                            width: `${row.porcentaje}%`,
                                            transition: 'var(--t-slow)',
                                        }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: 'var(--space-sm)', justifyContent: 'center', flexWrap: 'wrap' }}>
                        <button className="btn btn-primary" onClick={() => loadQuestions()}><RefreshCw size={15} /> Otra ronda</button>
                        <button className="btn btn-ghost" onClick={() => navigate('/chat')}><BookOpen size={15} /> Ir al chat</button>
                    </div>
                </div>
            </div>
        );
    }

    const sessionVisual = getCompetenciaVisual(sessionCompetencia);
    const SessionIcon = sessionVisual.Icon;

    return (
        <div ref={pageRef} style={{ minHeight: '100dvh', boxSizing: 'border-box', background: 'var(--grad-hero)', padding: 'var(--space-lg)', position: 'relative' }}>
            <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 1, overflow: 'hidden' }}>
                {particleConfigs.map((p, i) => (
                    <span
                        key={i}
                        style={{
                            position: 'absolute',
                            width: `${p.size}px`,
                            height: `${p.size}px`,
                            left: `${p.left}%`,
                            top: `${p.top}%`,
                            borderRadius: '999px',
                            background: i % 2 === 0 ? 'rgba(70, 104, 127, 0.62)' : 'rgba(87, 126, 110, 0.6)',
                            opacity: p.opacity,
                            animation: `bg-particle-random ${p.duration}s ease-in-out ${p.delay}s infinite alternate, bg-particle-glow ${2.3 + (i % 3) * 0.4}s ease-in-out ${p.delay}s infinite`,
                            boxShadow: i % 2 === 0 ? '0 0 12px rgba(93, 145, 186, 0.46)' : '0 0 12px rgba(102, 170, 137, 0.42)',
                            ['--dx1' as any]: `${p.dx1}px`,
                            ['--dy1' as any]: `${p.dy1}px`,
                            ['--dx2' as any]: `${p.dx2}px`,
                            ['--dy2' as any]: `${p.dy2}px`,
                            ['--dx3' as any]: `${p.dx3}px`,
                            ['--dy3' as any]: `${p.dy3}px`,
                        }}
                    />
                ))}
            </div>
            {startingSession && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 70,
                    display: 'grid',
                    placeItems: 'center',
                    background: `radial-gradient(circle at 30% 20%, color-mix(in srgb, ${sessionVisual.colorB} 30%, transparent), transparent 45%), linear-gradient(150deg, color-mix(in srgb, ${sessionVisual.colorA} 26%, #eaf2f8), #edf3f7)`,
                    backdropFilter: 'blur(4px)',
                    transition: 'opacity 560ms ease',
                    opacity: sessionStep === 'ready' ? 0 : 1,
                }}>
                    {sessionStep === 'generating' && (
                        <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
                            {Array.from({ length: 22 }).map((_, i) => (
                                <span
                                    key={`session-bg-particle-${i}`}
                                    style={{
                                        position: 'absolute',
                                        width: `${7 + (i % 4) * 2}px`,
                                        height: `${7 + (i % 4) * 2}px`,
                                        left: `${5 + ((i * 4.3) % 90)}%`,
                                        top: `${10 + ((i * 9.1) % 78)}%`,
                                        borderRadius: '999px',
                                        background: i % 2 === 0 ? 'rgba(90, 132, 160, 0.68)' : 'rgba(88, 151, 126, 0.64)',
                                        boxShadow: i % 2 === 0
                                            ? '0 0 14px rgba(119, 170, 202, 0.5)'
                                            : '0 0 14px rgba(116, 189, 157, 0.48)',
                                        animation: `session-particle-float ${3.4 + (i % 5) * 0.45}s ease-in-out ${i * 0.12}s infinite alternate`,
                                    }}
                                />
                            ))}
                        </div>
                    )}

                    <div style={{ textAlign: 'center', position: 'relative', zIndex: 2 }}>
                        <div style={{
                            width: '92px',
                            height: '92px',
                            margin: '0 auto 14px',
                            borderRadius: '999px',
                            display: 'grid',
                            placeItems: 'center',
                            color: '#fff',
                            background: sessionStep === 'generating'
                                ? 'linear-gradient(145deg, rgba(255,255,255,0.42), rgba(237,247,255,0.34))'
                                : `linear-gradient(140deg, ${sessionVisual.colorA}, ${sessionVisual.colorB})`,
                            border: sessionStep === 'generating' ? '1px solid rgba(255,255,255,0.58)' : 'none',
                            boxShadow: sessionStep === 'generating' ? '0 12px 26px rgba(41, 74, 96, 0.16)' : 'none',
                            backdropFilter: sessionStep === 'generating' ? 'blur(6px)' : 'none',
                            animation: sessionStep === 'generating' ? 'none' : 'session-icon 1200ms ease-in-out',
                        }}>
                            {sessionStep === 'generating' ? (
                                <div style={{ position: 'relative', width: '52px', height: '52px', display: 'grid', placeItems: 'center' }}>
                                    {Array.from({ length: 6 }).map((_, i) => (
                                        <span
                                            key={i}
                                            style={{
                                                position: 'absolute',
                                                width: '6px',
                                                height: '6px',
                                                borderRadius: '999px',
                                                background: i % 2 === 0 ? sessionVisual.colorA : sessionVisual.colorB,
                                                boxShadow: '0 0 8px rgba(255,255,255,0.42)',
                                                animation: `loader-particle-orbit ${1.8 + i * 0.12}s linear ${i * 0.14}s infinite`,
                                            }}
                                        />
                                    ))}
                                    <span style={{
                                        position: 'absolute',
                                        inset: 0,
                                        borderRadius: '999px',
                                        border: `2px solid color-mix(in srgb, ${sessionVisual.colorA} 22%, transparent)`,
                                        borderTopColor: sessionVisual.colorA,
                                        animation: 'loader-ring 1s linear infinite',
                                    }} />
                                    <span style={{
                                        position: 'absolute',
                                        inset: '7px',
                                        borderRadius: '999px',
                                        border: `2px solid color-mix(in srgb, ${sessionVisual.colorB} 24%, transparent)`,
                                        borderBottomColor: sessionVisual.colorB,
                                        animation: 'loader-ring-rev 1.25s linear infinite',
                                    }} />
                                    <Loader2 size={18} style={{ color: sessionVisual.colorA, animation: 'spin 1.3s linear infinite' }} />
                                </div>
                            ) : <SessionIcon size={34} weight="duotone" />}
                        </div>
                        <h3 style={{ margin: 0, fontSize: '26px', color: '#243746', fontFamily: 'var(--font-heading)' }}>
                            {sessionStep === 'generating' ? 'Generando práctica' : sessionStep === 'ready' ? 'Todo listo' : 'Preparando sesión'}
                        </h3>
                        <p style={{ margin: '6px 0 0', fontSize: '14px', color: '#4f6678', fontWeight: 600 }}>{sessionMessage}</p>
                        <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#5e7789' }}>{sessionCompetencia}</p>
                    </div>

                    {sessionStep === 'generating' && (
                        <div
                            style={{
                                position: 'absolute',
                                left: `${factX}%`,
                                top: `${factY}%`,
                                transform: 'translate(-50%, -50%)',
                                maxWidth: '420px',
                                textAlign: 'center',
                                opacity: factVisible ? 1 : 0,
                                transition: 'opacity 380ms ease',
                                pointerEvents: 'none',
                                zIndex: 1,
                                padding: '12px 14px',
                                borderRadius: '16px',
                                border: '1px solid rgba(255,255,255,0.42)',
                                background: 'linear-gradient(145deg, rgba(255,255,255,0.28), rgba(232,245,255,0.2))',
                                backdropFilter: 'blur(8px)',
                                boxShadow: '0 10px 24px rgba(31, 63, 84, 0.16)',
                            }}
                        >
                            <p style={{
                                margin: 0,
                                fontSize: '12px',
                                fontWeight: 800,
                                letterSpacing: '0.11em',
                                color: '#3e5b70',
                                textTransform: 'uppercase',
                                fontFamily: 'var(--font-heading)',
                            }}>
                                Dato curioso
                            </p>
                            <p style={{
                                margin: '8px 0 0',
                                fontSize: '18px',
                                lineHeight: 1.45,
                                color: '#2f4657',
                                fontFamily: '"Trebuchet MS", var(--font-heading), serif',
                                fontStyle: 'italic',
                                textShadow: '0 2px 10px rgba(255,255,255,0.55)',
                            }}>
                                {sessionFact}
                            </p>
                        </div>
                    )}
                </div>
            )}

            <div data-motion="headline" style={{ maxWidth: '100%', margin: '0 auto', position: 'relative', zIndex: 2 }}>
                {/* Header */}
                <div data-motion="panel" className="animate-fade-up" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div style={{ position: 'relative', minHeight: '84px', maxWidth: '100%', margin: '0 auto', padding: '0 8px' }}>
                        <button
                            className="btn-icon"
                            onClick={() => navigate('/chat')}
                            aria-label="Volver al chat"
                            style={{ position: 'absolute', left: 0, top: '50%', transform: 'translateY(-50%)', width: '44px', height: '44px' }}
                        >
                            <ArrowLeft size={20} />
                        </button>

                        <div style={{ textAlign: 'center' }}>
                            <h1 style={{ fontSize: '30px', lineHeight: 1.1 }}>Ascenso Pro · Práctica</h1>
                            <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '4px' }}>{student?.programa} · Entrenamiento guiado</p>
                        </div>

                        <div style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)' }}>
                            <InstitutionalLogo size={100} />
                        </div>
                    </div>
                </div>

                <div style={{ maxWidth: '760px', margin: '0 auto' }}>

                {/* Filtros */}
                {preguntas.length === 0 && !loading && (
                    <div data-motion="panel" className="card animate-fade-up" style={{ border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)' }}>
                        <h2 style={{ fontSize: '20px', marginBottom: 'var(--space-md)', textAlign: 'center' }}>Configura tu sesión</h2>
                        <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '10px', textAlign: 'center' }}>
                            Elige una competencia
                        </label>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                            gap: '10px',
                            marginBottom: 'var(--space-lg)',
                        }}>
                            <button
                                type="button"
                                onClick={() => setCompetencia('')}
                                style={{
                                    textAlign: 'left',
                                    borderRadius: '14px',
                                    border: competencia === '' ? '1px solid #35556a' : '1px solid var(--border)',
                                    background: competencia === ''
                                        ? 'linear-gradient(140deg, #e8f3fc 0%, #eef7ff 100%)'
                                        : 'linear-gradient(140deg, #ffffff 0%, #f6f9fc 100%)',
                                    boxShadow: competencia === '' ? '0 10px 20px rgba(53,85,106,0.16)' : '0 8px 16px rgba(27,45,61,0.08)',
                                    padding: '11px 12px',
                                    cursor: 'pointer',
                                    transition: 'var(--t-fast)',
                                    animation: 'practice-float 4.2s ease-in-out infinite',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', color: '#35556a', fontWeight: 700 }}>
                                    <LayoutGrid size={15} /> Todas
                                </div>
                                <p style={{ margin: 0, fontSize: '12px', color: '#587083' }}>Mezcla preguntas de todas las areas.</p>
                            </button>

                            {COMPETENCIA_CARDS.filter(c => COMPETENCIAS.includes(c.label)).map((card) => {
                                const active = competencia === card.label;
                                const idx = COMPETENCIA_CARDS.findIndex(c => c.label === card.label);
                                return (
                                    <button
                                        key={card.label}
                                        type="button"
                                        onClick={() => setCompetencia(card.label)}
                                        style={{
                                            textAlign: 'left',
                                            borderRadius: '14px',
                                            border: active ? `1px solid ${card.tint}` : '1px solid var(--border)',
                                            background: active
                                                ? `linear-gradient(145deg, #ffffff 0%, color-mix(in srgb, ${card.tint} 15%, #eef5fa) 100%)`
                                                : 'linear-gradient(140deg, #ffffff 0%, #f6f9fc 100%)',
                                            boxShadow: active ? '0 12px 22px rgba(40,72,94,0.16)' : '0 8px 16px rgba(27,45,61,0.08)',
                                            padding: '11px 12px',
                                            cursor: 'pointer',
                                            transition: 'var(--t-fast)',
                                            animation: `practice-float 4.2s ease-in-out ${idx * 0.24}s infinite`,
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', color: card.tint, fontWeight: 700 }}>
                                            {card.icon}
                                            <span style={{ fontSize: '12px' }}>{card.label}</span>
                                        </div>
                                        <p style={{ margin: 0, fontSize: '11px', color: '#5a7080' }}>
                                            {active ? 'Seleccionada para esta sesion.' : 'Practicar esta competencia.'}
                                        </p>
                                    </button>
                                );
                            })}
                        </div>

                        <label style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '10px', textAlign: 'center' }}>
                            Elige la duracion de entrenamiento
                        </label>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                            gap: '10px',
                            marginBottom: 'var(--space-lg)',
                        }}>
                            {(Object.keys(TRAINING_LENGTH_PRESETS) as TrainingLength[]).map((mode, idx) => {
                                const preset = TRAINING_LENGTH_PRESETS[mode];
                                const active = sessionLength === mode;

                                return (
                                    <button
                                        key={mode}
                                        type="button"
                                        onClick={() => setSessionLength(mode)}
                                        style={{
                                            textAlign: 'left',
                                            borderRadius: '14px',
                                            border: active ? '1px solid #35556a' : '1px solid var(--border)',
                                            background: active
                                                ? 'linear-gradient(140deg, #e8f3fc 0%, #eef7ff 100%)'
                                                : 'linear-gradient(140deg, #ffffff 0%, #f6f9fc 100%)',
                                            boxShadow: active ? '0 10px 20px rgba(53,85,106,0.16)' : '0 8px 16px rgba(27,45,61,0.08)',
                                            padding: '11px 12px',
                                            cursor: 'pointer',
                                            transition: 'var(--t-fast)',
                                            animation: `practice-float 4.2s ease-in-out ${idx * 0.2}s infinite`,
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', color: '#35556a', fontWeight: 700 }}>
                                            <span style={{ fontSize: '12px' }}>{preset.label}</span>
                                        </div>
                                        <p style={{ margin: 0, fontSize: '12px', color: '#587083' }}>{preset.descripcion}</p>
                                        <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#3f6278', fontWeight: 700 }}>
                                            {preset.cantidad} preguntas
                                        </p>
                                    </button>
                                );
                            })}
                        </div>

                        {error && <p style={{ color: 'var(--danger)', fontSize: '13px', marginBottom: 'var(--space-md)' }}>{error}</p>}
                        <button className="btn btn-primary" onClick={startPracticeSession} disabled={startingSession || loading} style={{ width: '100%', justifyContent: 'center', height: '44px' }}>
                            Comenzar práctica
                        </button>
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', position: 'relative', minHeight: '190px', display: 'grid', placeItems: 'center' }}>
                        <div style={{ position: 'relative', width: '84px', height: '84px', display: 'grid', placeItems: 'center', margin: '0 auto' }}>
                            {Array.from({ length: 8 }).map((_, i) => (
                                <span
                                    key={`load-particle-${i}`}
                                    style={{
                                        position: 'absolute',
                                        width: '6px',
                                        height: '6px',
                                        borderRadius: '999px',
                                        background: i % 2 === 0 ? 'rgba(70, 104, 127, 0.72)' : 'rgba(87, 126, 110, 0.68)',
                                        boxShadow: '0 0 8px rgba(255,255,255,0.38)',
                                        animation: `loader-particle-orbit ${1.9 + i * 0.1}s linear ${i * 0.12}s infinite`,
                                    }}
                                />
                            ))}
                            <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)', margin: '0 auto' }} />
                        </div>
                        <p style={{ color: 'var(--text-muted)', marginTop: 'var(--space-md)' }}>Cargando preguntas…</p>
                    </div>
                )}

                {/* Quiz */}
                {q && !loading && (
                    <>
                        {/* Progress */}
                        <div data-motion="panel" className="card animate-fade-up" style={{ marginBottom: 'var(--space-lg)', border: '1px solid var(--border)', padding: 'var(--space-md)' }}>
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
                            <p style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--text-hint)' }}>
                                Modalidad: {sessionLengthLabel} ({sessionQuestionCount} preguntas)
                            </p>
                            {isGeneralComp(q.competencia || '') && (
                                <div style={{ marginTop: '8px', display: 'grid', gap: '2px' }}>
                                    <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
                                        Entrenamiento guiado estilo Saber Pro: misma estructura, sin cronometro ni presion.
                                        Nivel objetivo actual: {isEnglishComp(q.competencia || '') ? adaptiveTarget : difficultyLabel(String(adaptiveTarget))}.
                                    </p>
                                    <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-hint)' }}>
                                        Progreso adaptativo: {adaptiveCorrect}/{adaptiveAnswered} aciertos en {q.competencia.toLowerCase()}.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Pregunta */}
                        <div data-motion="panel" className="card animate-fade-up" style={{ marginBottom: 'var(--space-md)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-md)' }}>
                            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
                                <span className="badge badge-primary">{q.competencia}</span>
                                {q.bloque_id && q.orden_en_bloque && q.preguntas_en_bloque && (
                                    <span className="badge" style={{ fontSize: '11px', background: 'rgba(63, 98, 120, 0.12)', border: '1px solid rgba(63, 98, 120, 0.24)', color: '#35556a' }}>
                                        Bloque {q.bloque_id} · {q.orden_en_bloque}/{q.preguntas_en_bloque}
                                    </span>
                                )}
                                {q.tipo_ingles && (
                                    <span className="badge" style={{ fontSize: '11px', background: 'rgba(63, 98, 120, 0.14)', border: '1px solid rgba(63, 98, 120, 0.28)', color: '#2f5468' }}>
                                        {englishTypeLabel(q.tipo_ingles)}
                                    </span>
                                )}
                                {q.nivel_cefr && (
                                    <span className="badge" style={{ fontSize: '11px', background: 'rgba(63, 122, 103, 0.14)', border: '1px solid rgba(63, 122, 103, 0.28)', color: '#2f6b58' }}>
                                        {String(q.nivel_cefr).toUpperCase()}
                                    </span>
                                )}
                                {q.nivel_dificultad && (
                                    <span className="badge" style={{ fontSize: '11px', background: 'rgba(120, 96, 63, 0.14)', border: '1px solid rgba(120, 96, 63, 0.28)', color: '#6f5630' }}>
                                        {difficultyLabel(String(q.nivel_dificultad))}
                                    </span>
                                )}
                            </div>

                            {/* Texto base / pasaje lector */}
                            {q.texto_base && (
                                <div style={{
                                    background: 'var(--surface-3)',
                                    border: '1px solid var(--border)',
                                    borderLeft: '4px solid var(--primary)',
                                    borderRadius: 'var(--radius-md)',
                                    padding: 'var(--space-md)',
                                    marginBottom: 'var(--space-md)',
                                }}>
                                    <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                        📄 Texto de referencia
                                    </p>
                                    <div style={{ fontSize: '14px', lineHeight: '1.75', color: 'var(--text-muted)', fontStyle: 'italic', whiteSpace: 'pre-wrap' }}>
                                        {renderTextWithLatex(q.texto_base)}
                                    </div>
                                    {qSupport?.mostrar_traduccion && qSupport?.texto_base_es && (
                                        <div style={{ marginTop: '10px', borderTop: '1px dashed var(--border)', paddingTop: '10px' }}>
                                            <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                                Traduccion al espanol
                                            </p>
                                            <div style={{ fontSize: '14px', lineHeight: '1.7', color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
                                                {renderTextWithLatex(qSupport.texto_base_es)}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div style={{ fontSize: '16px', lineHeight: '1.65', fontWeight: 500, whiteSpace: 'pre-wrap' }}>
                                {renderTextWithLatex(q.enunciado)}
                            </div>

                            {qSupport?.mostrar_traduccion && qSupport?.enunciado_es && (
                                <div style={{ marginTop: '10px', borderLeft: '3px solid var(--accent)', paddingLeft: '10px' }}>
                                    <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        Pregunta en espanol
                                    </p>
                                    <div style={{ fontSize: '15px', lineHeight: '1.6', color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
                                        {renderTextWithLatex(qSupport.enunciado_es)}
                                    </div>
                                </div>
                            )}

                            {qSupport?.loading && (
                                <p style={{ marginTop: '10px', fontSize: '12px', color: 'var(--text-muted)' }}>Generando apoyo visual y traduccion...</p>
                            )}

                            {qSupport?.image_data_url && (
                                <figure style={{ marginTop: '12px', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden', background: 'var(--surface)' }}>
                                    <img src={qSupport.image_data_url} alt={qSupport.caption || 'Grafica de apoyo'} style={{ width: '100%', display: 'block' }} />
                                    <figcaption style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '8px 10px' }}>
                                        {qSupport.caption || 'Grafica de apoyo para resolver la pregunta'}
                                    </figcaption>
                                </figure>
                            )}

                            {qSupport?.requiere_visual && !qSupport?.loading && !qSupport?.image_data_url && (
                                <div style={{ marginTop: '12px', border: '1px dashed var(--border)', borderRadius: '12px', padding: '10px', background: 'var(--surface-2)' }}>
                                    <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                        Guia visual sugerida
                                    </p>
                                    <p style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-muted)', margin: 0 }}>
                                        {qSupport.visual_descripcion || 'Construye una grafica con eje X (anios) y eje Y (valor de inversion), y compara la tendencia general para responder.'}
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Opciones — solo si la pregunta es estructurada */}
                        {tieneOpciones && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginBottom: 'var(--space-lg)' }}>
                                {q.opciones.map((op, i) => (
                                    <button key={i} onClick={() => handleSelect(op)} data-motion="row"
                                        className="card animate-fade-up"
                                        style={{
                                            textAlign: 'left', cursor: revealed ? 'default' : 'pointer',
                                            padding: 'var(--space-md)', transition: 'var(--t-base)',
                                            display: 'flex', alignItems: 'center', gap: 'var(--space-sm)',
                                            animationDelay: `${i * 60}ms`,
                                            border: '1px solid var(--border)',
                                            ...getOptionStyle(op),
                                        }}>
                                        <span style={{
                                            width: '28px', height: '28px', borderRadius: 'var(--radius-full)',
                                            border: '1.5px solid var(--border)', display: 'flex', alignItems: 'center',
                                            justifyContent: 'center', fontSize: '12px', fontWeight: 700, flexShrink: 0
                                        }}>
                                            {['A', 'B', 'C', 'D'][i]}
                                        </span>
                                        <div style={{ display: 'grid', gap: '3px' }}>
                                            <span style={{ fontSize: '14px', whiteSpace: 'pre-wrap' }}>{renderTextWithLatex(op)}</span>
                                            {qSupport?.mostrar_traduccion && qSupport?.opciones_es?.[i] && qSupport?.opciones_es?.[i] !== op && (
                                                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                                    {renderTextWithLatex(qSupport?.opciones_es?.[i])}
                                                </span>
                                            )}
                                        </div>
                                        {revealed && op === q.respuesta_correcta && <CheckCircle size={16} style={{ marginLeft: 'auto', color: 'var(--accent)' }} />}
                                        {revealed && op === selected && op !== q.respuesta_correcta && <XCircle size={16} style={{ marginLeft: 'auto', color: 'var(--danger)' }} />}
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Modo lectura — fragmento PDF sin opciones */}
                        {!tieneOpciones && (
                            <div data-motion="panel" className="card animate-fade-up" style={{ marginBottom: 'var(--space-lg)', borderColor: 'var(--primary)', opacity: 0.95, boxShadow: 'var(--shadow-md)' }}>
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
                            <div data-motion="panel" className="card animate-fade-up" style={{ borderColor: selected === q.respuesta_correcta ? 'var(--accent)' : 'var(--danger)', marginBottom: 'var(--space-lg)', boxShadow: 'var(--shadow-md)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: '8px' }}>
                                    {selected === q.respuesta_correcta
                                        ? <CheckCircle size={18} color="var(--accent)" />
                                        : <XCircle size={18} color="var(--danger)" />}
                                    <strong style={{ color: selected === q.respuesta_correcta ? 'var(--accent)' : 'var(--danger)' }}>
                                        {selected === q.respuesta_correcta
                                            ? (qSupport?.mostrar_traduccion ? 'Correct / Correcto' : '¡Correcto!')
                                            : (qSupport?.mostrar_traduccion ? 'Incorrect / Incorrecto' : 'Incorrecto')}
                                    </strong>
                                </div>
                                <div style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--text-muted)', whiteSpace: 'pre-wrap' }}>
                                    {renderTextWithLatex(q.explicacion)}
                                </div>
                                {qSupport?.mostrar_traduccion && qSupport?.explicacion_es && qSupport?.explicacion_es !== q.explicacion && (
                                    <div style={{ marginTop: '10px', borderLeft: '3px solid var(--accent)', paddingLeft: '10px' }}>
                                        <p style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent)', marginBottom: '5px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Explicacion en espanol
                                        </p>
                                        <div style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--text-muted)', margin: 0, whiteSpace: 'pre-wrap' }}>
                                            {renderTextWithLatex(qSupport.explicacion_es)}
                                        </div>
                                    </div>
                                )}
                                <button className="btn btn-primary" onClick={handleNext} style={{ marginTop: 'var(--space-md)' }}>
                                    {current + 1 >= preguntas.length ? <><Trophy size={15} /> Ver resultados</> : <>Siguiente <ChevronRight size={15} /></>}
                                </button>
                            </div>
                        )}
                    </>
                )}
                </div>
            </div>
            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
                @keyframes practice-float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                @keyframes bg-particle-random {
                    0% { transform: translate3d(0, 0, 0); }
                    25% { transform: translate3d(var(--dx1), var(--dy1), 0); }
                    55% { transform: translate3d(var(--dx2), var(--dy2), 0); }
                    100% { transform: translate3d(var(--dx3), var(--dy3), 0); }
                }
                @keyframes bg-particle-glow {
                    0%, 100% { opacity: 0.55; }
                    50% { opacity: 1; }
                }
                @keyframes loader-ring {
                    to { transform: rotate(360deg); }
                }
                @keyframes loader-ring-rev {
                    to { transform: rotate(-360deg); }
                }
                @keyframes loader-particle-orbit {
                    0% {
                        transform: rotate(0deg) translateX(34px) scale(0.9);
                        opacity: 0.35;
                    }
                    50% {
                        transform: rotate(180deg) translateX(30px) scale(1.05);
                        opacity: 0.95;
                    }
                    100% {
                        transform: rotate(360deg) translateX(34px) scale(0.9);
                        opacity: 0.35;
                    }
                }
                @keyframes session-particle-float {
                    0% { transform: translate3d(0, 0, 0) scale(0.9); opacity: 0.45; }
                    50% { transform: translate3d(10px, -14px, 0) scale(1.08); opacity: 1; }
                    100% { transform: translate3d(-8px, 10px, 0) scale(0.95); opacity: 0.55; }
                }
                @keyframes session-icon {
                    0% { transform: scale(0.86); }
                    40% { transform: scale(1.04); }
                    100% { transform: scale(1); }
                }
            `}</style>
        </div>
    );
};
