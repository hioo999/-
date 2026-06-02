"""微信公众号排版、素材上传与草稿箱发布服务。"""

from __future__ import annotations

import base64
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken


WECHAT_API = "https://api.weixin.qq.com/cgi-bin"
DEFAULT_RENDER_API = "https://feishu2weixin.maolai.cc"
TOKEN_TTL_SECONDS = 6800
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_BODY_IMAGES = 20
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}

MaterialLookup = Callable[[str, str], dict[str, str] | None]
MaterialSave = Callable[[str, str, dict[str, Any]], None]


class WechatPublishError(Exception):
    def __init__(self, code: str, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.payload = payload or {}


@dataclass
class WechatAccountConfig:
    app_id: str
    app_secret: str
    feishu_account: str = ""
    theme_id: str = ""
    api_base: str = DEFAULT_RENDER_API
    default_cover_url: str = ""


WECHAT_ERROR_GUIDE = {
    "40013": "AppID 无效，请检查公众号 AppID 是否填写正确。",
    "40125": "AppSecret 无效，请在公众号后台重新生成并更新密钥。",
    "40164": "服务器 IP 不在公众号 API 白名单，请到公众号后台基础配置添加服务器公网 IPv4。",
    "48001": "公众号接口权限不足，请确认账号类型和接口权限是否支持草稿/素材接口。",
    "45009": "微信接口调用频率达到上限，请稍后重试。",
    "40007": "媒体文件 ID 不合法，请重新上传封面素材。",
    "40097": "接口参数错误，请检查标题、正文、封面和图片格式。",
    "41006": "缺少 media_id，请确认封面素材上传成功。",
}


THEMES = {
    "knowledge": {
        "primary": "#2563eb",
        "accent": "#dbeafe",
        "text": "#1f2937",
        "muted": "#64748b",
        "surface": "#f8fafc",
        "quote": "#eff6ff",
    },
    "ip": {
        "primary": "#7c3aed",
        "accent": "#ede9fe",
        "text": "#22172f",
        "muted": "#6d5a7d",
        "surface": "#fbf7ff",
        "quote": "#f5f0ff",
    },
    "business": {
        "primary": "#b45309",
        "accent": "#fef3c7",
        "text": "#241a0f",
        "muted": "#78716c",
        "surface": "#fffbeb",
        "quote": "#fff7d6",
    },
    "emotion": {
        "primary": "#db2777",
        "accent": "#fce7f3",
        "text": "#35111f",
        "muted": "#8a4b63",
        "surface": "#fff7fb",
        "quote": "#fdf2f8",
    },
    "minimal": {
        "primary": "#111827",
        "accent": "#f1f5f9",
        "text": "#111827",
        "muted": "#64748b",
        "surface": "#ffffff",
        "quote": "#f8fafc",
    },
}


def encrypt_secret(secret: str) -> str:
    if not secret:
        return ""
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise WechatPublishError("secret_decrypt_failed", "公众号密钥解密失败，请重新保存 AppSecret") from exc


def _fernet() -> Fernet:
    seed = os.getenv("WECHAT_CREDENTIAL_KEY", "")
    if not seed:
        env = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()
        if env in {"prod", "production"}:
            raise WechatPublishError("missing_credential_key", "生产环境必须配置 WECHAT_CREDENTIAL_KEY 后才能保存公众号密钥")
        seed = "ip-system-local-dev-key"
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode("utf-8")).digest())
    return Fernet(key)


