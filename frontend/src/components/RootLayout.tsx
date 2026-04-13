import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { GlobalParticleBackground } from './GlobalParticleBackground';
import { useTheme } from '../context/ThemeContext';

// ── RootLayout ───────────────────────────────────────────
// Persistent layout that wraps ALL routes.
// Canvas (z-index: 0) sits beneath everything,
// Outlet (z-index: 10) renders page content on top.
// The Canvas NEVER unmounts during navigation.

export const RootLayout: React.FC = () => {
    const { theme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <>
            {/* ── Particle Canvas Layer ──────────────────── */}
            <div className="particle-canvas-container" aria-hidden="true">
                <Canvas
                    camera={{ position: [0, 0, 5], fov: 60 }}
                    dpr={[1, 1.5]}
                    gl={{
                        alpha: true,
                        antialias: false,
                        powerPreference: 'low-power',
                    }}
                    style={{ background: 'transparent' }}
                >
                    <GlobalParticleBackground isDark={isDark} />
                </Canvas>
            </div>

            {/* ── App Content Layer ──────────────────────── */}
            <div className="app-content">
                <Suspense
                    fallback={
                        <div style={{
                            minHeight: '100vh',
                            display: 'grid',
                            placeItems: 'center',
                            color: 'var(--text-muted)',
                        }}>
                            Cargando experiencia...
                        </div>
                    }
                >
                    <Outlet />
                </Suspense>
            </div>
        </>
    );
};
