import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { GraduationCap, BriefcaseBusiness, ArrowRight, Sun, Moon } from 'lucide-react';
import { InstitutionalLogo } from '../components/InstitutionalLogo';
import { useTheme } from '../context/ThemeContext';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const { theme, toggleTheme } = useTheme();
  const [phase, setPhase] = useState<'splash' | 'intro'>('splash');

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setPhase('intro');
      return;
    }

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power2.out' } });

      tl.fromTo('[data-splash="logo"]', { y: 18, scale: 0.95, autoAlpha: 0 }, { y: 0, scale: 1, autoAlpha: 1, duration: 0.95, ease: 'power3.out' }, 0.1)
        .fromTo('[data-splash="title"]', { y: 22, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8, ease: 'power2.out' }, 0.35)
        .fromTo('[data-splash="subtitle"]', { y: 12, autoAlpha: 0 }, { y: 0, autoAlpha: 0.9, duration: 0.65, ease: 'power2.out' }, 0.58)
        .to('[data-splash="logo"]', { y: -4, duration: 0.9, ease: 'sine.inOut' }, 1.55)
        .to('[data-splash="shell"]', {
          autoAlpha: 0,
          duration: 0.55,
          ease: 'power1.inOut',
          onComplete: () => setPhase('intro'),
        }, 2.5);
    }, root);

    return () => ctx.revert();
  }, []);

  useEffect(() => {
    if (phase !== 'intro') return;
    const root = rootRef.current;
    if (!root) return;

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const ctx = gsap.context(() => {
      gsap.fromTo('[data-intro="headline"]', { y: 16, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.7, ease: 'power2.out' });
      gsap.fromTo('[data-intro="card"]', { y: 22, autoAlpha: 0, scale: 0.985 }, {
        y: 0,
        autoAlpha: 1,
        scale: 1,
        duration: 0.75,
        stagger: 0.12,
        ease: 'power3.out',
      });
    }, root);

    return () => ctx.revert();
  }, [phase]);

  return (
    <div
      ref={rootRef}
      style={{
        minHeight: '100vh',
        position: 'relative',
        overflow: 'hidden',
        padding: '24px',
        /* Transparent background — WebGL particles show through from RootLayout Canvas */
      }}
    >
      {/* Theme Toggle Button */}
      {phase === 'intro' && (
        <button
          onClick={toggleTheme}
          className="glass-panel"
          style={{
            position: 'absolute',
            top: '24px',
            right: '24px',
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--text)',
            zIndex: 10,
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      )}

      {phase === 'splash' && (
        <div
          data-splash="shell"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            zIndex: 2,
            borderRadius: 0,
            border: 'none',
            background: 'color-mix(in srgb, var(--bg) 30%, transparent)',
            backdropFilter: 'blur(2px)',
            WebkitBackdropFilter: 'blur(2px)',
          }}
        >
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <div
              data-splash="logo"
              style={{
                margin: '0 auto 20px',
                display: 'grid',
                placeItems: 'center',
                position: 'relative',
              }}
            >
              <div style={{ zIndex: 1, display: 'flex', justifyContent: 'center' }}>
                <InstitutionalLogo size={194} radius={32} />
              </div>
            </div>

            <h1
              data-splash="title"
              style={{
                fontSize: 'clamp(34px, 6vw, 64px)',
                color: 'var(--text)',
                letterSpacing: '-0.035em',
                lineHeight: 1.02,
                fontFamily: 'var(--font-heading)',
                textShadow: '0 4px 20px color-mix(in srgb, var(--bg) 70%, transparent)',
              }}
            >
              Ascenso Pro
            </h1>
            <p
              data-splash="subtitle"
              style={{
                marginTop: '10px',
                fontSize: '14px',
                color: 'var(--text-muted)',
                textShadow: '0 2px 10px color-mix(in srgb, var(--bg) 60%, transparent)',
              }}
            >
              Universidad de Cundinamarca · Plataforma de aprendizaje guiado
            </p>
          </div>
        </div>
      )}

      {phase === 'intro' && (
        <div style={{ maxWidth: '980px', margin: '0 auto', minHeight: 'calc(100vh - 48px)', display: 'grid', alignContent: 'center' }}>
          <div data-intro="headline" style={{ textAlign: 'center', marginBottom: '26px', position: 'relative', zIndex: 1 }}>
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'center' }}>
              <InstitutionalLogo size={128} />
            </div>
            <h2 style={{ fontSize: 'clamp(28px, 4.6vw, 44px)', color: 'var(--text)', fontFamily: 'var(--font-heading)' }}>¿Cómo quieres ingresar?</h2>
            <p style={{ color: 'var(--text-muted)', marginTop: '6px' }}>Selecciona tu perfil para continuar con la experiencia adecuada.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '18px', position: 'relative', zIndex: 1 }}>
            <button
              data-intro="card"
              onClick={() => navigate('/login')}
              className="glass-panel"
              style={{
                textAlign: 'left',
                borderRadius: '26px',
                boxShadow: '0 24px 44px rgba(31, 63, 89, 0.13)',
                padding: '24px',
                transition: 'transform 220ms ease, box-shadow 220ms ease',
                cursor: 'pointer',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 30px 56px rgba(31, 63, 89, 0.16)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 24px 44px rgba(31, 63, 89, 0.13)';
              }}
            >
              <div style={{ width: '50px', height: '50px', borderRadius: '14px', background: 'var(--primary-soft)', display: 'grid', placeItems: 'center', marginBottom: '12px' }}>
                <GraduationCap size={24} color="var(--primary)" />
              </div>
              <h3 style={{ fontSize: '24px', color: 'var(--text)', marginBottom: '6px', fontFamily: 'var(--font-heading)' }}>Eres Estudiante</h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '14px' }}>Practica, pregunta y recibe retroalimentación guiada para Saber Pro.</p>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--primary)', fontWeight: 700 }}>Entrar <ArrowRight size={15} /></span>
            </button>

            <button
              data-intro="card"
              onClick={() => navigate('/coordinador')}
              className="glass-panel"
              style={{
                textAlign: 'left',
                borderRadius: '26px',
                boxShadow: '0 24px 44px rgba(29, 79, 63, 0.13)',
                padding: '24px',
                transition: 'transform 220ms ease, box-shadow 220ms ease',
                cursor: 'pointer',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-4px)';
                e.currentTarget.style.boxShadow = '0 30px 56px rgba(29, 79, 63, 0.16)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 24px 44px rgba(29, 79, 63, 0.13)';
              }}
            >
              <div style={{ width: '50px', height: '50px', borderRadius: '14px', background: 'var(--accent-soft)', display: 'grid', placeItems: 'center', marginBottom: '12px' }}>
                <BriefcaseBusiness size={24} color="var(--accent)" />
              </div>
              <h3 style={{ fontSize: '24px', color: 'var(--text)', marginBottom: '6px', fontFamily: 'var(--font-heading)' }}>Eres Coordinador</h3>
              <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '14px' }}>Gestiona métricas, revisa progreso y acompaña decisiones académicas.</p>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--accent)', fontWeight: 700 }}>Entrar <ArrowRight size={15} /></span>
            </button>
          </div>

          <div style={{ marginTop: '16px', textAlign: 'center' }}>
            <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '12px', fontWeight: 700, letterSpacing: '0.06em' }}>
              UNIVERSIDAD DE CUNDINAMARCA
            </p>
            <p style={{ margin: '4px 0 0', color: 'var(--text-hint)', fontSize: '11px' }}>
              Ascenso Pro
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
