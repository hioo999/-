"""内容解析服务

负责将各种输入源（URL链接、上传文件、纯文本）转化为统一的纯文本内容。
"""

import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NOISE_LINES = {
    "百度一下，你就知道",
    "打开APP",
    "APP内打开",
    "打开今日头条查看图片详情",
    "头条听资讯，时事尽掌握",
    "去听全文",
    "听全文约11分钟",
    "关注",
    "点击查看完整内容",
    "相关推荐",
    "打开今日头条查看全部",
    "去今日头条看专享资讯",
    "加载中...",
    "分享",
    "收藏",
    "暂无评论",
    "登录",
    "首页",
    "发布于",
    "赞同",
    "添加评论",
    "写回答",
    "收起",
    "展开阅读全文",
    "阅读原文",
    "继续阅读",
}

ERROR_PAGE_MARKERS = {
    "百度安全验证",
    "网络不给力，请稍后重试",
    "返回首页",
    "问题反馈",
    "验证码",
    "安全验证",
    "访问过于频繁",
    "请稍后重试",
    "页面不存在",
    "内容不存在",
    "该内容已被删除",
    "请在APP内打开",
    "请在 APP 内打开",
    "登录后查看",
    "您当前请求存在异常",
    "暂时限制本次访问",
    "请求存在异常",
}

PLATFORM_RENDER_DOMAINS = (
    "toutiao.com",
    "m.toutiao.com",
    "baijiahao.baidu.com",
    "mbd.baidu.com",
    "wappass.baidu.com",
    "zhihu.com",
    "zhuanlan.zhihu.com",
)

STATIC_SELECTORS = [
    ("微信公众号", ["#js_content", ".rich_media_content"]),
    ("知乎", [".Post-RichTextContainer", ".RichText", ".QuestionAnswer-content", ".AnswerItem"]),
    ("百家号", ["#content", ".article-content", "[class*=article-content]"]),
    ("头条", ["article", "[class*=article-content]", "[class*=content]"]),
    ("CSDN", ["#content_views", ".blog-content-box", "article"]),
    ("掘金", [".article-content", "article", ".markdown-body"]),
    ("简书", ["article", "._2rhmJa", ".show-content"]),
    ("通用", ["article", "main", "[class*=article]", "[class*=content]", "[class*=post]", "[class*=detail]"]),
]


async def extract_from_url(url: str) -> str:
    """从 URL 抓取并提取网页正文内容

    支持：微信公众号文章、小红书、知乎、一般博客等。
    使用 BeautifulSoup 去除 HTML 标签、脚本、样式，提取正文。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as e:
        if _should_render_url(url):
            rendered = await _extract_with_browser(url)
            if _is_text_usable(rendered):
                return rendered
            if _looks_like_error_page(rendered):
                raise ValueError("该链接返回了登录/验证/反爬限制页面，无法自动提取正文。请复制正文后使用文本模式粘贴。")
        logger.error(f"URL 抓取失败: {url}, 错误: {e}")
        raise ValueError(f"无法访问该链接: {e}")

    text = _extract_text_from_html(html)
    if _is_text_usable(text):
        return text

    if _should_render_with_browser(url, html):
        rendered = await _extract_with_browser(url)
        if _is_text_usable(rendered):
            return rendered

    if _looks_like_error_page(text):
        raise ValueError("该链接返回了登录/验证/反爬限制页面，无法自动提取正文。请复制正文后使用文本模式粘贴。")

    return text


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # 移除脚本、样式、导航等无关元素
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe"]):
        tag.decompose()

    selector_text = _extract_by_selectors(soup)
    if selector_text:
        return selector_text

    readability_text = _extract_with_trafilatura(html)
    if readability_text:
        return readability_text

    # 回退：提取 body 全文
    body = soup.find("body")
    if body:
        return _clean_text(body.get_text())

    return _clean_text(soup.get_text())


def _is_text_usable(text: str) -> bool:
    cleaned = (text or "").strip()
    return len(cleaned) >= 80 and not _looks_like_error_page(cleaned)


def _looks_like_error_page(text: str) -> bool:
    compact = "".join((text or "").split())
    if any("".join(marker.split()) in compact for marker in ERROR_PAGE_MARKERS):
        return True
    marker_count = sum(1 for marker in ERROR_PAGE_MARKERS if marker in text)
    return marker_count >= 3 and len(text) < 500


def _should_render_with_browser(url: str, html: str) -> bool:
    if _should_render_url(url):
        return True
    body_empty = "<body></body>" in html[:300].replace(" ", "").lower()
    return body_empty and len(html) > 1000


def _should_render_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in PLATFORM_RENDER_DOMAINS)


async def _extract_with_browser(url: str) -> str:
    """Render JS-heavy article pages and extract visible text.

    Toutiao share pages often return an empty body plus a JSVM script to plain
    HTTP clients. Playwright rendering lets the redirected mobile page expose
    the article body.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        logger.warning("Playwright 不可用，无法渲染页面: %s", exc)
        return ""

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                    "Mobile/15E148 Safari/604.1"
                ),
                viewport={"width": 390, "height": 844},
                is_mobile=True,
            )
            await page.goto(url, wait_until="networkidle", timeout=60000)
            text = await _extract_rendered_text(page, url)
            await browser.close()
            return _clean_text(text)
    except Exception as exc:
        logger.warning("浏览器渲染提取失败: %s", exc)
        return ""


