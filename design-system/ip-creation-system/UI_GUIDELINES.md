# IP Creation System UI Guidelines

## Visual Direction

Use **Light Glass SaaS Workbench** as the default product language.

The interface should feel like a professional AI content operations workspace: bright, calm, modular, readable, and action-oriented. Use visual effects to clarify hierarchy and state, not as decoration.

## Color Rules

- Primary actions use blue to purple gradients: `#2563EB` to `#7C3AED`.
- AI capability, Copilot, and intelligence cues use purple accents sparingly.
- Success, publish-ready, and pass states use green `#22C55E`.
- Warning and incomplete states use amber `#F59E0B`.
- Error and destructive actions use red `#DC2626`.
- Default canvas stays light: `#F6F8FB` with subtle blue/purple radial glows.
- Do not use full dark mode as the default workspace.
- Do not use creator-pink as the main shell color.

## Typography

- Use `Inter` plus `Noto Sans SC` globally.
- Body text should stay at least `14px`; long Chinese content should use `line-height: 1.7-1.9`.
- Headings can be bold, but avoid oversized landing-page typography in dense workbench screens.
- Use tabular or compact text only for metrics, IDs, dates, and technical metadata.

## Layout

- Desktop workspaces should prioritize task flow over decorative grids.
- The preferred IP production flow is: context selector, input, generation, refinement, quality check, publish/export.
- Use one primary CTA per area; secondary actions stay as ghost buttons.
- Keep modules as independent glass cards when they represent separate production steps.
- On mobile, collapse into a single-column task flow; avoid three-column layouts.

## Cards And Panels

- Use frosted white surfaces with subtle borders and shadows.
- Cards should have `20px-28px` radius depending on importance.
- Avoid flat ERP-like gray panels.
- Do not stack too many nested borders; use spacing and background contrast first.

## Buttons

- Primary: gradient background, white text, soft blue shadow.
- Secondary: white or translucent surface with border.
- Destructive: red text or border, only red-filled for confirmation actions.
- Buttons must have visible hover, active, disabled, and focus-visible states.
- Interactive targets should be at least `44px` high on mobile.

## Forms

- Labels must be visible; never rely on placeholder-only labels.
- Error or helper text should appear near the related field.
- Focus states must use visible blue rings.
- Long forms should be grouped by task stage: IP basics, positioning, platform, content rules.

## Generation Status

Use the same state vocabulary across modules:

- `待输入`: user has not provided required input.
- `可生成`: required input exists and generation can start.
- `生成中`: async generation is in progress.
- `已生成`: output exists.
- `已保存`: output has been persisted.
- `需优化`: quality check found issues or IP profile is incomplete.

## Empty States

Every empty state must answer:

- What is missing.
- Why it matters.
- What the user should do next.
- Which button starts the next step.

Example:

```text
还没有口播文案
先输入主题或上传素材，生成后即可发送到提词器和发布质检。
[输入主题] [上传素材]
```

## Copilot Panel

- Copilot should give contextual next steps, not generic chat filler.
- Suggested actions should map to existing buttons: parse, generate, publish package, quality check, send to teleprompter, export.
- Do not introduce a permanent right panel unless the layout has enough width; start with inline suggestion cards.

## Assets And Export

- Generated results should provide copy, export Markdown, save, and send-to-teleprompter actions where relevant.
- Export filenames should include date, module name, and a safe project/title slug.
- Content assets should keep their relationship to IP, platform, status, and update time.

## Accessibility

- Maintain text contrast of at least 4.5:1 for normal text.
- Do not use color as the only status indicator; pair color with text.
- Use `focus-visible` styles for buttons, links, inputs, selects, and textareas.
- Respect `prefers-reduced-motion`.
- Avoid emoji as structural icons; use text labels or vector icons.

## Visual Regression

Capture screenshots for these stable surfaces:

- Home dashboard.
- IP production workspace.
- IP archive/completeness page.

Use screenshots to catch layout regressions, not to over-constrain small copy changes.
