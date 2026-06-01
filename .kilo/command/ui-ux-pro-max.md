---
description: Apply UI/UX Pro Max design intelligence
---

Use the installed project skill at @.kilo/skills/ui-ux-pro-max/SKILL.md.

Project context:
- Product: lawyer local data-sovereign AI case knowledge-base workspace
- Frontend stack: React + TypeScript + Vite + Ant Design
- Primary app: `harness-engineering/apps/agent-console`

Workflow:
- Treat `$ARGUMENTS` as the UI/UX task or page/component to design, review, or improve.
- Start by generating a design-system recommendation with `.kilo/skills/ui-ux-pro-max/scripts/search.py` when the task involves a new page, major redesign, visual direction, color, typography, or layout decisions.
- Supplement with targeted `--domain ux`, `--domain style`, `--domain color`, `--domain typography`, and `--stack react` searches as needed.
- Apply recommendations pragmatically to the existing Ant Design visual system instead of replacing the whole stack.
- Preserve legal-domain trust, readability, accessibility, local-first privacy messaging, and dashboard usability.

User request:
$ARGUMENTS
