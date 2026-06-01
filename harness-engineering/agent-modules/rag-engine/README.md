# rag-engine

Responsibilities:

```text
Embedding calls
Qdrant vector writes
case_id-filtered semantic retrieval
case_id-filtered keyword retrieval
Prompt construction
OpenAI Compatible chat call
Citation generation
Insufficient-evidence guard
```

P0 rule:

```text
Every retrieval path must filter by case_id before returning chunks or citations.
```