def extract_first_image(markdown: str) -> str:
    stripped = re.sub(r"```[\s\S]*?```", "", markdown or "")
    match = re.search(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", stripped)
    return match.group(1) if match else ""


def extract_markdown_images(markdown: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", markdown or "")
    return re.findall(r"!\[[^\]]*\]\((https?://[^)\s]+)\)", stripped)


def explain_wechat_error(errcode: str | int, errmsg: str = "") -> str:
    code = str(errcode)
    base = WECHAT_ERROR_GUIDE.get(code, "微信接口返回错误，请根据错误码检查账号权限、参数和网络状态。")
    return f"{base}（错误码 {code}）" if not errmsg else f"{base} 原始信息：{errmsg}（错误码 {code}）"


def preflight_wechat_article(
    title: str,
    markdown: str,
    digest: str = "",
    cover_url: str = "",
    default_cover_url: str = "",
    allow_local_asset: bool = False,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def add(level: str, code: str, message: str, suggestion: str) -> None:
        issues.append({"level": level, "code": code, "message": message, "suggestion": suggestion})

    safe_title = (title or "").strip()
    safe_markdown = (markdown or "").strip()
    if not safe_title:
        add("error", "title_required", "文章标题不能为空", "填写一个清晰的公众号标题")
    if len(safe_title) > 64:
        add("warning", "title_too_long", "标题较长，可能影响公众号列表展示", "建议控制在 64 字以内")
    if not safe_markdown:
        add("error", "content_required", "正文不能为空", "先填写或导入二创后的文章内容")
    if len(digest or "") > 120:
        add("warning", "digest_too_long", "摘要超过 120 字，发送时会被截断", "建议压缩为 60-120 字")

    images = extract_markdown_images(safe_markdown)
    selected_cover = (cover_url or "").strip() or (images[0] if images else "") or (default_cover_url or "").strip()
    if not selected_cover:
        add("error", "cover_required", "公众号草稿必须有封面图", "填写封面图 URL、在正文插入图片，或为账号配置默认封面")
    elif selected_cover.startswith("http://"):
        add("warning", "cover_http", "封面图使用 HTTP 地址", "建议改用 HTTPS 图片地址，降低下载和中间人风险")
    if len(images) > MAX_BODY_IMAGES:
        add("error", "too_many_images", f"正文图片超过 {MAX_BODY_IMAGES} 张", "删减图片或拆成多篇文章")

    for url in [selected_cover, *images]:
        if not url:
            continue
        if allow_local_asset and url.startswith("file://"):
            continue
        try:
            _validate_public_url(url, require_https=False)
        except WechatPublishError as exc:
            add("error", exc.code, f"图片地址不可用：{url}", exc.message)

    placeholder_patterns = [r"TODO", r"待补充", r"这里填写", r"XXX", r"你的[\u4e00-\u9fa5]*"]
    if any(re.search(pattern, safe_markdown, re.I) for pattern in placeholder_patterns):
        add("warning", "placeholder_found", "正文中疑似存在未替换占位符", "发送前请检查 TODO、XXX、待补充等内容")

    blocking_risky_patterns = [r"最[好佳强快]", r"百分百", r"100%", r"保证", r"包治", r"稳赚", r"无风险"]
    if any(re.search(pattern, safe_markdown) for pattern in blocking_risky_patterns):
        add("error", "compliance_risk", "正文中存在绝对化或高风险承诺表达", "删除或改写绝对化、医疗功效、金融收益和无风险承诺后再发送")

    return {
        "canSend": not any(issue["level"] == "error" for issue in issues),
        "issues": issues,
        "imageCount": len(images),
        "selectedCoverUrl": selected_cover,
    }


async def render_markdown_for_wechat(
    markdown: str,
    style: str = "knowledge",
    feishu_account: str = "",
    theme_id: str = "",
    api_base: str = DEFAULT_RENDER_API,
) -> str:
    if feishu_account and theme_id:
        return sanitize_wechat_html(await _render_with_feishu2wechat(markdown, feishu_account, theme_id, api_base))
    return sanitize_wechat_html(render_markdown_locally(markdown, style))


async def list_remote_themes(feishu_account: str, api_base: str = DEFAULT_RENDER_API) -> dict[str, Any]:
    if not feishu_account.strip():
        raise WechatPublishError("missing_account", "请先填写 feishu2weixin 注册账号")
    safe_api_base = _safe_render_api_base(api_base)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{safe_api_base}/api/skill",
            headers={"Content-Type": "application/json", "X-Account": feishu_account.strip()},
            json={"action": "list_themes"},
        )
    if response.status_code >= 400:
        raise WechatPublishError("render_api_http_error", f"主题查询接口返回 HTTP {response.status_code}")
    data = response.json()
    if not data.get("success"):
        raise WechatPublishError("render_api_error", data.get("error") or "主题查询失败", data)
    return data


async def get_access_token(app_id: str, app_secret: str) -> str:
    cache_key = hashlib.sha256(f"{app_id}:{app_secret}".encode("utf-8")).hexdigest()
    cached = _TOKEN_CACHE.get(cache_key)
    if cached and cached[1] > time.time():
        return cached[0]

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{WECHAT_API}/token",
            params={"grant_type": "client_credential", "appid": app_id, "secret": app_secret},
        )
    data = response.json()
    if data.get("errcode"):
        raise _wechat_error("wechat_token", data)
    token = data.get("access_token")
    if not token:
        raise WechatPublishError("token_empty", f"获取 access_token 返回异常：{json.dumps(data, ensure_ascii=False)}", data)
    _TOKEN_CACHE[cache_key] = (token, time.time() + TOKEN_TTL_SECONDS)
    return token


async def probe_wechat_capabilities(token: str) -> list[dict[str, Any]]:
    """Probe core WeChat API permissions without creating a real draft."""
    checks: list[dict[str, Any]] = []

    async def add_check(name: str, ok: bool, message: str, payload: dict[str, Any] | None = None) -> None:
        checks.append({"name": name, "ok": ok, "message": message, "payload": payload or {}})

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            material_response = await client.get(f"{WECHAT_API}/material/get_materialcount", params={"access_token": token})
            material_data = material_response.json()
            if material_data.get("errcode"):
                await add_check("cover_material_api", False, explain_wechat_error(material_data.get("errcode"), material_data.get("errmsg", "")), material_data)
            else:
                await add_check("cover_material_api", True, "永久素材接口可访问，封面上传权限具备基础条件。", material_data)
        except Exception as exc:
            await add_check("cover_material_api", False, f"永久素材接口检测失败：{exc}")

        tiny_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
        try:
            upload_response = await client.post(
                f"{WECHAT_API}/media/uploadimg",
                params={"access_token": token},
                files={"media": ("permission-probe.png", tiny_png, "image/png")},
            )
            upload_data = upload_response.json()
            if upload_data.get("errcode"):
                await add_check("body_image_upload", False, explain_wechat_error(upload_data.get("errcode"), upload_data.get("errmsg", "")), upload_data)
            else:
                await add_check("body_image_upload", True, "正文图片上传接口可访问。", {"url": upload_data.get("url", "")})
        except Exception as exc:
            await add_check("body_image_upload", False, f"正文图片上传接口检测失败：{exc}")

        try:
            draft_response = await client.post(
                f"{WECHAT_API}/draft/add",
                params={"access_token": token},
                json={"articles": [{"title": "权限检测", "content": "<p>权限检测</p>", "thumb_media_id": "invalid_media_id_for_permission_probe"}]},
            )
            draft_data = draft_response.json()
            errcode = str(draft_data.get("errcode", ""))
            if draft_data.get("media_id") or errcode in {"40007", "40097", "41006"}:
                await add_check("draft_add", True, "草稿接口可访问，真实发送时需提供有效封面 media_id。", draft_data)
            elif draft_data.get("errcode"):
                await add_check("draft_add", False, explain_wechat_error(draft_data.get("errcode"), draft_data.get("errmsg", "")), draft_data)
            else:
                await add_check("draft_add", True, "草稿接口返回正常。", draft_data)
        except Exception as exc:
            await add_check("draft_add", False, f"草稿接口检测失败：{exc}")

    return checks


async def publish_markdown_to_draft(
    config: WechatAccountConfig,
    title: str,
    markdown: str,
    author: str = "",
    digest: str = "",
    cover_url: str = "",
    content_source_url: str = "",
    style: str = "knowledge",
    material_lookup: MaterialLookup | None = None,
    material_save: MaterialSave | None = None,
) -> dict[str, Any]:
    html_content = await render_markdown_for_wechat(
        markdown,
        style=style,
        feishu_account=config.feishu_account,
        theme_id=config.theme_id,
        api_base=config.api_base,
    )
    token = await get_access_token(config.app_id, config.app_secret)
    selected_cover = cover_url.strip() or extract_first_image(markdown) or config.default_cover_url.strip()
    if not selected_cover:
        raise WechatPublishError("missing_cover", "公众号草稿必须提供封面图，请填写封面 URL 或在正文中插入图片")
    thumb_media_id = await upload_cover_image(selected_cover, token, material_lookup=material_lookup, material_save=material_save)
    processed_html = await upload_and_replace_body_images(html_content, token, material_lookup=material_lookup, material_save=material_save)
    processed_html = sanitize_wechat_html(processed_html)
    media_id = await push_draft(
        token=token,
        title=title,
        author=author,
        digest=digest,
        html_content=processed_html,
        thumb_media_id=thumb_media_id,
        content_source_url=content_source_url,
    )
    return {
        "mediaId": media_id,
        "thumbMediaId": thumb_media_id,
        "coverUrl": selected_cover,
        "formattedHtml": processed_html,
    }


async def upload_cover_image(image_url: str, token: str, material_lookup: MaterialLookup | None = None, material_save: MaterialSave | None = None) -> str:
    cached = material_lookup("cover", image_url) if material_lookup else None
    if cached and cached.get("mediaId"):
        return cached["mediaId"]
    filename, content_type, content = await _download_image(image_url, "cover.jpg")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{WECHAT_API}/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (filename, content, content_type)},
        )
    data = response.json()
    if data.get("errcode"):
        raise _wechat_error("wechat_cover", data)
    media_id = data.get("media_id")
    if not media_id:
        raise WechatPublishError("upload_no_media_id", "封面上传成功但微信未返回 media_id", data)
    if material_save:
        material_save("cover", image_url, {"mediaId": media_id, "contentType": content_type, "byteSize": len(content)})
    return media_id


