"""AIService - OpenAI-compatible AI provider adapter.

Provider settings are read from environment variables. Do not hardcode API keys
in this module.
"""

import os
import json
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


# ─── Default model constants ──────────────────────────────────
MODEL_PRIMARY = "moonshotai/kimi-k2.6"
MODEL_STANDARD = "minimaxai/minimax-m2.7"
MODEL_FAST = "meta/llama-3.3-70b-instruct"
MODEL_IMAGE = MODEL_PRIMARY
MODEL_VIDEO = MODEL_PRIMARY
DEFAULT_MODEL = MODEL_PRIMARY

# 智能降级链，可通过 AI_PRIMARY_MODELS 覆盖，多个模型用逗号分隔。
FALLBACK_CHAIN = [MODEL_PRIMARY, MODEL_STANDARD, MODEL_FAST]

MAX_RETRIES_PER_MODEL = 2
FIRST_TOKEN_TIMEOUT = 30


class AIProviderError(RuntimeError):
    """Raised when the configured AI provider cannot serve a request."""

    def __init__(self, message: str, *, provider: str = "primary", status_code: int | None = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


def _split_models(raw: str | None, fallback: list[str]) -> list[str]:
    models = [item.strip() for item in (raw or "").split(",") if item.strip()]
    return models or fallback


def _redact_provider_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        detail = exc.response.text[:240].replace("\n", " ")
        return f"HTTP {status}: {detail}"
    if isinstance(exc, AIProviderError):
        return str(exc)
    return f"{type(exc).__name__}: {exc}"


@dataclass
class AIResponse:
    """对服务商原始响应的统一封装"""
    content: str = ""
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    raw_response: dict = field(default_factory=dict)
    images: List[str] = field(default_factory=list)
    annotations: dict = field(default_factory=dict)


class AIService:
    """AI 统一调度服务（OpenAI-compatible API）

    用法示例:
        ai = AIService(module_code="ip_system")
        response = await ai.chat(messages, prompt_name="generate_script")
    """

    def __init__(self, module_code: str = "ip_system", db_session=None):
        self.module_code = module_code
        self.db_session = db_session

        self.primary_provider = os.getenv("AI_PRIMARY_PROVIDER", "primary")
        self.primary_api_key = os.getenv("AI_PRIMARY_API_KEY", "")
        self.primary_base_url = os.getenv("AI_PRIMARY_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.primary_models = _split_models(os.getenv("AI_PRIMARY_MODELS") or os.getenv("AI_PRIMARY_MODEL"), FALLBACK_CHAIN)

        self.fallback_provider = os.getenv("AI_FALLBACK_PROVIDER", "fallback")
        self.fallback_api_key = os.getenv("AI_FALLBACK_API_KEY", "")
        self.fallback_base_url = os.getenv("AI_FALLBACK_BASE_URL", "").rstrip("/")
        self.fallback_models = _split_models(os.getenv("AI_FALLBACK_MODELS") or os.getenv("AI_FALLBACK_MODEL"), [])

    def _provider_specs(self) -> list[dict]:
        specs = []
        if self.primary_api_key and self.primary_base_url:
            specs.append({
                "name": self.primary_provider,
                "api_key": self.primary_api_key,
                "base_url": self.primary_base_url,
                "models": self.primary_models,
            })
        if self.fallback_api_key and self.fallback_base_url and self.fallback_models:
            specs.append({
                "name": self.fallback_provider,
                "api_key": self.fallback_api_key,
                "base_url": self.fallback_base_url,
                "models": self.fallback_models,
            })
        return specs

    async def chat(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
        prompt_name: str = "default",
        auto_fallback: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """非流式 AI 对话，支持 provider/model fallback。"""

        provider_specs = self._provider_specs()
        if not provider_specs:
            raise AIProviderError("AI provider is not configured. Set AI_PRIMARY_API_KEY and AI_PRIMARY_BASE_URL.")

        last_error = None
        for spec in provider_specs:
            chain = spec["models"] if auto_fallback else [model]
            if model != DEFAULT_MODEL and model not in chain:
                chain = [model, *chain]
            chain = list(dict.fromkeys(chain))

            for m in chain:
                for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                    try:
                        resp = await self._call_provider(
                            base_url=spec["base_url"],
                            api_key=spec["api_key"],
                            model=m,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            provider_name=spec["name"],
                        )
                        logger.info("[%s] %s %s 调用成功", self.module_code, spec["name"], m)
                        return resp
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            "[%s] %s %s 第%s次失败: %s",
                            self.module_code,
                            spec["name"],
                            m,
                            attempt,
                            _redact_provider_error(e),
                        )
                logger.warning("[%s] %s %s 失败%s次，降级到下一个模型", self.module_code, spec["name"], m, MAX_RETRIES_PER_MODEL)

        status_code = last_error.response.status_code if isinstance(last_error, httpx.HTTPStatusError) else None
        raise AIProviderError(f"All AI providers/models are unavailable: {_redact_provider_error(last_error)}", status_code=status_code)

    async def chat_stream(
        self,
        messages: list,
        model: str = DEFAULT_MODEL,
        prompt_name: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """流式 AI 对话（支持 provider/model fallback + 首字超时检测）"""

        provider_specs = self._provider_specs()
        if not provider_specs:
            yield "\n\n[错误] AI 服务未配置，请设置 AI_PRIMARY_API_KEY 和 AI_PRIMARY_BASE_URL。"
            return

        for spec in provider_specs:
            chain = spec["models"]
            if model != DEFAULT_MODEL and model not in chain:
                chain = [model, *chain]
            chain = list(dict.fromkeys(chain))

            for m in chain:
                try:
                    async for chunk in self._stream_provider(
                        base_url=spec["base_url"],
                        api_key=spec["api_key"],
                        model=m,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        provider_name=spec["name"],
                    ):
                        yield chunk
                    return
                except Exception as e:
                    logger.warning("[%s] %s %s 流式失败: %s", self.module_code, spec["name"], m, _redact_provider_error(e))

        yield "\n\n[错误] 所有 AI 服务商均不可用，请检查配置。"

    async def _call_provider(
        self, base_url: str, api_key: str, model: str,
        messages: list, temperature: float, max_tokens: int,
        provider_name: str,
    ) -> AIResponse:
        """执行单次非流式请求"""
        start_time = time.time()
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = int((time.time() - start_time) * 1000)
        usage = data.get("usage", {})

        return AIResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", model),
            provider=provider_name,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0),
            cost=usage.get("total_cost", 0.0),
            latency_ms=latency,
            raw_response=data,
        )

    async def _stream_provider(
        self, base_url: str, api_key: str, model: str,
        messages: list, temperature: float, max_tokens: int,
        provider_name: str,
    ) -> AsyncGenerator[str, None]:
        """执行单次流式请求，含首字超时检测"""
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                first_token_received = False
                start_time = time.time()

                async for line in resp.aiter_lines():
                    if not first_token_received:
                        if time.time() - start_time > FIRST_TOKEN_TIMEOUT:
                            raise TimeoutError(f"首字超时 ({FIRST_TOKEN_TIMEOUT}s)")

                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            first_token_received = True
                            yield content
                    except json.JSONDecodeError:
                        continue


def parse_ai_json_response(content: str) -> tuple:
    """公共 AI JSON 响应解析函数（与 SCRM 规范一致）

    处理能力：thinking 标签、JSON 代码块、混合文本、纯 JSON。
    返回: (result_dict, thinking_str)
    """
    thinking = ""
    clean = content

    # 提取 thinking 标签
    import re
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL)
    if thinking_match:
        thinking = thinking_match.group(1).strip()
        clean = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL).strip()

    # 尝试提取 JSON 代码块
    json_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
    if json_block:
        return json.loads(json_block.group(1)), thinking

    # 尝试直接解析
    json_match = re.search(r"\{.*\}", clean, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0)), thinking

    raise json.JSONDecodeError("无法从 AI 响应中提取 JSON", content, 0)


def safe_parse_ai_json(content: str, default: dict = None) -> tuple:
    """安全版本的 JSON 解析（不抛异常）"""
    try:
        return parse_ai_json_response(content)
    except (json.JSONDecodeError, Exception):
        return default or {}, ""
