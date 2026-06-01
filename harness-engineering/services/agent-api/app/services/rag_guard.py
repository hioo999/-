"""RAG answer guardrails for source-backed answers."""

from __future__ import annotations


INSUFFICIENT_EVIDENCE_MESSAGE = "当前案件材料中未检索到充分依据，无法给出确定结论。"


def should_refuse_without_sources(citations: list[object]) -> bool:
    return len(citations) == 0


def answer_or_refuse(answer: str, citations: list[object]) -> dict[str, object]:
    if should_refuse_without_sources(citations):
        return {"answer": INSUFFICIENT_EVIDENCE_MESSAGE, "citations": [], "insufficient_evidence": True}
    return {"answer": answer, "citations": citations, "insufficient_evidence": False}
