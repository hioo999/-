"""Short-video workflow routing APIs."""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_routes import get_current_user
from database import get_db
from models.persona import ShortVideoProject, UserAccount
from services.short_video_workflow import INTENT_CONFIGS, build_short_video_workflow


router = APIRouter(prefix="/api/short-video", tags=["AI短视频工作流"])


class ShortVideoWorkflowRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="用户自然语言需求")
    requested_intent: str = Field("auto", description="auto 或指定 intent key")
    subject_name: str = Field("主体", description="主体名称")
    platform: str = Field("抖音/小红书", description="目标平台")
    aspect_ratio: str = Field("9:16", description="画面比例")
    duration: str = Field("15秒", description="视频时长")
    model: str = Field("即梦2.0", description="目标视频模型")
    style: str = Field("高级、真实、有记忆点", description="情绪基调或画面风格")
    target_audience: str = Field("目标用户", description="目标受众")
    core_message: str = Field("核心卖点或核心观点", description="核心表达")


class ShortVideoDetectRequest(BaseModel):
    user_input: str = Field(..., min_length=1, description="用户自然语言需求")
    requested_intent: str = Field("auto", description="auto 或指定 intent key")


class ShortVideoProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="项目标题")
    subject_name: str = Field("", description="主体名称")
    intent_key: str = Field("", description="识别场景 key")
    intent_label: str = Field("", description="识别场景名称")
    confidence: float = Field(0, description="识别置信度")
    platform: str = Field("", description="目标平台")
    aspect_ratio: str = Field("", description="画面比例")
    duration: str = Field("", description="视频时长")
    model: str = Field("", description="目标视频模型")
    style: str = Field("", description="风格")
    target_audience: str = Field("", description="目标受众")
    core_message: str = Field("", description="核心表达")
    user_input: str = Field("", description="原始用户需求")
    workflow: dict = Field(default_factory=dict, description="完整工作流对象")
    archive_markdown: str = Field("", description="归档 Markdown")
    notes: str = Field("", description="备注")


@router.get("/intents", summary="获取短视频工作流场景列表")
async def list_short_video_intents():
    return {
        "code": 0,
        "data": [
            {
                "key": config.key,
                "label": config.label,
                "command": config.command,
                "template_doc": config.template_doc,
                "keywords": list(config.keywords),
                "steps": list(config.steps),
            }
            for config in INTENT_CONFIGS.values()
        ],
    }


@router.post("/workflow", summary="自动识别并生成短视频工作流")
async def build_workflow(data: ShortVideoWorkflowRequest):
    workflow = build_short_video_workflow(**data.model_dump())
    return {"code": 0, "data": workflow}


@router.post("/projects", summary="保存短视频项目归档")
async def create_short_video_project(
    data: ShortVideoProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    project = ShortVideoProject(
        user_id=current_user.id,
        title=data.title.strip(),
        subject_name=data.subject_name,
        intent_key=data.intent_key,
        intent_label=data.intent_label,
        confidence=str(data.confidence),
        platform=data.platform,
        aspect_ratio=data.aspect_ratio,
        duration=data.duration,
        model=data.model,
        style=data.style,
        target_audience=data.target_audience,
        core_message=data.core_message,
        user_input=data.user_input,
        workflow_json=json.dumps(data.workflow, ensure_ascii=False),
        archive_markdown=data.archive_markdown,
        notes=data.notes,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"code": 0, "data": project.to_dict(), "message": "保存成功"}


@router.get("/projects", summary="获取短视频项目归档列表")
async def list_short_video_projects(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    safe_limit = max(1, min(limit, 200))
    projects = (
        db.query(ShortVideoProject)
        .filter(ShortVideoProject.user_id == current_user.id, ShortVideoProject.is_active == True)
        .order_by(ShortVideoProject.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    return {"code": 0, "data": [project.to_dict(include_content=False) for project in projects]}


@router.get("/projects/{project_id}", summary="获取短视频项目归档详情")
async def get_short_video_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user),
):
    project = db.query(ShortVideoProject).filter(
        ShortVideoProject.id == project_id,
        ShortVideoProject.user_id == current_user.id,
    ).first()
    if not project or not project.is_active:
        raise HTTPException(status_code=404, detail="短视频项目不存在")
    return {"code": 0, "data": project.to_dict(include_content=True)}
