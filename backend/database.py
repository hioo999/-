"""数据库配置与会话管理"""

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from models.persona import Base, UserAccount
from services.auth_security import hash_password

# 数据库连接 URL（从环境变量读取，遵循规范禁止硬编码）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ip_system.db"  # 开发环境默认使用 SQLite
)

# 生产环境请通过 DATABASE_URL 注入 MySQL/PostgreSQL 等连接串，不要写入源码。

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)
    _ensure_user_account_columns()
    _ensure_generation_history_columns()
    _ensure_prompt_template_columns()
    _ensure_ai_model_config_columns()
    _ensure_platform_restructure_columns()
    _ensure_wechat_columns()
    _ensure_admin_account()


def _ensure_admin_account():
    """按环境变量创建或提升管理员账号。"""
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password:
        return
    admin_email = os.getenv("ADMIN_EMAIL", "admin@163.com").strip().lower()
    admin_name = os.getenv("ADMIN_NAME", "管理员").strip() or "管理员"
    with SessionLocal() as db:
        user = db.query(UserAccount).filter(UserAccount.email == admin_email).first()
        if user:
            changed = False
            if not user.is_admin:
                user.is_admin = True
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                db.commit()
            return
        db.add(UserAccount(
            name=admin_name,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_admin=True,
        ))
        db.commit()


def _ensure_user_account_columns():
    """轻量补齐 SQLite 开发库用户权限字段。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "user_accounts" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("user_accounts")}
    columns = {
        "is_admin": "BOOLEAN DEFAULT 0",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE user_accounts ADD COLUMN {name} {ddl}"))


def _ensure_generation_history_columns():
    """轻量补齐 SQLite 开发库新增字段，避免没有迁移工具时旧库启动失败。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "generation_history" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("generation_history")}
    columns = {
        "prompt_template_id": "INTEGER DEFAULT 0",
        "prompt_template_key": "VARCHAR(100) DEFAULT ''",
        "prompt_template_version": "VARCHAR(30) DEFAULT ''",
        "prompt_template_category": "VARCHAR(80) DEFAULT ''",
        "text_model_config_id": "INTEGER DEFAULT 0",
        "cover_prompt_template_id": "INTEGER DEFAULT 0",
        "cover_model_config_id": "INTEGER DEFAULT 0",
        "video_prompt_template_id": "INTEGER DEFAULT 0",
        "video_model_config_id": "INTEGER DEFAULT 0",
        "generation_params_json": "TEXT DEFAULT '{}'",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE generation_history ADD COLUMN {name} {ddl}"))


def _ensure_prompt_template_columns():
    """补齐生成模板从口播扩展到多模态所需字段。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "prompt_template_categories" in table_names:
            existing = {column["name"] for column in inspector.get_columns("prompt_template_categories")}
            if "template_type" not in existing:
                conn.execute(text("ALTER TABLE prompt_template_categories ADD COLUMN template_type VARCHAR(50) DEFAULT 'text_script'"))
        if "prompt_templates" in table_names:
            existing = {column["name"] for column in inspector.get_columns("prompt_templates")}
            columns = {
                "template_type": "VARCHAR(50) DEFAULT 'text_script'",
                "platform": "VARCHAR(80) DEFAULT ''",
                "scene": "VARCHAR(120) DEFAULT ''",
                "step": "VARCHAR(120) DEFAULT ''",
                "user_prompt_hint": "TEXT DEFAULT ''",
                "default_params_json": "TEXT DEFAULT '{}'",
                "default_model_config_id": "INTEGER DEFAULT 0",
            }
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE prompt_templates ADD COLUMN {name} {ddl}"))


def _ensure_ai_model_config_columns():
    """补齐模型中转和推荐字段，兼容旧 SQLite 开发库。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "ai_model_configs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("ai_model_configs")}
    columns = {
        "user_id": "INTEGER DEFAULT 0",
        "gateway_id": "INTEGER DEFAULT 0",
        "recommendation_label": "VARCHAR(120) DEFAULT ''",
        "recommendation_reason": "TEXT DEFAULT ''",
        "risk_note": "TEXT DEFAULT ''",
        "last_seen_at": "DATETIME",
    }
    with engine.begin() as conn:
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE ai_model_configs ADD COLUMN {name} {ddl}"))


def _ensure_wechat_columns():
    """补齐公众号发布表的新增稳定性字段。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "wechat_draft_records" in table_names:
            existing = {column["name"] for column in inspector.get_columns("wechat_draft_records")}
            columns = {
                "idempotency_key": "VARCHAR(120) DEFAULT ''",
                "project_id": "INTEGER DEFAULT 0",
                "topic_id": "INTEGER DEFAULT 0",
                "platform_content_id": "INTEGER DEFAULT 0",
                "task_id": "INTEGER DEFAULT 0",
                "theme_id": "VARCHAR(120) DEFAULT ''",
                "cover_asset_id": "INTEGER DEFAULT 0",
                "contains_ai_images": "BOOLEAN DEFAULT 0",
                "preflight_result_json": "TEXT DEFAULT '{}'",
            }
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE wechat_draft_records ADD COLUMN {name} {ddl}"))
        if "wechat_accounts" in table_names:
            existing = {column["name"] for column in inspector.get_columns("wechat_accounts")}
            columns = {
                "scope": "VARCHAR(30) DEFAULT 'system'",
                "authorized_user_ids_json": "TEXT DEFAULT '[]'",
            }
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE wechat_accounts ADD COLUMN {name} {ddl}"))


def _ensure_platform_restructure_columns():
    """补齐平台化重构核心表字段。"""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    patch_map = {
        "ip_projects": {
            "is_active": "BOOLEAN DEFAULT 1",
        },
        "content_topics": {
            "is_active": "BOOLEAN DEFAULT 1",
        },
        "source_materials": {
            "is_active": "BOOLEAN DEFAULT 1",
        },
        "platform_contents": {
            "is_active": "BOOLEAN DEFAULT 1",
        },
        "assets": {
            "status": "VARCHAR(40) DEFAULT 'active'",
        },
        "generation_tasks": {
            "raw_response_excerpt": "TEXT DEFAULT ''",
            "retry_count": "INTEGER DEFAULT 0",
            "parent_task_id": "INTEGER DEFAULT 0",
        },
        "video_aip_projects": {
            "user_id": "INTEGER DEFAULT 0",
            "source_type": "VARCHAR(80) DEFAULT 'manual'",
            "source_ref_id": "INTEGER DEFAULT 0",
            "source_assets_json": "TEXT DEFAULT '[]'",
        },
        "short_video_projects": {
            "user_id": "INTEGER DEFAULT 0",
        },
    }
    with engine.begin() as conn:
        for table_name, columns in patch_map.items():
            if table_name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


def get_db() -> Session:
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
