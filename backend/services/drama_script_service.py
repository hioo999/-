"""短剧脚本工坊：模板 seed 与读取。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from models.persona import DramaScriptTemplate
from prompts.drama_scheme_presets import resolve_template_key
from prompts.reversal_drama_prompts import BUILTIN_DRAMA_TEMPLATES


def _template_payload(key: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": key,
        "name": data["name"],
        "description": data.get("description", ""),
        "genre_prompt": data.get("genre_prompt", ""),
        "structure_prompt": data.get("structure_prompt", ""),
        "reversal_patterns_json": json.dumps(data.get("reversal_patterns", []), ensure_ascii=False),
        "style_prompt": data.get("style_prompt", ""),
        "output_format_prompt": data.get("output_format_prompt", ""),
        "default_cast_prompt": data.get("default_cast_prompt", ""),
        "default_cast_json": json.dumps(data.get("default_cast", []), ensure_ascii=False),
        "relationship_hint": data.get("relationship_hint", ""),
        "sort_order": data.get("sort_order", 0),
        "is_active": True,
    }


def ensure_drama_templates_seeded(db: Session) -> None:
    """写入内置短剧模板，已存在则跳过。"""
    for key, data in BUILTIN_DRAMA_TEMPLATES.items():
        existing = db.query(DramaScriptTemplate).filter(DramaScriptTemplate.key == key).first()
        if existing:
            continue
        db.add(DramaScriptTemplate(**_template_payload(key, data)))
    db.commit()


def get_drama_template(db: Session, template_key: str) -> dict[str, Any]:
    """优先读数据库，缺失时回退到内置模板。"""
    template_key = resolve_template_key(template_key or "workplace_reversal")
    ensure_drama_templates_seeded(db)
    record = (
        db.query(DramaScriptTemplate)
        .filter(DramaScriptTemplate.key == template_key, DramaScriptTemplate.is_active.is_(True))
        .first()
    )
    if record:
        return record.to_prompt_dict()

    fallback = BUILTIN_DRAMA_TEMPLATES.get(template_key) or BUILTIN_DRAMA_TEMPLATES["workplace_reversal"]
    payload = _template_payload(template_key if template_key in BUILTIN_DRAMA_TEMPLATES else "workplace_reversal", fallback)
    return {
        "key": payload["key"],
        "name": payload["name"],
        "description": payload["description"],
        "genre_prompt": payload["genre_prompt"],
        "structure_prompt": payload["structure_prompt"],
        "reversal_patterns": json.loads(payload["reversal_patterns_json"]),
        "style_prompt": payload["style_prompt"],
        "output_format_prompt": payload["output_format_prompt"],
        "default_cast_prompt": payload["default_cast_prompt"],
        "default_cast": json.loads(payload["default_cast_json"]),
        "relationship_hint": payload["relationship_hint"],
    }


def list_drama_templates(db: Session) -> list[dict[str, Any]]:
    ensure_drama_templates_seeded(db)
    records = (
        db.query(DramaScriptTemplate)
        .filter(DramaScriptTemplate.is_active.is_(True))
        .order_by(DramaScriptTemplate.sort_order.asc(), DramaScriptTemplate.id.asc())
        .all()
    )
    result: list[dict[str, Any]] = []
    for record in records:
        item = record.to_dict()
        builtin = BUILTIN_DRAMA_TEMPLATES.get(record.key, {})
        item["exampleHint"] = builtin.get("example_hint", "")
        item["category"] = builtin.get("category", "通用")
        result.append(item)
    return result
