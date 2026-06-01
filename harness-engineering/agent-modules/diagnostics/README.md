# diagnostics

Phase 1 status: M17 redacted diagnostics export implemented.

Current responsibilities:

```text
Generate local diagnostic bundle
Scan forbidden business fields
Preview before export
Export only after user confirmation
```

Usage:

```bash
bash scripts/export-diagnostics.sh
bash scripts/export-diagnostics.sh --confirm
```

The export uses whitelist-only diagnostics. It includes counts and status summaries, and excludes case names, file names, file paths, document text, chunks, vectors, questions, answers, prompts, model secrets, and database credentials.
