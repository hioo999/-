# PRD: MiniMax-Style Light Console Refactor

## Background

The previous AI Studio visual pass introduced a dark command-center theme with blue-purple neon gradients and broad global overrides. That direction is not suitable for an AI product backend and production workspace used by content production teams and operators. It reduced readability in legacy light pages, especially forms, editors, WeChat article previews, and teleprompter controls.

The confirmed direction is a MiniMax-inspired light product console: white and light gray surfaces, black/gray text, restrained brand blue, large cards, generous whitespace, and workflow-first information architecture.

## Goals

- Restore high-contrast readable light UI across the product backend.
- Remove broad dark/neon global styling that overrides editor and form surfaces.
- Establish a shared light token system for page backgrounds, surfaces, text, borders, status colors, buttons, and inputs.
- Refactor the global navigation into four primary modules: Overview, Production, Publishing, and Settings.
- Refactor the homepage from a dense tool-entry wall into a workflow-oriented product console.

## Target Users

- Content production team members who create IP profiles, scripts, articles, covers, and publishing packages.
- Operations staff who review task status, prepare publishing materials, and monitor failures.
- Admin users who manage model gateway settings and prompt templates.

## User Flow

1. User lands on the homepage and immediately sees today's priority work.
2. User chooses between starting production or creating a new IP profile.
3. User reviews up to three most important continuation tasks.
4. User checks key production indicators: IP completeness, content assets, pending publishing, failed tasks.
5. User follows the standard production path: build profile, input assets, generate content, quality-check and publish.
6. User opens recent assets or jumps into one of the core tools.

## Functional Scope

### Phase 1

- Remove AI Studio dark theme global overrides.
- Replace global tokens with light console tokens:
  - `#f6f7fb` page background.
  - `#ffffff` surface cards.
  - `#0b0b0f`, `#374151`, `#6b7280` text hierarchy.
  - `#2457ff` brand blue.
  - Neutral borders and weak status backgrounds.
- Update global buttons, inputs, tabs, badges, focus rings, and cards to light defaults.
- Update `AppLayout` shell background and spacing.
- Update `WorkspaceHeader` to MiniMax-style light top navigation.
- Update homepage layout and copy for the workflow-first console.

### Later Phases

- Refactor Production Center into a two-column workbench.
- Refactor Multi-platform Workbench into large platform cards and publishing suggestions.
- Refactor WeChat publishing page for editor/preview/config readability.
- Refactor Teleprompter to keep only the stage dark while controls and editor stay light.
- Refactor Sprint1 archive page into a guided profile-completion wizard.
- Reduce duplicate visual layers inside Copilot container.

## Page Requirements

### Global Navigation

- Fixed-height 64px top bar.
- Left: product name `IP 全案工作台`.
- Center: Overview / Production / Publishing / Settings.
- Right: module menu, search entry, online teleprompter, user, logout.
- Active navigation uses brand-blue text and pale blue background, not dark pills.
- Mobile layout wraps cleanly without horizontal page overflow.

### Homepage

- Hero asks `今天要推进什么？`.
- Primary CTA: `开始生产`.
- Secondary CTA: `新建 IP`.
- Show today's task summary on the right.
- Show only the three most important continuation tasks.
- Show key metrics in a compact right column on desktop.
- Show production path as four clear steps.
- Show recent assets separately from primary actions.

### Global Components

- Cards are white with light gray border and subtle shadow.
- Inputs are white or very light gray with high-contrast text.
- Primary buttons are solid brand blue with white text.
- Secondary buttons are white with gray border and dark text.
- Status states use weak backgrounds and readable semantic colors.

## Data Needs

- Existing dashboard overview API remains sufficient for Phase 1:
  - IP completeness.
  - Task summary.
  - Asset summary.
  - Today actions.
- Phase 1 does not require backend schema changes.

## Priorities

- P0: Remove global dark overrides and restore readable light baseline.
- P0: Homepage and top navigation reflect the new direction.
- P1: Keep all existing routes and user permissions working.
- P1: Preserve the existing non-3000 Vite port configuration.
- P2: Defer complex page-specific redesigns to later phases.

## Acceptance Criteria

- Global page background is light, not dark.
- No broad `#app ... !important` dark theme override remains.
- Homepage no longer uses dark/neon command-center visuals.
- Header navigation is light, clean, and uses restrained blue active states.
- Body text, labels, inputs, and buttons are readable with strong contrast.
- Homepage first screen communicates what work should happen today.
- 375px mobile viewport has no horizontal page scroll from homepage or header.
- `npm run build` passes in `frontend/`.
- Development server does not use port `3000`.

## Risks

- Removing global dark overrides may reveal inconsistent scoped styles in older pages.
- Some legacy components may still contain local dark styles and need later page-specific refactors.
- External Google font loading can affect runtime appearance in offline environments.

## Implementation Phases

1. Phase 1: light tokens, remove dark overrides, light navigation, homepage refactor.
2. Phase 2: production center and platform workbench page-level refactors.
3. Phase 3: WeChat publishing and teleprompter readability improvements.
4. Phase 4: Sprint1 guided archive flow and Copilot container simplification.
