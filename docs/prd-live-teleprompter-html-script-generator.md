# PRD: Live Teleprompter HTML Script Generator

## Background

The existing online teleprompter supports script playback, fullscreen reading, multi-script queues, local persistence, cloud drafts, and recording assist. Users now need a dedicated live-stream teleprompter generator that can turn product, host, schedule, and offer information into a complete HTML live script similar to a finished live selling run-of-show.

The feature is different from short-video talking scripts: live scripts need time segments, product sequencing, host roles, live interaction prompts, conversion language, return segments, and an HTML page that can be opened directly during a livestream.

## Goals

- Add an independent live teleprompter generation workflow inside the teleprompter tool.
- Support 1-person and 2-person livestream scripts.
- Support multi-product run-of-show editing with product positioning and duration.
- Generate both plain text and HTML teleprompter output.
- Allow generated plain text to be sent into the existing online teleprompter player.
- Provide export/copy/fullscreen preview actions for live operation.

## User Flow

1. User opens `直播提词器` from the home page or header.
2. User enters livestream basics: theme, platform, start time, duration, GMV target, audience, style, benefits, and hosts.
3. User adds products in the intended live order and fills price, offer, pain points, selling points, audience, FAQ, and notes.
4. User clicks `生成直播台本`.
5. System returns structured sections, plain text, and a full HTML teleprompter page.
6. User can preview HTML, copy HTML, copy plain text, download HTML, or send plain text into the online teleprompter player.

## Functional Scope

### MVP

- `直播台本生成` tab inside `/tools/teleprompter`.
- `在线提词播放` tab preserving the existing player.
- Rule-based backend generation endpoint for stable output even when AI providers are not configured.
- HTML output with:
  - fixed title bar
  - current time display
  - optional GMV badge
  - bottom quick navigation
  - time sections
  - host A/B styling
  - action prompts
  - must-remember list
  - compliance and field-control reminders
  - fullscreen and simple font/auto-scroll controls
- Product run-of-show form with add/remove product support.
- Copy HTML, copy plain text, export HTML, fullscreen preview.
- Send generated plain text to the existing teleprompter player.

### Out Of Scope For MVP

- Persisting generated live scripts as a separate database entity.
- AI model customization per live script.
- Drag-and-drop product ordering.
- Team collaboration or field-control multi-device sync.
- Industry-specific template library beyond the first generic strong-conversion structure.

## Phase 2 Functional Scope

- Advanced medical-beauty live template based on the completed 3.19 anti-inflammatory season run-of-show structure.
- Product table import from pasted Excel/CSV rows, with automatic mapping for product name, category, price, offer, selling points, and pain points.
- Pre-generation checklist for missing prices, weak selling points, missing offers, missing return products, and risky compliance phrases.
- HTML theme selection: dark live room, high contrast, medical green, beauty pink, black gold, minimal big text, and mobile landscape.
- Live control mode for field operators: current section, next section, big-script view, and quick section jump.
- Live review report generation after the stream, including actual GMV, product performance, winning lines, weak products, audience questions, and next-session suggestions.
- Admin template management for custom live-script templates.

## Page/API/Data Needs

### Frontend

- New component: `frontend/src/components/LiveTeleprompterGenerator.vue`.
- Extend `frontend/src/api/teleprompter.api.ts` with live script payload/result types and generator call.
- Update `frontend/src/views/CopilotWorkspace.vue` to show two teleprompter tabs.
- Update home/header navigation labels to expose `直播提词器`.

### Backend

- Add `POST /api/teleprompter/live-script/generate`.
- Request includes livestream metadata, hosts, benefits, compliance mode, and products.
- Response includes `plainText`, `html`, `sections`, `mustRemember`, `complianceTips`, and `generatedBy`.
- Escape all user-provided content before embedding it into generated HTML.

### Data

- MVP is stateless. Generated results are returned to the browser only.
- Existing teleprompter draft storage remains available when users send plain text into the online player.

## Priorities

- P0: Stable HTML and plain-text generation.
- P0: 1-person and 2-person host structure.
- P0: Product sequencing and product cards.
- P0: Copy/export/preview/send-to-player actions.
- P1: More industry templates and AI rewrite quality.
- P1: Persist generated live script history.
- P2: Drag sorting, mobile field-control mode, shared live queue.

## Acceptance Criteria

- User can open the live teleprompter generator from the home page and header route.
- User can generate a live script with at least one product.
- 1-person mode outputs single-host lines.
- 2-person mode outputs host A/B dialogue and distinct HTML host badges.
- Generated HTML contains quick navigation and can render in an iframe preview.
- User can copy HTML, copy plain text, and download an `.html` file.
- User can send generated plain text into the existing online teleprompter player.
- Backend escapes HTML-sensitive characters from user input.
- Frontend build and targeted backend tests pass.
- User can import product rows from pasted table text.
- User can run preflight checks before generation.
- User can select a visual HTML theme before generation.
- User can generate a post-live review report.
- Admin user can create, update, list, and delete custom live templates.

## Risks

- Rule-based generation may be less creative than model-based generation.
- Long product lists can generate large HTML, so MVP caps backend products at 20.
- Livestream compliance varies by category; MVP adds reminders but does not replace human review.
- Browser clipboard and download behavior can vary by device.

## Implementation Phases

1. MVP generator and export workflow.
2. Industry templates:医美/护肤、大健康、本地生活、课程、服装、食品、单品强转化、多品排品.
3. AI enhancement: model selection, tone rewrite, stronger FAQ and objection handling.
4. Generated script persistence and reusable live template history.
5. Field-control mode: shared navigation, product jump commands, mobile horizontal prompt mode.
