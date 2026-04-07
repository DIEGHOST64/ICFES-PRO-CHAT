import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GraduationCap, User, Lock, Eye, EyeOff, Loader2, Compass, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';
import { InstitutionalLogo } from '../components/InstitutionalLogo';

const PROGRAMAS = [
    'Ingeniería de Sistemas',
    'Contaduría Pública',
    'Administración de Empresas',
    'Derecho',
    'Enfermería',
    'Psicología',
    'Ingeniería Ambiental',
    'Trabajo Social',
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
            background: 'radial-gradient(circle at 8% 12%, #e6ecef 0%, transparent 38%), radial-gradient(circle at 90% 85%, #dde4e7 0%, transparent 36%), linear-gradient(155deg, #f3f5f6 0%, #eef1f3 45%, #e9eef0 100%)',
            position: 'relative',
            overflow: 'hidden',
        }}>
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                <div data-motion="blob" style={{
                    position: 'absolute', top: '-10%', right: '-12%',
                    width: '520px', height: '520px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(84,108,122,0.20) 0%, rgba(84,108,122,0.04) 45%, transparent 74%)',
                    filter: 'blur(24px)', animation: 'aurora-float 12s ease-in-out infinite',
                }} />
                <div data-motion="blob" style={{
                    position: 'absolute', left: '-8%', bottom: '-14%',
                    width: '460px', height: '460px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(100,124,114,0.18) 0%, rgba(100,124,114,0.03) 46%, transparent 76%)',
                    filter: 'blur(18px)', animation: 'aurora-float 14s ease-in-out infinite reverse',
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
                <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center', marginBottom: '2px' }}>
                    <InstitutionalLogo size={148} />
                </div>

                <section data-motion="panel" style={{
                    borderRadius: '28px',
                    padding: '36px',
                    border: '1px solid rgba(255,255,255,0.65)',
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.84) 0%, rgba(245,248,250,0.78) 100%)',
                    boxShadow: '0 28px 60px rgba(8, 33, 64, 0.12)',
                    backdropFilter: 'blur(8px)',
                    order: 2,
                }}>
                    <div style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        fontSize: '12px',
                        fontWeight: 700,
                        color: '#3f5566',
                        background: 'rgba(63,85,102,0.09)',
                        border: '1px solid rgba(63,85,102,0.16)',
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
                        color: '#1f2d38',
                        marginBottom: '14px',
                        letterSpacing: '-0.03em',
                    }}>
                        Bienvenido a Ascenso Pro,
                        <br />
                        tu ruta para mejorar en Saber Pro.
                    </h1>

                    <p style={{
                        color: '#455a68',
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
                                color: '#334652',
                                fontSize: '14px',
                            }}>
                                <span style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    background: 'linear-gradient(120deg, #4a6274, #6f8b84)',
                                    boxShadow: '0 0 0 4px rgba(74,98,116,0.14)',
                                }} />
                                {item}
                            </div>
                        ))}
                    </div>
                </section>

                <section data-motion="panel" className="animate-scale-in" style={{
                    borderRadius: '28px',
                    padding: '24px',
                    border: '1px solid rgba(255,255,255,0.75)',
                    background: 'linear-gradient(150deg, rgba(255,255,255,0.92) 0%, rgba(245,248,250,0.86) 100%)',
                    boxShadow: '0 26px 60px rgba(12, 27, 51, 0.14)',
                    backdropFilter: 'blur(9px)',
                    order: 1,
                }}>
                    <div style={{ marginBottom: '18px' }}>
                        <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#3e5566',
                            background: 'rgba(62,85,102,0.10)',
                            borderRadius: '999px',
                            padding: '5px 10px',
                            marginBottom: '10px',
                        }}>
                            <GraduationCap size={12} /> UDEC · Fusagasuga
                        </div>
                        <h2 style={{ fontSize: '26px', color: '#1f2d38', marginBottom: '4px' }}>Ascenso Pro</h2>
                        <p style={{ color: '#5a6f84', fontSize: '13px' }}>Empieza tu plan de estudio en pocos segundos.</p>
                    </div>

                    <div style={{
                        display: 'flex',
                        gap: '6px',
                        background: 'rgba(46,63,76,0.08)',
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
                                    background: tab === t ? 'linear-gradient(120deg, #314859, #435c6d)' : 'transparent',
                                    color: tab === t ? '#fff' : '#4f6277',
                                    transition: 'var(--t-base)',
                                }}
                            >
                                {t === 'login' ? 'Ya tengo cuenta' : 'Crear cuenta'}
                            </button>
                        ))}
                    </div>

                    {error && (
                        <div style={{
                            width: '100%',
                            padding: '10px 12px',
                            marginBottom: '12px',
                            borderRadius: '10px',
                            fontSize: '13px',
                            color: '#9d1f1f',
                            border: '1px solid #f8b4b4',
                            background: '#fff1f2',
                        }}>
                            {error}
                        </div>
                    )}

                    {tab === 'login' && (
                        <form data-motion="card" onSubmit={handleLogin} className="animate-fade-up">
                            <div style={{ marginBottom: '12px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>
                                    Numero de cedula
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <User size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }} />
                                    <input className="input" style={{ paddingLeft: '38px', background: '#fff', borderColor: '#dce6f0' }}
                                        placeholder="Ej: 1234567890"
                                        value={cedula} onChange={e => setCedula(e.target.value)} required />
                                </div>
                            </div>

                            <div style={{ marginBottom: '18px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>
                                    Clave secreta
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }} />
                                    <input className="input" style={{ paddingLeft: '38px', paddingRight: '42px', background: '#fff', borderColor: '#dce6f0' }}
                                        type={showKey ? 'text' : 'password'}
                                        placeholder="Ingresa tu clave"
                                        value={clave} onChange={e => setClave(e.target.value)} required />
                                    <button type="button" onClick={() => setShowKey(s => !s)}
                                        style={{ position: 'absolute', right: '7px', top: '50%', transform: 'translateY(-50%)', color: '#6d8298', width: '28px', height: '28px', borderRadius: '8px' }}
                                        aria-label={showKey ? 'Ocultar clave' : 'Mostrar clave'}>
                                        {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                                    </button>
                                </div>
                                <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#7a8ea3' }}>
                                    Si tu cuenta es antigua, tu clave puede tener más de 1 carácter.
                                </p>
                            </div>

                            <button className="btn" type="submit" disabled={loading}
                                style={{
                                    width: '100%',
                                    justifyContent: 'center',
                                    height: '44px',
                                    color: '#fff',
                                    fontWeight: 700,
                                    background: 'linear-gradient(120deg, #314859 0%, #425c6e 100%)',
                                    boxShadow: '0 10px 24px rgba(49, 72, 89, 0.30)',
                                }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <>Entrar al asistente <ArrowRight size={16} /></>}
                            </button>
                        </form>
                    )}

                    {tab === 'register' && (
                        <form data-motion="card" onSubmit={handleRegister} className="animate-fade-up">
                            {[
                                { label: 'Numero de cedula', val: regCedula, set: setRegCedula, placeholder: 'Ej: 1234567890', icon: <User size={15} /> },
                                { label: 'Nombre completo', val: regNombre, set: setRegNombre, placeholder: 'Tu nombre completo', icon: <GraduationCap size={15} /> },
                            ].map(({ label, val, set, placeholder, icon }) => (
                                <div key={label} style={{ marginBottom: '12px' }}>
                                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>{label}</label>
                                    <div style={{ position: 'relative' }}>
                                        <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }}>{icon}</span>
                                        <input className="input" style={{ paddingLeft: '38px', background: '#fff', borderColor: '#dce6f0' }} placeholder={placeholder} value={val} onChange={e => set(e.target.value)} required />
                                    </div>
                                </div>
                            ))}

                            <div style={{ marginBottom: '12px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>Programa academico</label>
                                <select className="input" style={{ background: '#fff', borderColor: '#dce6f0' }} value={regPrograma} onChange={e => setRegPrograma(e.target.value)} required>
                                    <option value="">Selecciona tu programa…</option>
                                    {PROGRAMAS.map(p => <option key={p} value={p}>{p}</option>)}
                                </select>
                            </div>

                            <div style={{ marginBottom: '18px' }}>
                                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>
                                    Clave secreta <span style={{ fontWeight: 500, color: '#7a8ea3' }}>(1 caracter)</span>
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }} />
                                    <input className="input" style={{ paddingLeft: '38px', background: '#fff', borderColor: '#dce6f0' }}
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
                                    background: 'linear-gradient(120deg, #4a6f65 0%, #557f73 100%)',
                                    boxShadow: '0 10px 24px rgba(74, 111, 101, 0.28)',
                                }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Crear cuenta'}
                            </button>
                        </form>
                    )}

                    <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e5edf5' }}>
                        <Link to="/coordinador" style={{ fontSize: '13px', color: '#496278', fontWeight: 600 }}>
                            Eres coordinador? Accede aqui
                        </Link>
                    </div>

                    <p style={{ textAlign: 'center', marginTop: '14px', fontSize: '11px', color: '#7c8fa4' }}>
                        Datos protegidos bajo Ley 1581 de 2012
                    </p>
                </section>

                <div style={{ position: 'absolute', left: 0, right: 0, bottom: '18px', textAlign: 'center' }}>
                    <p style={{ margin: 0, color: '#4f6576', fontSize: '12px', fontWeight: 700, letterSpacing: '0.04em' }}>
                        UNIVERSIDAD DE CUNDINAMARCA
                    </p>
                    <p style={{ margin: '1px 0 0', color: '#4f6576', opacity: 0.85, fontSize: '11px' }}>
                        Ascenso Pro
                    </p>
                </div>
            </div>

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
                @keyframes aurora-float {
                    0%, 100% { transform: translate3d(0, 0, 0); }
                    50% { transform: translate3d(12px, -16px, 0); }
                }
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
                    div[style*='grid-template-columns: 1.1fr 0.9fr'] {
                        grid-template-columns: 1fr !important;
                    }
                    section[style*='line-height: 1.05'] {
                        order: 2;
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
                    background: 'radial-gradient(circle at 18% 20%, rgba(159,195,221,0.3), transparent 45%), radial-gradient(circle at 82% 78%, rgba(161,210,188,0.28), transparent 46%), linear-gradient(155deg, rgba(37,53,64,0.86), rgba(32,52,66,0.9))',
                    backdropFilter: 'blur(5px)',
                    animation: 'access-fade 2000ms ease forwards',
                }}>
                    <div style={{ textAlign: 'center', color: '#edf6fb', position: 'relative', zIndex: 2, padding: '16px' }}>
                        <div style={{
                            width: '94px',
                            height: '94px',
                            borderRadius: '999px',
                            margin: '0 auto 14px',
                            display: 'grid',
                            placeItems: 'center',
                            border: '1px solid rgba(255,255,255,0.3)',
                            background: 'linear-gradient(150deg, rgba(255,255,255,0.18), rgba(212,240,255,0.1))',
                            boxShadow: '0 16px 32px rgba(8, 23, 35, 0.34)',
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
                                            background: i % 2 === 0 ? 'rgba(148, 201, 235, 0.88)' : 'rgba(149, 220, 186, 0.84)',
                                            boxShadow: '0 0 8px rgba(255,255,255,0.35)',
                                            animation: `login-loader-orbit ${1.8 + i * 0.12}s linear ${i * 0.14}s infinite`,
                                        }}
                                    />
                                ))}
                                <span style={{
                                    position: 'absolute',
                                    inset: 0,
                                    borderRadius: '999px',
                                    border: '2px solid rgba(146, 197, 230, 0.28)',
                                    borderTopColor: '#8fbde0',
                                    animation: 'login-loader-ring 1s linear infinite',
                                }} />
                                <span style={{
                                    position: 'absolute',
                                    inset: '7px',
                                    borderRadius: '999px',
                                    border: '2px solid rgba(146, 212, 184, 0.28)',
                                    borderBottomColor: '#8fd2b8',
                                    animation: 'login-loader-ring-rev 1.25s linear infinite',
                                }} />
                                <Loader2 size={20} style={{ color: '#dff1ff', animation: 'spin 1.3s linear infinite' }} />
                            </div>
                        </div>
                        <h3 style={{ margin: 0, fontSize: '30px', fontFamily: 'var(--font-heading)' }}>Bienvenido</h3>
                        <p style={{ margin: '8px 0 0', fontSize: '14px', opacity: 0.92 }}>{sessionGreeting}</p>

                        <div style={{
                            margin: '16px auto 0',
                            width: '250px',
                            height: '5px',
                            borderRadius: '999px',
                            overflow: 'hidden',
                            border: '1px solid rgba(255,255,255,0.24)',
                            background: 'rgba(255,255,255,0.16)',
                        }}>
                            <span style={{
                                display: 'block',
                                width: '100%',
                                height: '100%',
                                borderRadius: '999px',
                                background: 'linear-gradient(90deg, #94c6e9, #9ddcc0)',
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
                                    background: i % 2 === 0 ? 'rgba(150,209,244,0.72)' : 'rgba(157,224,192,0.68)',
                                    boxShadow: i % 2 === 0 ? '0 0 12px rgba(139,206,248,0.56)' : '0 0 12px rgba(143,224,188,0.5)',
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
