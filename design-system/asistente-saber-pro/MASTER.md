# Design System Master File — Asistente Saber Pro

> Cuando construyas una página, revisa primero `design-system/pages/[nombre].md`.
> Si existe, ese archivo tiene prioridad. Si no, usa este MASTER.

---

**Proyecto:** Asistente Saber Pro — UCundinamarca Fusagasugá
**Categoría:** EdTech / Study Tool — Dual Mode (Light + Dark)
**Fuente de diseño:** UI UX Pro Max Skill + Inspección visual Antigravity

---

## Sistema de Colores

### 🌙 Dark Mode (Antigravity-inspired)

| Rol | Hex | CSS Variable | Descripción |
|-----|-----|-------------|-------------|
| Background | `#09090B` | `--bg` | Negro zinc — fondo principal |
| Surface | `#18181B` | `--surface` | Cards, panels |
| Surface-2 | `#27272A` | `--surface-2` | Sidebar, inputs, headers |
| Border | `#3F3F46` | `--border` | Bordes sutiles |
| Primary | `#6366F1` | `--primary` | Indigo — acento principal |
| Primary-hover | `#4F46E5` | `--primary-hover` | Estado hover |
| Primary-glow | `#6366F133` | `--primary-glow` | Glow sutil en focus |
| Accent | `#10B981` | `--accent` | Emerald — éxito, correcto |
| Warning | `#F59E0B` | `--warning` | Ámbar — alertas, badges |
| Danger | `#EF4444` | `--danger` | Rojo suave — incorrecto |
| Text | `#FAFAFA` | `--text` | Texto principal |
| Text-muted | `#A1A1AA` | `--text-muted` | Texto secundario |
| Text-hint | `#71717A` | `--text-hint` | Placeholders, timestamps |

### ☀️ Light Mode (Blanco + Verde elegante)

| Rol | Hex | CSS Variable | Descripción |
|-----|-----|-------------|-------------|
| Background | `#F8FAFC` | `--bg` | Blanco azulado muy suave |
| Surface | `#FFFFFF` | `--surface` | Cards, panels — puro blanco |
| Surface-2 | `#F1F5F9` | `--surface-2` | Sidebar, inputs, navegación |
| Border | `#E2E8F0` | `--border` | Slate-200 — borde elegante |
| Primary | `#059669` | `--primary` | Emerald-600 — verde que no grita |
| Primary-hover | `#047857` | `--primary-hover` | Emerald-700 |
| Primary-glow | `#05966915` | `--primary-glow` | Ring de focus |
| Accent | `#6366F1` | `--accent` | Indigo — consistencia con dark |
| Warning | `#D97706` | `--warning` | Ámbar más oscuro — contraste |
| Danger | `#DC2626` | `--danger` | Rojo legible |
| Text | `#0F172A` | `--text` | Slate-900 — sin ser negro duro |
| Text-muted | `#475569` | `--text-muted` | Slate-600 |
| Text-hint | `#94A3B8` | `--text-hint` | Slate-400 |

---

## Tipografía

**Heading:** `Outfit` — Geométrica, moderna, premium. Mucha personalidad.
**Body:** `Inter` — El estándar de oro. Como en Notion, Linear, Vercel.

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');

:root {
  --font-heading: 'Outfit', sans-serif;
  --font-body: 'Inter', sans-serif;
}

h1, h2, h3, h4 { font-family: var(--font-heading); font-weight: 700; }
body, p, input, button { font-family: var(--font-body); }
```

---

## Espaciado

| Token | Valor | Uso |
|-------|-------|-----|
| `--space-xs` | `4px` | Gaps internos mínimos |
| `--space-sm` | `8px` | Iconos, inline |
| `--space-md` | `16px` | Padding estándar |
| `--space-lg` | `24px` | Secciones |
| `--space-xl` | `32px` | Gaps grandes |
| `--space-2xl` | `48px` | Secciones mayores |

---

## Bordes Redondeados

```css
--radius-sm: 6px;    /* Badges, chips */
--radius-md: 10px;   /* Inputs, botones */
--radius-lg: 14px;   /* Cards */
--radius-xl: 20px;   /* Modales, panels grandes */
--radius-full: 9999px; /* Pills, avatares */
```

---

## Sombras

```css
/* Dark mode shadows */
--shadow-sm: 0 1px 3px rgba(0,0,0,0.4);
--shadow-md: 0 4px 12px rgba(0,0,0,0.5);
--shadow-lg: 0 8px 24px rgba(0,0,0,0.6);
--shadow-glow: 0 0 20px rgba(99,102,241,0.3); /* Indigo glow */

