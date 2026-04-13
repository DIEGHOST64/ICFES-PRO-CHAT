import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useVisualMood } from '../context/VisualMoodContext';
import type { VisualMood } from '../context/VisualMoodContext';

// ── GLSL Vertex Shader ───────────────────────────────────
const VERTEX = /* glsl */ `
attribute float aShape;
attribute float aSize;
attribute float aSeed;

varying float vShape;
varying float vAlpha;
varying float vSeed;

uniform float uTime;
uniform float uSizeScale;

void main() {
    vShape = aShape;
    vSeed  = aSeed;

    vec4 mv = modelViewMatrix * vec4(position, 1.0);

    // Subtle breathing pulse per particle
    float pulse = 1.0 + 0.16 * sin(uTime * 0.45 + aSeed * 6.283);

    // Size with perspective attenuation, scale it down to make it less distracting
    gl_PointSize = min(aSize * pulse * (85.0 / -mv.z) * uSizeScale, 24.0 * uSizeScale);
    gl_Position  = projectionMatrix * mv;

    // Fade distant particles
    vAlpha = smoothstep(22.0, 3.0, -mv.z);
}
`;

// ── GLSL Fragment Shader — 5 shapes: circle, triangle, diamond, ring, cross
const FRAGMENT = /* glsl */ `
varying float vShape;
varying float vAlpha;
varying float vSeed;

uniform vec3  uColor;
uniform float uOpacity;
uniform float uTime;

void main() {
    vec2  uv = gl_PointCoord - 0.5;
    float d  = length(uv);
    float s  = floor(vShape + 0.5);
    float a  = 0.0;

    // ── Shape 0: Soft circle ─────────────────────────
    if (s < 0.5) {
        a = 1.0 - smoothstep(0.28, 0.48, d);
    }
    // ── Shape 1: Triangle ────────────────────────────
    else if (s < 1.5) {
        vec2 p = uv;
        p.y += 0.08;
        float t = max(abs(p.x) * 1.732 + p.y, -p.y * 1.6);
        a = 1.0 - smoothstep(0.30, 0.40, t);
    }
    // ── Shape 2: Diamond ─────────────────────────────
    else if (s < 2.5) {
        a = 1.0 - smoothstep(0.26, 0.38, abs(uv.x) + abs(uv.y));
    }
    // ── Shape 3: Ring (hollow circle) ────────────────
    else if (s < 3.5) {
        a = 1.0 - smoothstep(0.04, 0.09, abs(d - 0.28));
    }
    // ── Shape 4: Cross / Plus ────────────────────────
    else {
        float c = min(abs(uv.x), abs(uv.y));
        a = (1.0 - smoothstep(0.045, 0.09, c))
          * (1.0 - smoothstep(0.34, 0.48, d));
    }

    // Soft glow halo around every particle
    a = max(a, exp(-d * d * 6.0) * 0.35);

    // Subtle per-particle color shimmer
    vec3 col = uColor + 0.08 * sin(uTime * 0.3 + vSeed * 3.14);

    a *= uOpacity * vAlpha;
    if (a < 0.004) discard;

    gl_FragColor = vec4(col, a);
}
`;

// ── Mood configuration ───────────────────────────────────
interface MoodParams {
    speed: number;
    colorLight: [number, number, number];
    colorDark: [number, number, number];
    count: number;
    waveAmplitude: number;
    rotationSpeed: number;
    opacity: number;
    mouseRadius: number;
    mouseForce: number;
    sizeScale: number;
}

const MOOD_CONFIG: Record<VisualMood, MoodParams> = {
    idle: {
        speed: 0.08,
        colorLight: [0.50, 0.65, 0.80],
        colorDark: [0.55, 0.70, 0.88],
        count: 700,
        waveAmplitude: 0.3,
        rotationSpeed: 0,
        opacity: 0.72,
        mouseRadius: 2.5,
        mouseForce: 0.45,
        sizeScale: 2.8,
    },
    authenticated: {
        speed: 0.12,
        colorLight: [0.38, 0.58, 0.78],
        colorDark: [0.50, 0.72, 0.92],
        count: 500,
        waveAmplitude: 0.4,
        rotationSpeed: 0.0003,
        opacity: 0.45,
        mouseRadius: 2.0,
        mouseForce: 0.45,
        sizeScale: 0.65,
    },
    processing: {
        speed: 0.22,
        colorLight: [0.30, 0.62, 0.75],
        colorDark: [0.45, 0.78, 0.92],
        count: 600,
        waveAmplitude: 0.6,
        rotationSpeed: 0.0010,
        opacity: 0.60,
        mouseRadius: 2.8,
        mouseForce: 0.65,
        sizeScale: 0.85,
    },
};