async def upload_and_replace_body_images(html_content: str, token: str, material_lookup: MaterialLookup | None = None, material_save: MaterialSave | None = None) -> str:
    wechat_domains = ("mmbiz.qpic.cn", "mmbiz.qlogo.cn", "res.wx.qq.com")
    urls = sorted({m.group(1) for m in re.finditer(r'\bsrc="(https?://[^"]+)"', html_content)})
    if len(urls) > MAX_BODY_IMAGES:
        raise WechatPublishError("too_many_images", f"正文图片最多支持 {MAX_BODY_IMAGES} 张，请删减后再发送")
    replacements: dict[str, str] = {}
    for url in urls:
        if any(domain in url for domain in wechat_domains):
            continue
        try:
            replacements[url] = await upload_body_image(url, token, material_lookup=material_lookup, material_save=material_save)
        except WechatPublishError:
            raise
        except Exception:
            continue
    result = html_content
    for original, replacement in replacements.items():
        result = result.replace(original, replacement)
    return result


async def upload_body_image(image_url: str, token: str, material_lookup: MaterialLookup | None = None, material_save: MaterialSave | None = None) -> str:
    cached = material_lookup("body", image_url) if material_lookup else None
    if cached and cached.get("wechatUrl"):
        return cached["wechatUrl"]
    filename, content_type, content = await _download_image(image_url, "body.jpg")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{WECHAT_API}/media/uploadimg",
            params={"access_token": token},
            files={"media": (filename, content, content_type)},
        )
    data = response.json()
    if data.get("errcode"):
        raise _wechat_error("wechat_body_image", data)
    url = data.get("url")
    if not url:
        raise WechatPublishError("uploadimg_no_url", "正文图片上传成功但微信未返回 URL", data)
    if material_save:
        material_save("body", image_url, {"wechatUrl": url, "contentType": content_type, "byteSize": len(content)})
    return url