/* Light mode shadows */
--shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
--shadow-md: 0 4px 12px rgba(0,0,0,0.08);
--shadow-lg: 0 8px 24px rgba(0,0,0,0.1);
--shadow-glow: 0 0 20px rgba(5,150,105,0.2); /* Green glow */
```

---

## Animaciones

```css
/* Transiciones estándar */
--transition-fast: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-base: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-slow: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
--transition-spring: all 400ms cubic-bezier(0.34, 1.56, 0.64, 1); /* Spring/bounce */

/* Keyframes */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.4); }
  50%       { box-shadow: 0 0 0 8px rgba(99,102,241,0); }
}

@keyframes skeleton {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Clases de animación */
.animate-fade-up   { animation: fadeInUp 300ms ease forwards; }
.animate-slide-in  { animation: slideInRight 250ms ease forwards; }
.animate-pulse-glow { animation: pulse-glow 2s infinite; }
```

---

## Componentes

### Botones

```css
/* Botón Primario */
.btn-primary {
  background: var(--primary);
  color: white;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: var(--transition-base);
  position: relative;
  overflow: hidden;
}
.btn-primary::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.1);
  opacity: 0;
  transition: var(--transition-fast);
}
.btn-primary:hover::after { opacity: 1; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: var(--shadow-glow); }
.btn-primary:active { transform: translateY(0); }

/* Botón Ghost */
.btn-ghost {
  background: transparent;
  color: var(--primary);
  border: 1.5px solid var(--primary);
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition-base);
}
.btn-ghost:hover { background: var(--primary); color: white; }

/* Botón Icono */
.btn-icon {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  transition: var(--transition-fast);
}
.btn-icon:hover { background: var(--primary); color: white; border-color: var(--primary); }
```

### Cards

```css
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  transition: var(--transition-base);
}
.card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  background: var(--surface-2);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: 15px;
  color: var(--text);
  width: 100%;
  transition: var(--transition-fast);
}
.input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}
```

### Skeleton Loaders

```css
.skeleton {
  background: linear-gradient(90deg,
    var(--surface-2) 25%,
    var(--border) 50%,
    var(--surface-2) 75%
  );
  background-size: 200% 100%;
  animation: skeleton 1.5s ease infinite;
  border-radius: var(--radius-sm);
}
```

---

## Patrones por pantalla

| Pantalla | Patrón | Nota |
|---|---|---|
| Login / Registro | Card centrada, fondo con patrón de puntos sutil | Animación fadeIn al cargar |
| Chat IA | Sidebar historial + área de mensajes + input sticky | Burbujas con slideIn |
| Práctica Quiz | Card de pregunta + opciones animadas | Feedback visual con color |
| Dashboard | Bento grid de KPIs + gráficos Plotly | Skeleton loaders |
| Tabla estudiantes | Tabla con sticky header + filtros | Row hover highlight |

---

## Anti-Patrones ❌

- ❌ Emojis como íconos — usar Lucide React (SVG)
- ❌ Colores sin contraste suficiente (mínimo 4.5:1)
- ❌ Cambios de estado sin transición
- ❌ Layout que se mueve en hover (no usar scale)
- ❌ Texto gris muy claro sobre fondo blanco
- ❌ Botones sin cursor:pointer
- ❌ Focus states invisibles

---

## Checklist Pre-entrega

- [ ] Iconos: solo Lucide React (SVG consistente)
- [ ] cursor:pointer en todos los clickables
- [ ] Hover con transición 150-300ms
- [ ] Contraste texto 4.5:1 mínimo (ambos modos)
- [ ] Focus state visible (ring de 3px)
- [ ] prefers-reduced-motion respetado
- [ ] Responsive: 375px / 768px / 1024px / 1440px
- [ ] Sin scroll horizontal en móvil
- [ ] Skeleton loaders en todas las peticiones async
