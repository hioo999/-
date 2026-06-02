"""IP 人设库 CRUD API"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.persona import Persona

router = APIRouter(prefix="/api/personas", tags=["IP人设库"])


# ─── Pydantic Schemas ─────────────────────────────────────────

class PersonaCreate(BaseModel):
    name: str = Field(..., max_length=100, description="人设名称")
    avatar_url: str = Field("", description="头像 URL")
    description: str = Field("", description="人设简介")
    tone: str = Field("专业", description="语气风格")
    speaking_style: str = Field("", description="说话风格详述")
    catchphrase: str = Field("", description="口头禅")
    target_audience: str = Field("", description="目标受众")
    professional_field: str = Field("", description="专业领域")
    reference_account: str = Field("", description="对标账号")
    forbidden_words: str = Field("", description="禁用词汇")
    full_prompt: str = Field("", description="完整人设提示词（高级）")
    sort_order: int = Field(0, description="排序权重")


class PersonaUpdate(PersonaCreate):
    is_active: bool = Field(True, description="是否启用")


# ─── CRUD 路由 ──────────────────────────────────────────────

@router.get("", summary="获取所有人设")
async def list_personas(db: Session = Depends(get_db)):
    personas = db.query(Persona).filter(Persona.is_active == True).order_by(Persona.sort_order).all()
    return {"code": 0, "data": [p.to_dict() for p in personas]}


@router.get("/{persona_id}", summary="获取单个人设详情")
async def get_persona(persona_id: int, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="人设不存在")
    return {"code": 0, "data": persona.to_dict()}


@router.post("", summary="创建新人设")
async def create_persona(data: PersonaCreate, db: Session = Depends(get_db)):
    persona = Persona(**data.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return {"code": 0, "data": persona.to_dict(), "message": "创建成功"}


@router.put("/{persona_id}", summary="更新人设")
async def update_persona(persona_id: int, data: PersonaUpdate, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="人设不存在")
    for key, value in data.model_dump().items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return {"code": 0, "data": persona.to_dict(), "message": "更新成功"}


@router.delete("/{persona_id}", summary="删除人设（软删除）")
async def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise HTTPException(status_code=404, detail="人设不存在")
    persona.is_active = False
    db.commit()
    return {"code": 0, "message": "删除成功"}