async def push_draft(
    token: str,
    title: str,
    author: str,
    digest: str,
    html_content: str,
    thumb_media_id: str,
    content_source_url: str = "",
) -> str:
    article: dict[str, Any] = {
        "title": title,
        "content": html_content,
        "thumb_media_id": thumb_media_id,
        "show_cover_pic": 1,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    if author:
        article["author"] = author
    if digest:
        article["digest"] = digest[:120]
    if content_source_url:
        article["content_source_url"] = content_source_url

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{WECHAT_API}/draft/add",
            params={"access_token": token},
            json={"articles": [article]},
        )
    data = response.json()
    if data.get("errcode"):
        raise _wechat_error("wechat_draft", data)
    media_id = data.get("media_id")
    if not media_id:
        raise WechatPublishError("draft_no_media_id", "草稿创建成功但微信未返回 media_id", data)
    return media_id


async def _render_with_feishu2wechat(markdown: str, account: str, theme_id: str, api_base: str) -> str:
    safe_api_base = _safe_render_api_base(api_base)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{safe_api_base}/api/skill",
            headers={
                "Content-Type": "application/json",
                "X-Account": account.strip(),
                "X-Theme-Id": theme_id.strip(),
            },
            json={"action": "render", "markdown": markdown},
        )
    if response.status_code >= 400:
        raise WechatPublishError("render_api_http_error", f"排版服务返回 HTTP {response.status_code}")
    data = response.json()
    if not data.get("success"):
        raise WechatPublishError("render_api_error", data.get("error") or "排版服务渲染失败", data)
    html_content = data.get("html") or ""
    if not html_content:
        raise WechatPublishError("empty_html", "排版服务返回空 HTML")
    return html_content


