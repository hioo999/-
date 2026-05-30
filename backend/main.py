"""直播 AIP 打造全案系统 - FastAPI 入口

启动命令：uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import logging
from dotenv import load_dotenv

# 在所有模块 import 之前加载 .env，确保 AIService 能读取 API Key
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from api.persona_routes import router as persona_router
from api.auth_routes import router as auth_router
from api.copilot_routes import router as copilot_router
from api.video_routes import router as video_router
from api.short_video_routes import router as short_video_router
from api.sprint1_routes import router as sprint1_router
from api.teleprompter_routes import router as teleprompter_router
from video_engine import runtime as video_runtime

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_cors_origins() -> list[str]:
    raw = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:13000,http://127.0.0.1:13000,http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 IP 打造全案系统启动中...")
    init_db()
    logger.info("✅ 数据库初始化完成")
    # video_engine 启动失败不阻塞主服务（路由会返回 503）
    await video_runtime.startup()
    if video_runtime.ENGINE_STATE.ready:
        logger.info("🎬 视频引擎已就绪")
    else:
        logger.warning("⚠️  视频引擎未就绪：%s", video_runtime.ENGINE_STATE.error)
    yield
    await video_runtime.shutdown()
    logger.info("👋 系统关闭")


app = FastAPI(
    title="直播 AIP 打造全案系统",
    description="将素材一键转化为口播文案、视频分镜提示词和封面提示词的 AI Copilot 工作台",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件：生产环境通过 BACKEND_CORS_ORIGINS 指定明确域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(persona_router)
app.include_router(copilot_router)
app.include_router(video_router)
app.include_router(short_video_router)
app.include_router(sprint1_router)
app.include_router(teleprompter_router)


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点（Docker 容器健康检查使用）"""
    return {"status": "ok", "service": "ip-system-backend"}


@app.get("/", tags=["首页"])
async def root():
    return {
        "name": "直播 AIP 打造全案系统",
        "version": "1.0.0",
        "docs": "/docs",
    }