const MAX_PARTICLES = 800;
const SPREAD_X = 16;
const SPREAD_Y = 12;
const SPREAD_Z = 8;

// ── Component ────────────────────────────────────────────
export const GlobalParticleBackground: React.FC<{ isDark?: boolean }> = ({ isDark = false }) => {
    const pointsRef = useRef<THREE.Points>(null);
    const materialRef = useRef<THREE.ShaderMaterial>(null);
    const { mood } = useVisualMood();

    // Smoothly interpolated values (refs avoid re-renders)
    const target = useRef({ speed: 0.08, opacity: 0.62, wave: 0.3, rot: 0, r: 0.50, g: 0.65, b: 0.80, mRadius: 2.0, mForce: 0.35, sizeScale: 1.0 });
    const current = useRef({ speed: 0.08, opacity: 0.62, wave: 0.3, rot: 0, r: 0.50, g: 0.65, b: 0.80, mRadius: 2.0, mForce: 0.35, sizeScale: 1.0 });

    // Mouse tracking — NDC coordinates, set via window event listener
    const mouseNdc = useRef({ x: 999, y: 999 });
    const mouseActive = useRef(false);
    // Reusable vectors (avoid GC)
    const _vec3 = useRef(new THREE.Vector3());

    // ── Generate buffers (once) ──────────────────────────
    const positions = useMemo(() => {
        const arr = new Float32Array(MAX_PARTICLES * 3);
        for (let i = 0; i < MAX_PARTICLES; i++) {
            const i3 = i * 3;
            arr[i3]     = (Math.random() - 0.5) * SPREAD_X;
            arr[i3 + 1] = (Math.random() - 0.5) * SPREAD_Y;
            arr[i3 + 2] = (Math.random() - 0.5) * SPREAD_Z;
        }
        return arr;
    }, []);

    // Base reference positions (immutable copy)
    const basePos = useMemo(() => {
        const arr = new Float32Array(MAX_PARTICLES * 3);
        arr.set(positions);
        return arr;
    }, [positions]);

    // Per-particle random seeds
    const seeds = useMemo(() => {
        const arr = new Float32Array(MAX_PARTICLES);
        for (let i = 0; i < MAX_PARTICLES; i++) arr[i] = Math.random() * Math.PI * 2;
        return arr;
    }, []);

    // Random shape assignment: 0=circle, 1=triangle, 2=diamond, 3=ring, 4=cross
    const shapeTypes = useMemo(() => {
        const arr = new Float32Array(MAX_PARTICLES);
        for (let i = 0; i < MAX_PARTICLES; i++) arr[i] = Math.floor(Math.random() * 5);
        return arr;
    }, []);

    // Random sizes (shader units, scaled by gl_PointSize in vertex shader)
    const particleSizes = useMemo(() => {
        const arr = new Float32Array(MAX_PARTICLES);
        for (let i = 0; i < MAX_PARTICLES; i++) arr[i] = 0.10 + Math.random() * 0.22;
        return arr;
    }, []);

    // Mouse displacement buffer (decays over time)
    const mouseOffsets = useMemo(() => new Float32Array(MAX_PARTICLES * 3), []);

    // Shader uniforms (memoized to avoid re-creation)
    const uniforms = useMemo(() => ({
        uColor:     { value: new THREE.Color(0.50, 0.65, 0.80) },
        uOpacity:   { value: 0.62 },
        uTime:      { value: 0 },
        uSizeScale: { value: 1.0 },
    }), []);

    // ── Mouse event listeners ────────────────────────────
    useEffect(() => {
        const onMove = (e: MouseEvent) => {
            mouseNdc.current.x = (e.clientX / window.innerWidth) * 2 - 1;
            mouseNdc.current.y = -(e.clientY / window.innerHeight) * 2 + 1;
            mouseActive.current = true;
        };
        const onLeave = () => {
            mouseActive.current = false;
        };
        window.addEventListener('mousemove', onMove, { passive: true });
        document.addEventListener('mouseleave', onLeave);
        return () => {
            window.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseleave', onLeave);
        };
    }, []);

    // ── Animation loop ───────────────────────────────────
    useFrame((state) => {
        const pts = pointsRef.current;
        const mat = materialRef.current;
        if (!pts || !mat) return;

        const cfg = MOOD_CONFIG[mood];
        const ck = isDark ? 'colorDark' : 'colorLight';

        // Set targets
        const t = target.current;
        t.speed     = cfg.speed;
        t.opacity   = cfg.opacity;
        t.wave      = cfg.waveAmplitude;
        t.rot       = cfg.rotationSpeed;
        t.r         = cfg[ck][0];
        t.g         = cfg[ck][1];
        t.b         = cfg[ck][2];
        t.mRadius   = cfg.mouseRadius;
        t.mForce    = cfg.mouseForce;
        t.sizeScale = cfg.sizeScale;

        // Smooth interpolation (lerp)
        const c = current.current;
        const lf = 0.025;
        c.speed     += (t.speed     - c.speed)     * lf;
        c.opacity   += (t.opacity   - c.opacity)   * lf;
        c.wave      += (t.wave      - c.wave)      * lf;
        c.rot       += (t.rot       - c.rot)       * lf;
        c.r         += (t.r         - c.r)         * lf;
        c.g         += (t.g         - c.g)         * lf;
        c.b         += (t.b         - c.b)         * lf;
        c.mRadius   += (t.mRadius   - c.mRadius)   * lf;
        c.mForce    += (t.mForce    - c.mForce)    * lf;
        c.sizeScale += (t.sizeScale - c.sizeScale) * lf;

        // ── Unproject mouse to world space (z=0 plane) ───
        let mouseWorldX = 999;
        let mouseWorldY = 999;

        if (mouseActive.current) {
            const v = _vec3.current;
            v.set(mouseNdc.current.x, mouseNdc.current.y, 0.5);
            v.unproject(state.camera);
            const camPos = state.camera.position;
            const dir = v.sub(camPos).normalize();
            const dist = -camPos.z / dir.z;
            mouseWorldX = camPos.x + dir.x * dist;
            mouseWorldY = camPos.y + dir.y * dist;
        }

        const elapsed = state.clock.elapsedTime;
        const posArray = pts.geometry.attributes.position.array as Float32Array;
        const activeCount = cfg.count;
        const mRadSq = c.mRadius * c.mRadius;

        // ── Animate each particle ────────────────────────
        for (let i = 0; i < activeCount; i++) {
            const i3 = i * 3;
            const seed = seeds[i];

            // Base wave animation
            const animX = basePos[i3]     + Math.sin(elapsed * c.speed * 0.4 + seed) * c.wave * 0.3;
            const animY = basePos[i3 + 1] + Math.sin(elapsed * c.speed + seed) * c.wave;
            const animZ = basePos[i3 + 2];

            // ── Mouse repulsion ──────────────────────────
            // Decay existing offset
            mouseOffsets[i3]     *= 0.92;
            mouseOffsets[i3 + 1] *= 0.92;

            if (mouseActive.current) {
                const dx = animX - mouseWorldX;
                const dy = animY - mouseWorldY;
                const distSq = dx * dx + dy * dy;

                if (distSq < mRadSq && distSq > 0.001) {
                    const dist = Math.sqrt(distSq);
                    const falloff = 1 - dist / c.mRadius;
                    const force = falloff * falloff * c.mForce;
                    const invDist = 1 / dist;
                    mouseOffsets[i3]     += dx * invDist * force;
                    mouseOffsets[i3 + 1] += dy * invDist * force;
                }
            }

            // Final position = animated + mouse displacement
            posArray[i3]     = animX + mouseOffsets[i3];
            posArray[i3 + 1] = animY + mouseOffsets[i3 + 1];
            posArray[i3 + 2] = animZ;
        }

        // Hide inactive particles (push off-screen)
        for (let i = activeCount; i < MAX_PARTICLES; i++) {
            posArray[i * 3 + 1] = 200;
        }

        pts.geometry.attributes.position.needsUpdate = true;

        // Subtle group rotation
        if (c.rot > 0.0001) {
            pts.rotation.y += c.rot;
        }

        // Update shader uniforms
        mat.uniforms.uColor.value.setRGB(c.r, c.g, c.b);
        mat.uniforms.uOpacity.value = c.opacity;
        mat.uniforms.uTime.value = elapsed;
        mat.uniforms.uSizeScale.value = c.sizeScale;
    });

    // ── Render ────────────────────────────────────────────
    return (
        <points ref={pointsRef} frustumCulled={false}>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" args={[positions, 3]} />
                <bufferAttribute attach="attributes-aShape"   args={[shapeTypes, 1]} />
                <bufferAttribute attach="attributes-aSize"    args={[particleSizes, 1]} />
                <bufferAttribute attach="attributes-aSeed"    args={[seeds, 1]} />
            </bufferGeometry>
            <shaderMaterial
                ref={materialRef}
                vertexShader={VERTEX}
                fragmentShader={FRAGMENT}
                uniforms={uniforms}
                transparent
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
};
