import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GraduationCap, User, Lock, Eye, EyeOff, Loader2, Compass, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';
import { InstitutionalLogo } from '../components/InstitutionalLogo';

const PROGRAMAS = [
    'Administración de Empresas',
    'Contaduría Pública',
    'Ingeniería de Sistemas y Computación',
    'Ingeniería Electrónica',
    'Ingeniería Agronómica',
    'Zootecnia',
    'Licenciatura en Ciencias Sociales',
    'Licenciatura en Educación Física, Recreación y Deportes',
];

export const LoginPage: React.FC = () => {
    const pageRef = useRef<HTMLDivElement>(null);
    const accessTimerRef = useRef<number | null>(null);
    const navigate = useNavigate();
    const { loginStudent } = useAuth();
    const [tab, setTab] = useState<'login' | 'register'>('login');
    const [showKey, setShowKey] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [startingStudentSession, setStartingStudentSession] = useState(false);
    const [sessionGreeting, setSessionGreeting] = useState('Preparando tu espacio de estudio...');

    // Login state
    const [cedula, setCedula] = useState('');
    const [clave, setClave] = useState('');

    // Register state
    const [regCedula, setRegCedula] = useState('');
    const [regNombre, setRegNombre] = useState('');
    const [regPrograma, setRegPrograma] = useState('');
    const [regClave, setRegClave] = useState('');

    useGsapPageMotion(pageRef);

    useEffect(() => {
        return () => {
            if (accessTimerRef.current !== null) {
                window.clearTimeout(accessTimerRef.current);
            }
        };
    }, []);

    const beginStudentSession = (studentName?: string) => {
        const firstName = studentName?.split(' ')[0] || 'estudiante';
        setSessionGreeting(`${firstName}, entramos en modo concentracion...`);
        setStartingStudentSession(true);
        accessTimerRef.current = window.setTimeout(() => {
            navigate('/chat');
        }, 2000);
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const res = await authAPI.loginStudent({ cedula, clave_secreta: clave });
            loginStudent(res.data.token, res.data.student);
            beginStudentSession(res.data.student?.nombre);
        } catch (err: any) {
            setError(err.response?.data?.message ?? 'Error al iniciar sesión.');
        } finally {
            setLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        if (regClave.length !== 1) { setError('La clave secreta debe ser exactamente 1 carácter.'); return; }
        setLoading(true); setError('');
        try {
            const res = await authAPI.registerStudent({
                cedula: regCedula, nombre: regNombre,
                programa: regPrograma, clave_secreta: regClave,
            });
            loginStudent(res.data.token, res.data.student);
            beginStudentSession(res.data.student?.nombre);
        } catch (err: any) {
            setError(err.response?.data?.message ?? 'Error en el registro.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div ref={pageRef} style={{
            minHeight: '100vh',
            padding: '24px',
            position: 'relative',
            overflow: 'hidden',
            /* Transparent — WebGL particles show through from RootLayout */
        }}>
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                <div data-motion="blob" style={{
                    position: 'absolute', top: '-14%', right: '-10%',
                    width: '500px', height: '500px', borderRadius: '50%',
                    background: 'radial-gradient(circle, var(--primary-soft) 0%, color-mix(in srgb, var(--primary-soft) 20%, transparent) 48%, transparent 76%)',
                    filter: 'blur(24px)', animation: 'aurora-float 13s ease-in-out infinite',
                }} />
                <div data-motion="blob" style={{
                    position: 'absolute', left: '-10%', bottom: '-16%',
                    width: '430px', height: '430px', borderRadius: '50%',
                    background: 'radial-gradient(circle, var(--accent-soft) 0%, color-mix(in srgb, var(--accent-soft) 20%, transparent) 48%, transparent 74%)',
                    filter: 'blur(20px)', animation: 'aurora-float 15s ease-in-out infinite reverse',
                }} />
            </div>
            <div data-motion="headline" style={{
                maxWidth: '1080px',
                margin: '0 auto',
                minHeight: 'calc(100vh - 48px)',
                display: 'grid',
                gridTemplateColumns: '0.95fr 1.05fr',
                gap: '20px',
                alignItems: 'start',
                alignContent: 'start',
                position: 'relative',
                paddingTop: '8px',
                paddingBottom: '18px',
                zIndex: 1,
            }}>
                <div 
                    onClick={() => navigate('/')}
                    style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center', marginBottom: '2px', cursor: 'pointer' }}
                    title="Volver a la vista principal"
                >
                    <InstitutionalLogo size={148} />
                </div>

                {/* ── Info Panel ───────────────────────────────── */}
                <section data-motion="panel" className="glass-panel" style={{
                    borderRadius: '28px',
                    padding: '36px',
                    boxShadow: 'var(--shadow-lg)',
                    order: 2,
                }}>
                    <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: 'var(--primary)',
                        background: 'var(--primary-soft)',
                        border: '1px solid var(--border)',
                        padding: '6px 12px',
                        borderRadius: '999px',
                        letterSpacing: '0.03em',
                        marginBottom: '18px',
                    }}>
                        <Compass size={14} /> EXPERIENCIA DE ESTUDIO GUIADA
                    </div>

                    <h1 style={{
                        fontSize: 'clamp(30px, 4vw, 48px)',
                        lineHeight: 1.05,
                        color: 'var(--text)',
                        marginBottom: '14px',
                        letterSpacing: '-0.03em',
                    }}>
                        Bienvenido a Ascenso Pro,
                        <br />
                        tu ruta para mejorar en Saber Pro.
                    </h1>

                    <p style={{
                        color: 'var(--text-muted)',
                        fontSize: '16px',
                        maxWidth: '52ch',
                        marginBottom: '24px',
                    }}>
                        Aqui encontraras explicaciones claras, practicas guiadas y seguimiento de tu avance
                        para estudiar mejor y subir tus resultados en las Pruebas Saber Pro.
                    </p>

                    <div style={{ display: 'grid', gap: '12px', maxWidth: '520px' }}>
                        {[
                            'Explicaciones paso a paso de los temas que mas cuestan.',
                            'Preguntas de practica con retroalimentacion inmediata.',
                            'Historial de consultas para medir tu progreso.',
                        ].map((item) => (
                            <div key={item} style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px',
                                color: 'var(--text)',
                                fontSize: '14px',
                            }}>
                                <span style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    background: 'var(--grad-primary)',
                                    boxShadow: '0 0 0 4px var(--primary-glow)',
                                    flexShrink: 0,
                                }} />
                                {item}
                            </div>
                        ))}
                    </div>
                </section>

                {/* ── Form Panel ──────────────────────────────── */}
                <section data-motion="panel" className="glass-panel-strong animate-scale-in" style={{
                    borderRadius: '28px',
                    padding: '24px',
                    boxShadow: 'var(--shadow-lg)',
                    order: 1,
                }}>
                    <div style={{ marginBottom: '18px' }}>
                        <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            fontWeight: 700,
                            color: 'var(--primary)',
                            background: 'var(--primary-soft)',
                            borderRadius: '999px',
                            padding: '5px 10px',
                            marginBottom: '10px',
                        }}>
                            <GraduationCap size={12} /> UDEC · Fusagasuga
                        </div>
                        <h2 style={{ fontSize: '26px', color: 'var(--text)', marginBottom: '4px' }}>Ascenso Pro</h2>
                        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Empieza tu plan de estudio en pocos segundos.</p>
                    </div>

                    {/* Tab switcher */}
                    <div style={{
                        display: 'flex',
                        gap: '6px',
                        background: 'var(--surface-2)',
                        borderRadius: '12px',
                        padding: '4px',
                        marginBottom: '18px',
                    }}>
                        {(['login', 'register'] as const).map(t => (
                            <button
                                key={t}
                                onClick={() => { setTab(t); setError(''); }}
                                style={{
                                    flex: 1,
                                    padding: '9px',
                                    borderRadius: '10px',
                                    fontSize: '13px',
                                    fontWeight: 700,
                                    background: tab === t ? 'var(--grad-primary)' : 'transparent',
                                    color: tab === t ? '#fff' : 'var(--text-muted)',
                                    transition: 'var(--t-base)',
                                }}
                            >
                                {t === 'login' ? 'Ya tengo cuenta' : 'Crear cuenta'}
                            </button>
                        ))}
                    </div>

                    {/* Error message */}
                    {error && (
                        <div style={{
                            width: '100%',
                            padding: '10px 12px',
                            marginBottom: '12px',
                            borderRadius: '10px',
                            fontSize: '13px',
                            color: 'var(--danger)',
                            border: '1px solid var(--danger)',
                            background: 'var(--danger-soft)',
                        }}>
                            {error}
                        </div>
                    )}

                    {/* LOGIN FORM */}
                    {tab === 'login' && (
                        <form data-motion="card" onSubmit={handleLogin} className="animate-fade-up">
                            <div style={{ marginBottom: '12px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Numero de cedula
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <User size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '38px' }}
                                        placeholder="Ej: 1234567890"
                                        value={cedula} onChange={e => setCedula(e.target.value)} required />
                                </div>
                            </div>

                            <div style={{ marginBottom: '18px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Clave secreta
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '38px', paddingRight: '42px' }}
                                        type={showKey ? 'text' : 'password'}
                                        placeholder="Ingresa tu clave"
                                        value={clave} onChange={e => setClave(e.target.value)} required />
                                    <button type="button" onClick={() => setShowKey(s => !s)}
                                        style={{ position: 'absolute', right: '7px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)', width: '28px', height: '28px', borderRadius: '8px' }}
                                        aria-label={showKey ? 'Ocultar clave' : 'Mostrar clave'}>
                                        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                                    </button>
                                </div>
                                <p style={{ margin: '6px 0 0', fontSize: '11px', color: 'var(--text-hint)' }}>
                                    Si tu cuenta es antigua, tu clave puede tener más de 1 carácter.
                                </p>
                            </div>

                            <button className="btn btn-primary" type="submit" disabled={loading}
                                style={{
                                    width: '100%',
                                    justifyContent: 'center',
                                    height: '44px',
                                    fontWeight: 700,
                                    boxShadow: 'var(--shadow-glow)',
                                }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <>Entrar al asistente <ArrowRight size={16} /></>}
                            </button>
                        </form>
                    )}

                    {/* REGISTER FORM */}
                    {tab === 'register' && (
                        <form data-motion="card" onSubmit={handleRegister} className="animate-fade-up">
                            {[
                                { label: 'Numero de cedula', val: regCedula, set: setRegCedula, placeholder: 'Ej: 1234567890', icon: <User size={15} /> },
                                { label: 'Nombre completo', val: regNombre, set: setRegNombre, placeholder: 'Tu nombre completo', icon: <GraduationCap size={15} /> },
                            ].map(({ label, val, set, placeholder, icon }) => (
                                <div key={label} style={{ marginBottom: '12px' }}>
                                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-muted)' }}>{label}</label>
                                    <div style={{ position: 'relative' }}>
                                        <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }}>{icon}</span>
                                        <input className="input" style={{ paddingLeft: '38px' }} placeholder={placeholder} value={val} onChange={e => set(e.target.value)} required />
                                    </div>
                                </div>
                            ))}

                            <div style={{ marginBottom: '12px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-muted)' }}>Programa academico</label>
                                <select className="input" value={regPrograma} onChange={e => setRegPrograma(e.target.value)} required>
                                    <option value="">Selecciona tu programa…</option>
                                    {PROGRAMAS.map(p => <option key={p} value={p}>{p}</option>)}
                                </select>
                            </div>

                            <div style={{ marginBottom: '18px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Clave secreta <span style={{ fontWeight: 500, color: 'var(--text-hint)' }}>(1 caracter)</span>
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '38px' }}
                                        type={showKey ? 'text' : 'password'} maxLength={1}
                                        placeholder="Ej: @ o A"
                                        value={regClave} onChange={e => setRegClave(e.target.value)} required />
                                </div>
                            </div>

                            <button className="btn" type="submit" disabled={loading}
                                style={{
                                    width: '100%',
                                    justifyContent: 'center',
                                    height: '44px',
                                    color: '#fff',
                                    fontWeight: 700,
                                    background: 'linear-gradient(120deg, var(--accent) 0%, var(--accent-h) 100%)',
                                    boxShadow: 'var(--shadow-glow)',
                                }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Crear cuenta'}
                            </button>
                        </form>
                    )}

                    <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
                        <Link to="/coordinador" style={{ fontSize: '13px', color: 'var(--primary)', fontWeight: 600 }}>
                            Eres gestor de conocimiento? Accede aqui
                        </Link>
                    </div>

                    <p style={{ textAlign: 'center', marginTop: '14px', fontSize: '11px', color: 'var(--text-hint)' }}>
                        Datos protegidos bajo Ley 1581 de 2012
                    </p>
                </section>

                <div style={{ position: 'absolute', left: 0, right: 0, bottom: '18px', textAlign: 'center' }}>
                    <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '12px', fontWeight: 700, letterSpacing: '0.04em' }}>
                        UNIVERSIDAD DE CUNDINAMARCA
                    </p>
                    <p style={{ margin: '1px 0 0', color: 'var(--text-hint)', fontSize: '11px' }}>
                        Ascenso Pro
                    </p>
                </div>
            </div>

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
                @keyframes access-fade {
                    0% { opacity: 0; }
                    12% { opacity: 1; }
                    88% { opacity: 1; }
                    100% { opacity: 0.96; }
                }
                @keyframes access-wave {
                    0%, 100% { transform: translateY(0) scale(1); opacity: 0.65; }
                    50% { transform: translateY(-8px) scale(1.04); opacity: 1; }
                }
                @keyframes access-progress {
                    0% { transform: scaleX(0); }
                    100% { transform: scaleX(1); }
                }
                @keyframes login-loader-ring {
                    to { transform: rotate(360deg); }
                }
                @keyframes login-loader-ring-rev {
                    to { transform: rotate(-360deg); }
                }
                @keyframes login-loader-orbit {
                    0% {
                        transform: rotate(0deg) translateX(32px) scale(0.9);
                        opacity: 0.4;
                    }
                    50% {
                        transform: rotate(180deg) translateX(28px) scale(1.05);
                        opacity: 0.95;
                    }
                    100% {
                        transform: rotate(360deg) translateX(32px) scale(0.9);
                        opacity: 0.4;
                    }
                }
                @keyframes access-particles {
                    0% { transform: translate3d(0, 0, 0) scale(0.88); opacity: 0.35; }
                    100% { transform: translate3d(10px, -14px, 0) scale(1.16); opacity: 0.95; }
                }
                @media (max-width: 980px) {
                    .animate-scale-in {
                        animation-duration: 220ms;
                    }
                }
                @media (max-width: 900px) {
                    div[style*='grid-template-columns: 0.95fr 1.05fr'] {
                        grid-template-columns: 1fr !important;
                    }
                }
            `}</style>

            {startingStudentSession && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 110,
                    display: 'grid',
                    placeItems: 'center',
                    background: 'color-mix(in srgb, var(--bg) 88%, transparent)',
                    backdropFilter: 'blur(8px)',
                    animation: 'access-fade 2000ms ease forwards',
                }}>
                    <div style={{ textAlign: 'center', color: 'var(--text)', position: 'relative', zIndex: 2, padding: '16px' }}>
                        <div style={{
                            width: '94px',
                            height: '94px',
                            borderRadius: '999px',
                            margin: '0 auto 14px',
                            display: 'grid',
                            placeItems: 'center',
                            border: '1px solid var(--border)',
                            background: 'var(--primary-soft)',
                            boxShadow: 'var(--shadow-lg)',
                            animation: 'access-wave 1800ms ease-in-out infinite',
                        }}>
                            <div style={{ position: 'relative', width: '56px', height: '56px', display: 'grid', placeItems: 'center' }}>
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <span
                                        key={`login-loader-particle-${i}`}
                                        style={{
                                            position: 'absolute',
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '999px',
                                            background: i % 2 === 0 ? 'var(--primary)' : 'var(--accent)',
                                            opacity: 0.7,
                                            boxShadow: 'var(--shadow-glow)',
                                            animation: `login-loader-orbit ${1.8 + i * 0.12}s linear ${i * 0.14}s infinite`,
                                        }}
                                    />
                                ))}
                                <span style={{
                                    position: 'absolute',
                                    inset: 0,
                                    borderRadius: '999px',
                                    border: '2px solid var(--border)',
                                    borderTopColor: 'var(--primary)',
                                    animation: 'login-loader-ring 1s linear infinite',
                                }} />
                                <span style={{
                                    position: 'absolute',
                                    inset: '7px',
                                    borderRadius: '999px',
                                    border: '2px solid var(--border)',
                                    borderBottomColor: 'var(--accent)',
                                    animation: 'login-loader-ring-rev 1.25s linear infinite',
                                }} />
                                <Loader2 size={20} style={{ color: 'var(--primary)', animation: 'spin 1.3s linear infinite' }} />
                            </div>
                        </div>
                        <h3 style={{ margin: 0, fontSize: '30px', fontFamily: 'var(--font-heading)', color: 'var(--text)' }}>Bienvenido</h3>
                        <p style={{ margin: '8px 0 0', fontSize: '14px', color: 'var(--text-muted)' }}>{sessionGreeting}</p>

                        <div style={{
                            margin: '16px auto 0',
                            width: '250px',
                            height: '5px',
                            borderRadius: '999px',
                            overflow: 'hidden',
                            border: '1px solid var(--border)',
                            background: 'var(--surface-2)',
                        }}>
                            <span style={{
                                display: 'block',
                                width: '100%',
                                height: '100%',
                                borderRadius: '999px',
                                background: 'var(--grad-primary)',
                                transformOrigin: 'left center',
                                animation: 'access-progress 2000ms linear forwards',
                            }} />
                        </div>
                    </div>

                    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
                        {Array.from({ length: 14 }).map((_, i) => (
                            <span
                                key={`access-particle-${i}`}
                                style={{
                                    position: 'absolute',
                                    left: `${8 + ((i * 6.4) % 84)}%`,
                                    top: `${10 + ((i * 8.8) % 76)}%`,
                                    width: `${6 + (i % 3) * 2}px`,
                                    height: `${6 + (i % 3) * 2}px`,
                                    borderRadius: '999px',
                                    background: i % 2 === 0 ? 'var(--primary)' : 'var(--accent)',
                                    opacity: 0.5,
                                    boxShadow: 'var(--shadow-glow)',
                                    animation: `access-particles ${1.8 + (i % 4) * 0.2}s ease-in-out ${i * 0.1}s infinite alternate`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