async def _download_image(image_url: str, fallback_name: str) -> tuple[str, str, bytes]:
    if image_url.startswith("file://"):
        path = os.path.abspath(image_url[7:])
        ext = os.path.splitext(path)[1].lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "")
        if not content_type or not os.path.isfile(path):
            raise WechatPublishError("local_image_invalid", "本地上传图片不存在或格式不支持")
        with open(path, "rb") as source:
            content = source.read(MAX_IMAGE_BYTES + 1)
        if len(content) > MAX_IMAGE_BYTES:
            raise WechatPublishError("image_too_large", f"图片不能超过 {MAX_IMAGE_BYTES // 1024 // 1024}MB")
        return os.path.basename(path) or fallback_name, content_type, content
    safe_url = _validate_public_url(image_url, require_https=False)
    final_url, content_type, content = await _safe_download_bytes(safe_url)
    filename = image_url.rstrip("/").split("/")[-1].split("?")[0] or fallback_name
    if "." not in filename:
        filename = final_url.rstrip("/").split("/")[-1].split("?")[0] or fallback_name
    if "." not in filename:
        filename = fallback_name
    return filename, content_type, content


async def _safe_download_bytes(url: str, max_redirects: int = 3) -> tuple[str, str, bytes]:
    current = url
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        for _ in range(max_redirects + 1):
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise WechatPublishError("image_redirect_invalid", "图片地址重定向缺少 Location")
                    current = _validate_public_url(urljoin(current, location), require_https=False)
                    continue
                if response.status_code >= 400:
                    raise WechatPublishError("image_download_failed", f"图片下载失败（HTTP {response.status_code}）：{current}")
                content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                if content_type not in ALLOWED_IMAGE_TYPES:
                    raise WechatPublishError("image_type_not_allowed", f"仅支持 JPG/PNG/GIF/WebP 图片，当前类型：{content_type or '未知'}")
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit() and int(content_length) > MAX_IMAGE_BYTES:
                    raise WechatPublishError("image_too_large", "图片大小不能超过 5MB")
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > MAX_IMAGE_BYTES:
                        raise WechatPublishError("image_too_large", "图片大小不能超过 5MB")
                return current, content_type, content
    raise WechatPublishError("image_redirect_too_many", "图片地址重定向次数过多")


def _safe_render_api_base(api_base: str) -> str:
    raw = (api_base or DEFAULT_RENDER_API).strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.hostname:
        raise WechatPublishError("render_api_not_allowed", "排版服务地址必须是 HTTPS 域名")
    allowed_hosts = {
        item.strip().lower()
        for item in os.getenv("WECHAT_RENDER_API_ALLOWLIST", "feishu2weixin.maolai.cc").split(",")
        if item.strip()
    }
    host = parsed.hostname.lower()
    if host not in allowed_hosts:
        raise WechatPublishError("render_api_not_allowed", f"排版服务域名不在允许列表：{host}")
    _assert_public_hostname(host)
    return raw