async def _extract_rendered_text(page, url: str) -> str:
    host = urlparse(url).netloc.lower()
    selectors: list[str]
    if "toutiao.com" in host:
        selectors = ["article", "[class*=article-content]", "[class*=content]"]
    elif "baijiahao.baidu.com" in host or "mbd.baidu.com" in host:
        selectors = ["#content", "[class*=article-content]", "[class*=content]"]
    elif "zhihu.com" in host:
        selectors = [".Post-RichTextContainer", ".RichText", ".QuestionAnswer-content", ".AnswerItem", "article", "main"]
    else:
        selectors = ["article", "main", "[class*=article]", "[class*=content]", "body"]

    best_text = ""
    for selector in selectors:
        try:
            loc = page.locator(selector)
            count = min(await loc.count(), 8)
            for idx in range(count):
                text = await loc.nth(idx).inner_text(timeout=3000)
                text = _clean_text(text)
                if len(text) > len(best_text):
                    best_text = text
        except Exception:
            continue
    return best_text or await page.locator("body").inner_text(timeout=10000)


def _extract_by_selectors(soup: BeautifulSoup) -> str:
    best_text = ""
    for _, selectors in STATIC_SELECTORS:
        for selector in selectors:
            try:
                for node in soup.select(selector)[:10]:
                    text = _clean_text(node.get_text("\n"))
                    if len(text) > len(best_text):
                        best_text = text
            except Exception:
                continue
    return best_text


def _extract_with_trafilatura(html: str) -> str:
    try:
        import trafilatura
    except Exception:
        return ""
    try:
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
        )
        return _clean_text(text or "")
    except Exception as exc:
        logger.debug("trafilatura 正文抽取失败: %s", exc)
        return ""


def extract_from_text(raw_text: str) -> str:
    """对纯文本做基础清理"""
    return _clean_text(raw_text)


async def extract_from_file(file_content: bytes, filename: str) -> str:
    """从上传文件中提取文本内容

    支持格式：
    - .txt：直接 UTF-8 解码
    - .pdf：使用 PyPDF2 提取
    - .docx：使用 python-docx 提取
    - .md：直接 UTF-8 解码
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("txt", "md"):
        return _clean_text(file_content.decode("utf-8", errors="ignore"))

    elif ext == "pdf":
        return _extract_pdf(file_content)

    elif ext == "docx":
        return _extract_docx(file_content)

    else:
        # 尝试作为纯文本处理
        try:
            return _clean_text(file_content.decode("utf-8", errors="ignore"))
        except Exception:
            raise ValueError(f"不支持的文件格式: .{ext}。目前支持 txt, md, pdf, docx")


def _extract_pdf(content: bytes) -> str:
    """从 PDF 提取文本"""
    import io
    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(content))
    texts = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texts.append(page_text)

    if not texts:
        raise ValueError("PDF 中未提取到任何文本内容，可能是扫描件（建议使用 OCR）。")
    return _clean_text("\n".join(texts))


def _extract_docx(content: bytes) -> str:
    """从 Word 文档提取文本"""
    import io
    from docx import Document

    doc = Document(io.BytesIO(content))
    texts = [p.text for p in doc.paragraphs if p.text.strip()]

    if not texts:
        raise ValueError("Word 文档中未提取到任何文本内容。")
    return _clean_text("\n".join(texts))


def _clean_text(text: str) -> str:
    """统一文本清洗"""
    import re

    # 合并多余空白行
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除每行首尾空白
    lines = [line.strip() for line in text.split("\n")]
    # 去除空行
    text = "\n".join(line for line in lines if line and not _is_noise_line(line))
    return text.strip()


def _is_noise_line(line: str) -> bool:
    compact = "".join(line.split())
    if compact in NOISE_LINES:
        return True
    if any(marker in compact for marker in ("打开APP查看", "去APP内查看", "客户端下载")):
        return True
    if compact.startswith("——©"):
        return True
    if compact.startswith("评论") and len(compact) <= 8:
        return True
    if compact.startswith("去今日头条看"):
        return True
    return False
