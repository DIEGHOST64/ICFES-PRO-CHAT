import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, Loader2, BookOpen, Compass, ArrowRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';
import { useGsapPageMotion } from '../hooks/useGsapPageMotion';
import { InstitutionalLogo } from '../components/InstitutionalLogo';

export const CoordinadorLoginPage: React.FC = () => {
    const pageRef = useRef<HTMLDivElement>(null);
    const accessTimerRef = useRef<number | null>(null);
    const navigate = useNavigate();
    const { loginCoordinator } = useAuth();
    // tema disponible pero no usado directamente aquí — toggle en header superior
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [startingCoordinatorSession, setStartingCoordinatorSession] = useState(false);
    const [sessionGreeting, setSessionGreeting] = useState('Ingresando al panel de coordinacion...');

    useGsapPageMotion(pageRef);

    useEffect(() => {
        return () => {
            if (accessTimerRef.current !== null) {
                window.clearTimeout(accessTimerRef.current);
            }
        };
    }, []);

    const beginCoordinatorSession = (coordinatorName?: string, coordinatorEmail?: string) => {
        const fallback = coordinatorEmail?.split('@')[0] || 'coordinador';
        const firstName = coordinatorName?.split(' ')[0] || fallback;
        setSessionGreeting(`${firstName}, cargando tablero estrategico...`);
        setStartingCoordinatorSession(true);
        accessTimerRef.current = window.setTimeout(() => {
            navigate('/coordinador/dashboard');
        }, 2000);
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const cleanEmail = email.trim();
            const cleanPassword = password.trim();
            const res = await authAPI.loginCoordinator({ email: cleanEmail, password: cleanPassword });
            loginCoordinator(res.data.token, res.data.coordinator);
            beginCoordinatorSession(res.data.coordinator?.nombre, cleanEmail);
        } catch (err: any) {
            setError(err.response?.data?.message ?? 'Credenciales incorrectas.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div ref={pageRef} style={{
            minHeight: '100vh',
            padding: '24px',
            background: 'radial-gradient(circle at 14% 12%, #dbe4ea 0%, transparent 36%), radial-gradient(circle at 88% 85%, #e2e8e2 0%, transparent 32%), linear-gradient(155deg, #eef2f4 0%, #e8edf0 45%, #e4eaed 100%)',
            position: 'relative',
            overflow: 'hidden',
        }}>
            <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
                <div data-motion="blob" style={{
                    position: 'absolute', top: '-14%', right: '-10%',
                    width: '500px', height: '500px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(58,90,118,0.20) 0%, rgba(58,90,118,0.04) 48%, transparent 76%)',
                    filter: 'blur(24px)', animation: 'aurora-float 13s ease-in-out infinite',
                }} />
                <div data-motion="blob" style={{
                    position: 'absolute', left: '-10%', bottom: '-16%',
                    width: '430px', height: '430px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(75,102,87,0.20) 0%, rgba(75,102,87,0.05) 48%, transparent 74%)',
                    filter: 'blur(20px)', animation: 'aurora-float 15s ease-in-out infinite reverse',
                }} />
            </div>

            <div data-motion="headline" style={{
                maxWidth: '1080px',
                margin: '0 auto',
                minHeight: 'calc(100vh - 48px)',
                display: 'grid',
                gridTemplateColumns: '1fr 420px',
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
                    border: '1px solid rgba(255,255,255,0.66)',
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.84) 0%, rgba(245,248,250,0.8) 100%)',
                    boxShadow: '0 28px 60px rgba(8, 33, 64, 0.12)',
                    backdropFilter: 'blur(8px)',
                }}>
                    <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '18px',
                        fontSize: '12px', fontWeight: 700, color: '#3f5566',
                        background: 'rgba(63,85,102,0.09)', border: '1px solid rgba(63,85,102,0.16)',
                        padding: '6px 12px', borderRadius: '999px', letterSpacing: '0.03em',
                    }}>
                        <Compass size={14} /> MODO COORDINACION ACADEMICA
                    </div>

                    <h1 style={{
                        fontSize: 'clamp(30px, 4vw, 48px)', lineHeight: 1.05,
                        color: '#1f2d38', marginBottom: '14px', letterSpacing: '-0.03em',
                    }}>
                        Gestiona el progreso
                        <br />
                        de tus estudiantes
                        <br />
                        en Ascenso Pro.
                    </h1>

                    <p style={{ color: '#455a68', fontSize: '16px', maxWidth: '52ch', marginBottom: '24px' }}>
                        Accede al panel de coordinacion para revisar indicadores, acompanar resultados y orientar acciones de mejora para Saber Pro.
                    </p>

                    <div style={{ display: 'grid', gap: '12px', maxWidth: '560px' }}>
                        {[
                            'Seguimiento de metricas por programa y cohorte.',
                            'Vision central del avance de practica y consultas.',
                            'Herramientas para decisiones academicas con evidencia.',
                        ].map((item) => (
                            <div key={item} style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#334652', fontSize: '14px' }}>
                                <span style={{
                                    width: '8px', height: '8px', borderRadius: '50%',
                                    background: 'linear-gradient(120deg, #3a5a76, #5a7c70)',
                                    boxShadow: '0 0 0 4px rgba(58,90,118,0.14)',
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
                    background: 'linear-gradient(150deg, rgba(255,255,255,0.93) 0%, rgba(245,248,250,0.88) 100%)',
                    boxShadow: '0 26px 60px rgba(12, 27, 51, 0.14)',
                    backdropFilter: 'blur(9px)',
                }}>
                    <div style={{ marginBottom: '18px' }}>
                        <div style={{
                            display: 'inline-flex', alignItems: 'center', gap: '6px', marginBottom: '10px',
                            fontSize: '11px', fontWeight: 700, color: '#3e5566',
                            background: 'rgba(62,85,102,0.10)', borderRadius: '999px', padding: '5px 10px',
                        }}>
                            <ShieldCheck size={12} /> ACCESO RESTRINGIDO
                        </div>
                        <h2 style={{ fontSize: '26px', color: '#1f2d38', marginBottom: '4px' }}>Panel Coordinador</h2>
                        <p style={{ color: '#5a6f84', fontSize: '13px' }}>Ingresa con tus credenciales institucionales.</p>
                    </div>

                    {error && (
                        <div style={{
                            width: '100%', padding: '10px 12px', marginBottom: '12px', borderRadius: '10px',
                            fontSize: '13px', color: '#9d1f1f', border: '1px solid #f8b4b4', background: '#fff1f2',
                        }}>
                            {error}
                        </div>
                    )}

                    <form data-motion="card" onSubmit={handleLogin} className="animate-fade-up">
                        <div style={{ marginBottom: '12px' }}>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>
                                Correo institucional
                            </label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }} />
                                <input
                                    className="input"
                                    style={{ paddingLeft: '38px', background: '#fff', borderColor: '#dce6f0' }}
                                    type="email"
                                    placeholder="coordinador@ucundinamarca.edu.co"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div style={{ marginBottom: '18px' }}>
                            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#4a6076' }}>
                                Contrasena
                            </label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7a8ea3' }} />
                                <input
                                    className="input"
                                    style={{ paddingLeft: '38px', background: '#fff', borderColor: '#dce6f0' }}
                                    type="password"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <button
                            className="btn"
                            type="submit"
                            disabled={loading}
                            style={{
                                width: '100%',
                                justifyContent: 'center',
                                height: '44px',
                                color: '#fff',
                                fontWeight: 700,
                                background: 'linear-gradient(120deg, #365064 0%, #486579 100%)',
                                boxShadow: '0 10px 24px rgba(53, 78, 98, 0.30)',
                            }}
                        >
                            {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <>Entrar al panel <ArrowRight size={16} /></>}
                        </button>
                    </form>

                    <div style={{ textAlign: 'center', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e5edf5' }}>
                        <button
                            onClick={() => navigate('/login')}
                            style={{ fontSize: '13px', color: '#496278', fontWeight: 600, cursor: 'pointer', background: 'none', border: 'none' }}
                        >
                            <BookOpen size={13} style={{ display: 'inline', marginRight: '4px' }} />
                            Eres estudiante? Accede aqui
                        </button>
                    </div>

                    <p style={{ textAlign: 'center', marginTop: '14px', fontSize: '11px', color: '#7c8fa4' }}>
                        Acceso institucional protegido
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
                @keyframes coordinator-access-fade {
                    0% { opacity: 0; }
                    12% { opacity: 1; }
                    88% { opacity: 1; }
                    100% { opacity: 0.96; }
                }
                @keyframes coordinator-access-wave {
                    0%, 100% { transform: translateY(0) scale(1); opacity: 0.65; }
                    50% { transform: translateY(-8px) scale(1.04); opacity: 1; }
                }
                @keyframes coordinator-access-progress {
                    0% { transform: scaleX(0); }
                    100% { transform: scaleX(1); }
                }
                @keyframes coordinator-loader-ring {
                    to { transform: rotate(360deg); }
                }
                @keyframes coordinator-loader-ring-rev {
                    to { transform: rotate(-360deg); }
                }
                @keyframes coordinator-loader-orbit {
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
                @keyframes coordinator-access-particles {
                    0% { transform: translate3d(0, 0, 0) scale(0.88); opacity: 0.35; }
                    100% { transform: translate3d(10px, -14px, 0) scale(1.16); opacity: 0.95; }
                }
                @media (max-width: 980px) {
                    .animate-scale-in {
                        animation-duration: 220ms;
                    }
                }
                @media (max-width: 900px) {
                    div[style*='grid-template-columns: 1fr 420px'] {
                        grid-template-columns: 1fr !important;
                    }
                }
            `}</style>

            {startingCoordinatorSession && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 110,
                    display: 'grid',
                    placeItems: 'center',
                    background: 'radial-gradient(circle at 18% 20%, rgba(159,195,221,0.3), transparent 45%), radial-gradient(circle at 82% 78%, rgba(161,210,188,0.28), transparent 46%), linear-gradient(155deg, rgba(37,53,64,0.86), rgba(32,52,66,0.9))',
                    backdropFilter: 'blur(5px)',
                    animation: 'coordinator-access-fade 2000ms ease forwards',
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
                            animation: 'coordinator-access-wave 1800ms ease-in-out infinite',
                        }}>
                            <div style={{ position: 'relative', width: '56px', height: '56px', display: 'grid', placeItems: 'center' }}>
                                {Array.from({ length: 6 }).map((_, i) => (
                                    <span
                                        key={`coordinator-loader-particle-${i}`}
                                        style={{
                                            position: 'absolute',
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '999px',
                                            background: i % 2 === 0 ? 'rgba(148, 201, 235, 0.88)' : 'rgba(149, 220, 186, 0.84)',
                                            boxShadow: '0 0 8px rgba(255,255,255,0.35)',
                                            animation: `coordinator-loader-orbit ${1.8 + i * 0.12}s linear ${i * 0.14}s infinite`,
                                        }}
                                    />
                                ))}
                                <span style={{
                                    position: 'absolute',
                                    inset: 0,
                                    borderRadius: '999px',
                                    border: '2px solid rgba(146, 197, 230, 0.28)',
                                    borderTopColor: '#8fbde0',
                                    animation: 'coordinator-loader-ring 1s linear infinite',
                                }} />
                                <span style={{
                                    position: 'absolute',
                                    inset: '7px',
                                    borderRadius: '999px',
                                    border: '2px solid rgba(146, 212, 184, 0.28)',
                                    borderBottomColor: '#8fd2b8',
                                    animation: 'coordinator-loader-ring-rev 1.25s linear infinite',
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
                                animation: 'coordinator-access-progress 2000ms linear forwards',
                            }} />
                        </div>
                    </div>

                    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
                        {Array.from({ length: 14 }).map((_, i) => (
                            <span
                                key={`coordinator-access-particle-${i}`}
                                style={{
                                    position: 'absolute',
                                    left: `${8 + ((i * 6.4) % 84)}%`,
                                    top: `${10 + ((i * 8.8) % 76)}%`,
                                    width: `${6 + (i % 3) * 2}px`,
                                    height: `${6 + (i % 3) * 2}px`,
                                    borderRadius: '999px',
                                    background: i % 2 === 0 ? 'rgba(150,209,244,0.72)' : 'rgba(157,224,192,0.68)',
                                    boxShadow: i % 2 === 0 ? '0 0 12px rgba(139,206,248,0.56)' : '0 0 12px rgba(143,224,188,0.5)',
                                    animation: `coordinator-access-particles ${1.8 + (i % 4) * 0.2}s ease-in-out ${i * 0.1}s infinite alternate`,
                                }}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};
