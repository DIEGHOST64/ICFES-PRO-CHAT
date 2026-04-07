import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { GraduationCap, BriefcaseBusiness, ArrowRight } from 'lucide-react';
import { InstitutionalLogo } from '../components/InstitutionalLogo';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const particlesRef = useRef<HTMLDivElement>(null);
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

      tl.fromTo('[data-splash="veil"]', { autoAlpha: 0.9 }, { autoAlpha: 0.55, duration: 1.4 }, 0)
        .fromTo('[data-splash="logo"]', { y: 18, scale: 0.95, autoAlpha: 0 }, { y: 0, scale: 1, autoAlpha: 1, duration: 0.95, ease: 'power3.out' }, 0.1)
        .fromTo('[data-splash="title"]', { y: 22, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8, ease: 'power2.out' }, 0.35)
        .fromTo('[data-splash="subtitle"]', { y: 12, autoAlpha: 0 }, { y: 0, autoAlpha: 0.9, duration: 0.65, ease: 'power2.out' }, 0.58)
        .to('[data-splash="logo"]', { y: -4, duration: 0.9, ease: 'sine.inOut' }, 1.55)
        .to('[data-splash="shell"]', {
          autoAlpha: 0,
          duration: 0.55,
          ease: 'power1.inOut',
          onComplete: () => setPhase('intro'),
        }, 2.5);

      gsap.fromTo('[data-splash="particle"]', {
        autoAlpha: 0.5,
        y: 8,
      }, {
        autoAlpha: 1,
        y: -14,
        stagger: 0.06,
        duration: 2.6,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
      });
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
      gsap.fromTo('[data-intro="halo"]', { scale: 0.92, autoAlpha: 0.28 }, {
        scale: 1.03,
        autoAlpha: 0.54,
        duration: 4.8,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
      });
    }, root);

    return () => ctx.revert();
  }, [phase]);

  return (
    <div
      ref={rootRef}
      style={{
        minHeight: '100vh',
        background: 'radial-gradient(circle at 12% 18%, #dce7ef 0%, transparent 36%), radial-gradient(circle at 88% 84%, #d9ece2 0%, transparent 34%), linear-gradient(155deg, #edf2f5 0%, #e8eef2 52%, #e3ebef 100%)',
        position: 'relative',
        overflow: 'hidden',
        padding: '24px',
      }}
    >
      {phase === 'splash' && (
        <div
          data-splash="shell"
          style={{
            position: 'absolute',
            inset: 0,
            display: 'grid',
            placeItems: 'center',
            background: 'linear-gradient(150deg, rgba(237,242,245,0.92) 0%, rgba(229,237,242,0.9) 100%)',
            backdropFilter: 'blur(8px)',
            zIndex: 2,
          }}
        >
          <div
            data-splash="veil"
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle at 30% 22%, rgba(120, 147, 165, 0.18), transparent 45%), radial-gradient(circle at 70% 76%, rgba(103, 141, 122, 0.16), transparent 42%)',
            }}
          />
          <div
            ref={particlesRef}
            style={{
              position: 'absolute',
              inset: 0,
              pointerEvents: 'none',
              background: 'radial-gradient(circle at 16% 26%, rgba(116, 145, 163, 0.12) 0%, transparent 40%), radial-gradient(circle at 84% 74%, rgba(102, 140, 122, 0.11) 0%, transparent 42%)',
            }}
          >
            {Array.from({ length: 16 }).map((_, i) => (
              <span
                key={i}
                data-splash="particle"
                style={{
                  position: 'absolute',
                  width: `${6 + (i % 3) * 2}px`,
                  height: `${6 + (i % 3) * 2}px`,
                  borderRadius: '999px',
                  background: i % 2 === 0 ? 'rgba(74, 106, 125, 0.54)' : 'rgba(72, 122, 101, 0.5)',
                  left: `${6 + (i * 6)}%`,
                  top: `${16 + ((i * 13) % 66)}%`,
                  boxShadow: '0 0 8px rgba(255,255,255,0.22)',
                }}
              />
            ))}
          </div>
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
                color: '#223644',
                letterSpacing: '-0.035em',
                lineHeight: 1.02,
                fontFamily: 'var(--font-heading)',
                textShadow: '0 10px 22px rgba(35, 67, 92, 0.16)',
              }}
            >
              Ascenso Pro
            </h1>
            <p
              data-splash="subtitle"
              style={{
                marginTop: '10px',
                fontSize: '14px',
                color: '#4e6678',
              }}
            >
              Universidad de Cundinamarca · Plataforma de aprendizaje guiado
            </p>
          </div>
        </div>
      )}

      {phase === 'intro' && (
        <div style={{ maxWidth: '980px', margin: '0 auto', minHeight: 'calc(100vh - 48px)', display: 'grid', alignContent: 'center' }}>
          <div
            data-intro="halo"
            style={{
              position: 'absolute',
              width: '520px',
              height: '520px',
              borderRadius: '999px',
              left: '50%',
              top: '52%',
              transform: 'translate(-50%, -50%)',
              background: 'radial-gradient(circle, rgba(68, 103, 124, 0.14), rgba(68, 103, 124, 0.02) 54%, transparent 72%)',
              pointerEvents: 'none',
              zIndex: 0,
            }}
          />
          <div data-intro="headline" style={{ textAlign: 'center', marginBottom: '26px', position: 'relative', zIndex: 1 }}>
            <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'center' }}>
              <InstitutionalLogo size={128} />
            </div>
            <h2 style={{ fontSize: 'clamp(28px, 4.6vw, 44px)', color: '#1f3140', fontFamily: 'var(--font-heading)' }}>¿Cómo quieres ingresar?</h2>
            <p style={{ color: '#566c7e', marginTop: '6px' }}>Selecciona tu perfil para continuar con la experiencia adecuada.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '18px', position: 'relative', zIndex: 1 }}>
            <button
              data-intro="card"
              onClick={() => navigate('/login')}
              style={{
                textAlign: 'left',
                borderRadius: '26px',
                border: '1px solid #cedae4',
                background: 'linear-gradient(150deg, #ffffff 0%, #f1f8ff 62%, #edf5fd 100%)',
                boxShadow: '0 24px 44px rgba(31, 63, 89, 0.13)',
                padding: '24px',
                transition: 'transform 220ms ease, box-shadow 220ms ease',
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
              <div style={{ width: '50px', height: '50px', borderRadius: '14px', background: 'rgba(54, 90, 116, 0.14)', display: 'grid', placeItems: 'center', marginBottom: '12px' }}>
                <GraduationCap size={24} color="#345d77" />
              </div>
              <h3 style={{ fontSize: '24px', color: '#203646', marginBottom: '6px', fontFamily: 'var(--font-heading)' }}>Eres Estudiante</h3>
              <p style={{ fontSize: '14px', color: '#576f80', marginBottom: '14px' }}>Practica, pregunta y recibe retroalimentación guiada para Saber Pro.</p>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#2f556d', fontWeight: 700 }}>Entrar <ArrowRight size={15} /></span>
            </button>

            <button
              data-intro="card"
              onClick={() => navigate('/coordinador')}
              style={{
                textAlign: 'left',
                borderRadius: '26px',
                border: '1px solid #cfdad6',
                background: 'linear-gradient(150deg, #ffffff 0%, #eff7f2 62%, #ebf4ef 100%)',
                boxShadow: '0 24px 44px rgba(29, 79, 63, 0.13)',
                padding: '24px',
                transition: 'transform 220ms ease, box-shadow 220ms ease',
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
              <div style={{ width: '50px', height: '50px', borderRadius: '14px', background: 'rgba(69, 111, 94, 0.14)', display: 'grid', placeItems: 'center', marginBottom: '12px' }}>
                <BriefcaseBusiness size={24} color="#3c6a58" />
              </div>
              <h3 style={{ fontSize: '24px', color: '#1f3744', marginBottom: '6px', fontFamily: 'var(--font-heading)' }}>Eres Coordinador</h3>
              <p style={{ fontSize: '14px', color: '#576f80', marginBottom: '14px' }}>Gestiona métricas, revisa progreso y acompaña decisiones académicas.</p>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#355f4f', fontWeight: 700 }}>Entrar <ArrowRight size={15} /></span>
            </button>
          </div>

          <div style={{ marginTop: '16px', textAlign: 'center' }}>
            <p style={{ margin: 0, color: '#4f6576', fontSize: '12px', fontWeight: 700, letterSpacing: '0.06em' }}>
              UNIVERSIDAD DE CUNDINAMARCA
            </p>
            <p style={{ margin: '4px 0 0', color: '#4f6576', opacity: 0.85, fontSize: '11px' }}>
              Ascenso Pro
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
