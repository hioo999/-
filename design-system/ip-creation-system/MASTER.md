# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** IP Creation System
**Generated:** 2026-05-29 23:38:45
**Category:** AI Creator SaaS Workbench

---

## Global Rules

### Visual Direction

**Style:** Light Glass SaaS Workbench

**Positioning:** AI personal IP content production workspace for creators, founders, and operators.

**Keywords:** light glass, creator intelligence, AI copilot, professional dashboard, calm premium, workflow-first

**Principle:** Keep the interface bright, readable, and operational. Use glass surfaces and blue-purple accents to express AI capability, but prioritize task clarity, content readability, and long-session comfort.

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#2563EB` | `--color-primary` |
| On Primary | `#FFFFFF` | `--color-on-primary` |
| Secondary | `#7C3AED` | `--color-secondary` |
| Accent/CTA | `#22C55E` | `--color-accent` |
| Background | `#F6F8FB` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
| Muted | `#F1F5F9` | `--color-muted` |
| Border | `rgba(15,23,42,0.08)` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| Ring | `#2563EB` | `--color-ring` |

**Color Notes:** Trust blue for primary actions, creator purple for AI intelligence, green only for success/pass/publish states, on a light gray-blue canvas.

### Typography

- **Heading Font:** Inter + Noto Sans SC
- **Body Font:** Inter + Noto Sans SC
- **Mood:** modern, professional, Chinese-readable, SaaS, calm, precise
- **Google Fonts:** [Inter + Noto Sans SC](https://fonts.google.com/)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |
| `--space-3xl` | `64px` / `4rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
   background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #7C3AED;
  border: 1px solid rgba(37, 99, 235, 0.22);
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: rgba(255, 255, 255, 0.74);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #7C3AED;
  outline: none;
  box-shadow: 0 0 0 3px #7C3AED20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Light Glass SaaS Workbench

**Keywords:** light glass, blue-purple AI gradient, calm SaaS, modular cards, sticky workbench, readable Chinese content, clear status badges

**Best For:** AI content tools, creator operation systems, SaaS dashboards, personal IP workspaces, long-session productivity interfaces

**Key Effects:** frosted white cards, soft blue-purple canvas glows, compact but breathable grid, 150-250ms feedback, visible focus states

### Page Pattern

**Pattern Name:** Creator Intelligence Workbench

- **Conversion Strategy:** Move users from IP profile to material input, AI generation, content refinement, quality check, and publish package.
- **CTA Placement:** Primary generation actions stay near the active input; save/publish actions stay near output and status panels.
- **Section Order:** 1. IP/context selector, 2. Material/input panel, 3. Generation workflow output, 4. Copilot refinement, 5. Quality/publish readiness.

---

## Anti-Patterns (Do NOT Use)

- ❌ Full dark mode as the default workspace
- ❌ Creator-pink marketing style as the main product shell
- ❌ ERP-like flat gray admin panels

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
