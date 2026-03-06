import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, Lock, Mail, Loader2, BookOpen } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/client';

export const CoordinadorLoginPage: React.FC = () => {
    const navigate = useNavigate();
    const { loginCoordinator } = useAuth();
    // tema disponible pero no usado directamente aquí — toggle en header superior
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const res = await authAPI.loginCoordinator({ email, password });
            loginCoordinator(res.data.token, res.data.coordinator);
            navigate('/coordinador/dashboard');
        } catch (err: any) {
            setError(err.response?.data?.message ?? 'Credenciales incorrectas.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-lg)' }}>
            <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}>
                <div style={{ position: 'absolute', top: '-15%', right: '-10%', width: '450px', height: '450px', borderRadius: '50%', background: 'radial-gradient(circle, var(--primary-glow) 0%, transparent 70%)' }} />
            </div>

            <div className="animate-scale-in" style={{ width: '100%', maxWidth: '420px', position: 'relative', zIndex: 1 }}>
                <div style={{ textAlign: 'center', marginBottom: 'var(--space-xl)' }}>
                    <div style={{ display: 'inline-flex', padding: '14px', background: 'var(--accent)', borderRadius: 'var(--radius-lg)', marginBottom: 'var(--space-md)', boxShadow: '0 0 20px rgba(16,185,129,0.35)' }}>
                        <BarChart3 size={28} color="#fff" />
                    </div>
                    <h1 style={{ fontSize: '26px', marginBottom: '6px' }}>Panel Coordinador</h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Asistente Saber Pro · UCundinamarca</p>
                </div>

                <div className="card" style={{ padding: 'var(--space-xl)' }}>
                    {error && (
                        <div className="badge badge-danger animate-fade-up" style={{ width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-md)', fontSize: '13px' }}>
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleLogin}>
                        <div style={{ marginBottom: 'var(--space-md)' }}>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>Correo Institucional</label>
                            <div style={{ position: 'relative' }}>
                                <Mail size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                <input className="input" style={{ paddingLeft: '40px' }} type="email" placeholder="coordinador@ucundinamarca.edu.co" value={email} onChange={e => setEmail(e.target.value)} required />
                            </div>
                        </div>

                        <div style={{ marginBottom: 'var(--space-xl)' }}>
                            <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-muted)' }}>Contraseña</label>
                            <div style={{ position: 'relative' }}>
                                <Lock size={16} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-hint)' }} />
                                <input className="input" style={{ paddingLeft: '40px' }} type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
                            </div>
                        </div>

                        <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center', height: '44px' }}>
                            {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : 'Acceder al Panel'}
                        </button>
                    </form>

                    <div style={{ textAlign: 'center', marginTop: 'var(--space-lg)', paddingTop: 'var(--space-lg)', borderTop: '1px solid var(--border)' }}>
                        <button onClick={() => navigate('/login')} style={{ fontSize: '13px', color: 'var(--text-muted)', cursor: 'pointer', background: 'none', border: 'none', transition: 'var(--t-fast)' }}
                            onMouseOver={e => (e.currentTarget.style.color = 'var(--primary)')}
                            onMouseOut={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
                            <BookOpen size={13} style={{ display: 'inline', marginRight: '4px' }} />
                            ¿Eres estudiante? Accede aquí
                        </button>
                    </div>
                </div>
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
};
