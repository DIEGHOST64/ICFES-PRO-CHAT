import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { BookOpen, User, Lock, GraduationCap, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';

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
    const navigate = useNavigate();
    const { loginStudent } = useAuth();
    const [tab, setTab] = useState<'login' | 'register'>('login');
    const [showKey, setShowKey] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Login state
    const [cedula, setCedula] = useState('');
    const [clave, setClave] = useState('');

    // Register state
    const [regCedula, setRegCedula] = useState('');
    const [regNombre, setRegNombre] = useState('');
    const [regPrograma, setRegPrograma] = useState('');
    const [regClave, setRegClave] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const res = await authAPI.loginStudent({ cedula, clave_secreta: clave });
            loginStudent(res.data.token, res.data.student);
            navigate('/chat');
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
            navigate('/chat');
        } catch (err: any) {
            setError(err.response?.data?.message ?? 'Error en el registro.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh', display: 'flex', alignItems: 'center',
            justifyContent: 'center', padding: 'var(--space-lg)',
            background: 'var(--bg)',
        }}>
            {/* Fondo decorativo — manchas de color suaves */}
            <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
                <div style={{
                    position: 'absolute', top: '-15%', right: '-8%',
                    width: '480px', height: '480px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(79,70,229,0.10) 0%, transparent 70%)',
                }} />
                <div style={{
                    position: 'absolute', bottom: '-15%', left: '-8%',
                    width: '420px', height: '420px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(5,150,105,0.10) 0%, transparent 70%)',
                }} />
                {/* Puntos decorativos tipo "estudiantil" */}
                <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0, opacity: 0.04 }}>
                    <pattern id="dots" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">
                        <circle cx="3" cy="3" r="2" fill="var(--primary)" />
                    </pattern>
                    <rect width="100%" height="100%" fill="url(#dots)" />
                </svg>
            </div>

            <div className="animate-scale-in" style={{
                width: '100%', maxWidth: '440px', position: 'relative', zIndex: 1,
            }}>
                {/* Logo + header */}
                <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)' }}>
                    {/* Badge UDEC */}
                    <div style={{
                        display: 'inline-flex', alignItems: 'center', gap: '6px',
                        background: 'var(--accent-soft)', color: 'var(--accent)',
                        border: '1px solid rgba(5,150,105,0.25)',
                        borderRadius: 'var(--radius-full)', padding: '4px 12px',
                        fontSize: '11px', fontWeight: 600, marginBottom: 'var(--space-md)',
                        letterSpacing: '0.04em',
                    }}>
                        <GraduationCap size={12} /> UDEC · Fusagasugá
                    </div>
                    <div style={{
                        display: 'inline-flex', padding: '16px',
                        background: 'var(--grad-primary)', borderRadius: 'var(--radius-xl)',
                        marginBottom: 'var(--space-md)',
                        boxShadow: '0 8px 24px rgba(79,70,229,0.30)',
                    }}>
                        <BookOpen size={30} color="#fff" />
                    </div>
                    <h1 style={{ fontSize: '26px', marginBottom: '6px', letterSpacing: '-0.5px' }}>Asistente Saber Pro</h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: 1.5 }}>
                        Prepárate con IA para tu examen de estado
                    </p>
                </div>

                {/* Card */}
                <div className="card" style={{ padding: 'var(--space-xl)', boxShadow: 'var(--shadow-lg)', borderTop: '3px solid var(--primary)' }}>
                    {/* Tabs */}
                    <div style={{
                        display: 'flex', background: 'var(--surface-2)',
                        borderRadius: 'var(--radius-md)', padding: '4px',
                        marginBottom: 'var(--space-xl)', gap: '4px',
                    }}>
                        {(['login', 'register'] as const).map(t => (
                            <button key={t}
                                onClick={() => { setTab(t); setError(''); }}
                                style={{
                                    flex: 1, padding: '8px',
                                    borderRadius: 'calc(var(--radius-md) - 2px)',
                                    fontSize: '14px', fontWeight: 600,
                                    background: tab === t ? 'var(--primary)' : 'transparent',
                                    color: tab === t ? '#fff' : 'var(--text-muted)',
                                    transition: 'var(--t-base)',
                                }}
                            >
                                {t === 'login' ? 'Iniciar Sesión' : 'Registrarse'}
                            </button>
                        ))}
                    </div>

                    {error && (
                        <div className="badge badge-danger animate-fade-up" style={{
                            width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)',
                            marginBottom: 'var(--space-md)', fontSize: '13px',
                        }}>
                            {error}
                        </div>
                    )}

                    {/* Login Form */}
                    {tab === 'login' && (
                        <form onSubmit={handleLogin} className="animate-fade-up">
                            <div style={{ marginBottom: 'var(--space-md)' }}>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Número de Cédula
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <User size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '40px' }}
                                        placeholder="Ej: 1234567890"
                                        value={cedula} onChange={e => setCedula(e.target.value)} required />
                                </div>
                            </div>

                            <div style={{ marginBottom: 'var(--space-xl)' }}>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Clave Secreta
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '40px', paddingRight: '44px' }}
                                        type={showKey ? 'text' : 'password'} maxLength={1}
                                        placeholder="1 carácter"
                                        value={clave} onChange={e => setClave(e.target.value)} required />
                                    <button type="button" onClick={() => setShowKey(s => !s)} className="btn-icon"
                                        style={{ position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)', border: 'none', background: 'transparent', width: '32px', height: '32px' }}
                                        aria-label={showKey ? 'Ocultar clave' : 'Mostrar clave'}>
                                        {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                                    </button>
                                </div>
                            </div>

                            <button className="btn btn-primary" type="submit" disabled={loading}
                                style={{ width: '100%', justifyContent: 'center', height: '44px' }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Entrar al Asistente'}
                            </button>
                        </form>
                    )}

                    {/* Register Form */}
                    {tab === 'register' && (
                        <form onSubmit={handleRegister} className="animate-fade-up">
                            {[
                                { label: 'Número de Cédula', val: regCedula, set: setRegCedula, placeholder: 'Ej: 1234567890', icon: <User size={16} /> },
                                { label: 'Nombre Completo', val: regNombre, set: setRegNombre, placeholder: 'Tu nombre completo', icon: <GraduationCap size={16} /> },
                            ].map(({ label, val, set, placeholder, icon }) => (
                                <div key={label} style={{ marginBottom: 'var(--space-md)' }}>
                                    <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>{label}</label>
                                    <div style={{ position: 'relative' }}>
                                        <span style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }}>{icon}</span>
                                        <input className="input" style={{ paddingLeft: '40px' }} placeholder={placeholder} value={val} onChange={e => set(e.target.value)} required />
                                    </div>
                                </div>
                            ))}

                            <div style={{ marginBottom: 'var(--space-md)' }}>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>Programa Académico</label>
                                <select className="input" value={regPrograma} onChange={e => setRegPrograma(e.target.value)} required>
                                    <option value="">Selecciona tu programa…</option>
                                    {PROGRAMAS.map(p => <option key={p} value={p}>{p}</option>)}
                                </select>
                            </div>

                            <div style={{ marginBottom: 'var(--space-xl)' }}>
                                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>
                                    Clave Secreta <span style={{ fontWeight: 400, color: 'var(--text-hint)' }}>(1 carácter: letra o símbolo)</span>
                                </label>
                                <div style={{ position: 'relative' }}>
                                    <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                    <input className="input" style={{ paddingLeft: '40px' }}
                                        type={showKey ? 'text' : 'password'} maxLength={1}
                                        placeholder="Ej: @ o A"
                                        value={regClave} onChange={e => setRegClave(e.target.value)} required />
                                </div>
                                <p style={{ fontSize: '12px', color: 'var(--text-hint)', marginTop: '6px' }}>
                                    Guárdala bien — junto con tu cédula, será tu contraseña de acceso.
                                </p>
                            </div>

                            <button className="btn btn-primary" type="submit" disabled={loading}
                                style={{ width: '100%', justifyContent: 'center', height: '44px' }}>
                                {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Crear Cuenta'}
                            </button>
                        </form>
                    )}

                    {/* Coordinador link */}
                    <div style={{ textAlign: 'center', marginTop: 'var(--space-lg)', paddingTop: 'var(--space-lg)', borderTop: '1px solid var(--border)' }}>
                        <Link to="/coordinador" style={{ fontSize: '13px', color: 'var(--text-muted)', transition: 'var(--t-fast)' }}
                            onMouseOver={e => (e.currentTarget.style.color = 'var(--primary)')}
                            onMouseOut={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
                            ¿Eres coordinador? Accede aquí →
                        </Link>
                    </div>
                </div>

                <p style={{ textAlign: 'center', marginTop: 'var(--space-lg)', fontSize: '12px', color: 'var(--text-hint)' }}>
                    Datos protegidos bajo Ley 1581 de 2012
                </p>
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};