def _validate_public_url(value: str, require_https: bool) -> str:
    parsed = urlparse((value or "").strip())
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if parsed.scheme not in allowed_schemes or not parsed.hostname:
        raise WechatPublishError("url_not_allowed", "仅支持公网 HTTP/HTTPS 图片 URL")
    _assert_public_hostname(parsed.hostname)
    return parsed.geturl()


def _assert_public_hostname(hostname: str) -> None:
    host = hostname.strip().lower().strip("[]")
    if host in {"localhost", "0.0.0.0"} or host.endswith(".localhost"):
        raise WechatPublishError("private_url_blocked", "不允许访问本机或内网地址")
    try:
        ip_addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise WechatPublishError("url_resolve_failed", "域名解析失败") from exc
        ip_addresses = [ipaddress.ip_address(info[4][0]) for info in infos]
    for ip in ip_addresses:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise WechatPublishError("private_url_blocked", "不允许访问本机、内网、链路本地或保留地址")


def sanitize_wechat_html(html_content: str) -> str:
    allowed_tags = {
        "section", "p", "span", "strong", "em", "code", "pre", "blockquote", "br", "hr",
        "h1", "h2", "h3", "h4", "ul", "ol", "li", "a", "img", "table", "thead", "tbody", "tr", "th", "td",
    }
    allowed_attrs = {
        "a": {"href", "title", "style"},
        "img": {"src", "alt", "style"},
        "section": {"style"},
        "p": {"style"},
        "span": {"style"},
        "strong": {"style"},
        "em": {"style"},
        "code": {"style"},
        "pre": {"style"},
        "blockquote": {"style"},
        "hr": {"style"},
        "h1": {"style"},
        "h2": {"style"},
        "h3": {"style"},
        "h4": {"style"},
        "ul": {"style"},
        "ol": {"style"},
        "li": {"style"},
        "table": {"style"},
        "thead": {"style"},
        "tbody": {"style"},
        "tr": {"style"},
        "th": {"style"},
        "td": {"style"},
    }
    soup = BeautifulSoup(html_content or "", "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name not in allowed_tags:
            if tag.name in {"script", "style", "iframe", "object", "embed", "link", "meta", "form", "input", "button", "textarea"}:
                tag.decompose()
            else:
                tag.unwrap()
            continue
        allowed = allowed_attrs.get(tag.name, set())
        for attr in list(tag.attrs.keys()):
            if attr.lower().startswith("on") or attr not in allowed:
                del tag.attrs[attr]
                continue
            value = tag.attrs.get(attr)
            raw_value = " ".join(value) if isinstance(value, list) else str(value)
            lowered = raw_value.strip().lower()
            if attr in {"href", "src"} and not lowered.startswith(("http://", "https://")):
                del tag.attrs[attr]
            if attr == "style" and re.search(r"expression\s*\(|javascript\s*:|@import|behavior\s*:|url\s*\(", lowered):
                del tag.attrs[attr]
    return str(soup)


def render_markdown_locally(markdown: str, style: str = "knowledge") -> str:
    theme = THEMES.get(style, THEMES["knowledge"])
    lines = (markdown or "").splitlines()
    blocks: list[str] = []
    in_code = False
    code_lines: list[str] = []

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                blocks.append(_code_block("\n".join(code_lines), theme))
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            continue
        if re.match(r"^---+$", line.strip()):
            blocks.append(f'<hr style="border:0;border-top:1px solid {theme["accent"]};margin:28px 0;"/>')
            continue
        image_match = re.match(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", line.strip())
        if image_match:
            alt = html.escape(image_match.group(1) or "文章配图")
            src = html.escape(image_match.group(2))
            blocks.append(f'<p style="margin:24px 0;text-align:center;"><img src="{src}" alt="{alt}" style="max-width:100%;border-radius:14px;display:block;margin:0 auto;"/></p>')
            continue
        if line.startswith("# "):
            blocks.append(f'<h1 style="margin:0 0 24px;color:{theme["text"]};font-size:26px;line-height:1.35;font-weight:800;text-align:left;">{_inline(line[2:].strip(), theme)}</h1>')
            continue
        if line.startswith("## "):
            blocks.append(f'<h2 style="margin:32px 0 16px;padding:10px 14px;border-left:5px solid {theme["primary"]};background:{theme["accent"]};color:{theme["text"]};font-size:20px;line-height:1.45;font-weight:800;">{_inline(line[3:].strip(), theme)}</h2>')
            continue
        if line.startswith("### "):
            blocks.append(f'<h3 style="margin:26px 0 12px;color:{theme["primary"]};font-size:17px;line-height:1.6;font-weight:800;">{_inline(line[4:].strip(), theme)}</h3>')
            continue
        if line.startswith(">"):
            text = line.lstrip("> ")
            blocks.append(f'<blockquote style="margin:18px 0;padding:14px 16px;border-left:4px solid {theme["primary"]};background:{theme["quote"]};color:{theme["text"]};border-radius:12px;line-height:1.8;">{_inline(text, theme)}</blockquote>')
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            text = re.sub(r"^\s*[-*+]\s+", "", line)
            blocks.append(f'<p style="margin:10px 0;color:{theme["text"]};font-size:16px;line-height:1.85;">• {_inline(text, theme)}</p>')
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            text = re.sub(r"^\s*\d+\.\s+", "", line)
            number = re.match(r"^\s*(\d+)\.", line).group(1)  # type: ignore[union-attr]
            blocks.append(f'<p style="margin:10px 0;color:{theme["text"]};font-size:16px;line-height:1.85;"><strong style="color:{theme["primary"]};">{number}.</strong> {_inline(text, theme)}</p>')
            continue
        blocks.append(f'<p style="margin:16px 0;color:{theme["text"]};font-size:16px;line-height:1.9;letter-spacing:0.02em;">{_inline(line.strip(), theme)}</p>')

    if code_lines:
        blocks.append(_code_block("\n".join(code_lines), theme))
    body = "\n".join(blocks)
    return f'<section style="max-width:677px;margin:0 auto;padding:8px 4px;background:{theme["surface"]};font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">{body}</section>'


def _inline(text: str, theme: dict[str, str]) -> str:
    value = html.escape(text)
    value = re.sub(r"`([^`]+)`", rf'<code style="padding:2px 5px;border-radius:5px;background:{theme["accent"]};color:{theme["primary"]};font-size:90%;">\1</code>', value)
    value = re.sub(r"\*\*([^*]+)\*\*", rf'<strong style="color:{theme["primary"]};font-weight:800;">\1</strong>', value)
    value = re.sub(r"==([^=]+)==", rf'<strong style="padding:0 4px;background:{theme["accent"]};color:{theme["primary"]};font-weight:800;">\1</strong>', value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", rf'<a href="\2" style="color:{theme["primary"]};text-decoration:none;">\1</a>', value)
    return value


def _code_block(code: str, theme: dict[str, str]) -> str:
    return f'<pre style="margin:18px 0;padding:14px;border-radius:12px;background:#0f172a;color:#e2e8f0;white-space:pre-wrap;line-height:1.7;font-size:13px;overflow:auto;"><code>{html.escape(code)}</code></pre>'


def _wechat_error(prefix: str, data: dict[str, Any]) -> WechatPublishError:
    code = str(data.get("errcode") or "unknown")
    raw_message = data.get("errmsg") or json.dumps(data, ensure_ascii=False)
    message = explain_wechat_error(code, raw_message)
    if code == "40164":
        ip_match = re.search(r"invalid ip\s+([\d.]+)", raw_message, re.I)
        ip = ip_match.group(1) if ip_match else "见微信错误信息"
        message = f"当前服务器 IP 未加入公众号 API 白名单。微信识别 IP：{ip}。请到公众号后台基础配置中添加后重试。原始错误：{data.get('errmsg', '')}"
    return WechatPublishError(f"{prefix}_{code}", message, data)
