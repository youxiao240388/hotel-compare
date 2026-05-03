"""
LLM 数据解析器 - 支持多厂商智能体，用户可自行选择

支持的厂商预设（一键切换）：
  deepseek    → DeepSeek 官方 (deepseek-chat)
  openai      → OpenAI (gpt-4o-mini)
  siliconflow → SiliconFlow (deepseek-ai/DeepSeek-V3)
  openrouter  → OpenRouter (openai/gpt-4o-mini)
  zhipu       → 智谱 GLM (glm-4-flash)
  custom      → 自定义 OpenAI 兼容端点

环境变量覆盖（优先级最高）：
  HOTEL_LLM_PROVIDER / HOTEL_LLM_MODEL / HOTEL_LLM_API_KEY / HOTEL_LLM_BASE_URL
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional

import httpx

from src.platforms.base import RoomInfo

logger = logging.getLogger(__name__)

# ── 厂商预设 ──────────────────────────────────────────────
PROVIDER_PRESETS = {
    "deepseek": {
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "desc": "DeepSeek 官方",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "desc": "OpenAI",
    },
    "siliconflow": {
        "model": "deepseek-ai/DeepSeek-V3",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "desc": "SiliconFlow（国产模型聚合）",
    },
    "openrouter": {
        "model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "desc": "OpenRouter（全球模型聚合）",
    },
    "zhipu": {
        "model": "glm-4-flash",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        "desc": "智谱 GLM",
    },
    "custom": {
        "model": "",
        "base_url": "",
        "api_key_env": "HOTEL_LLM_API_KEY",
        "desc": "自定义 OpenAI 兼容端点",
    },
}


def list_providers() -> dict:
    """列出所有可用厂商"""
    return {
        k: {"model": v["model"], "desc": v["desc"], "key_env": v["api_key_env"]}
        for k, v in PROVIDER_PRESETS.items()
    }


def resolve_llm_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> dict:
    """
    解析 LLM 配置，优先级：
    1. 显式传入参数
    2. HOTEL_LLM_* 环境变量
    3. 厂商预设
    4. Hermes config.yaml 兜底
    """

    # ── 确定 provider ──
    p = provider or os.getenv("HOTEL_LLM_PROVIDER", "") or os.getenv("LLM_PROVIDER", "")
    if not p:
        # 从 config.yaml 推断
        p = _guess_provider_from_hermes()

    preset = PROVIDER_PRESETS.get(p, {})

    # ── base_url ──
    url = (
        base_url
        or os.getenv("HOTEL_LLM_BASE_URL", "")
        or os.getenv("LLM_BASE_URL", "")
        or preset.get("base_url", "")
        or _detect_base_url_from_hermes()
        or "https://api.deepseek.com"
    )

    # ── model ──
    m = (
        model
        or os.getenv("HOTEL_LLM_MODEL", "")
        or os.getenv("LLM_MODEL", "")
        or preset.get("model", "")
        or _detect_model_from_hermes()
        or "deepseek-chat"
    )

    # ── api_key ──
    key = (
        api_key
        or os.getenv("HOTEL_LLM_API_KEY", "")
        or os.getenv(preset.get("api_key_env", ""), "")
        or _detect_api_key_from_hermes()
        or ""
    )

    return {
        "provider": p or "deepseek",
        "model": m,
        "base_url": url,
        "api_key": key,
    }


def _guess_provider_from_hermes() -> str:
    """从 Hermes config.yaml 推断当前使用的 provider"""
    try:
        import yaml
        hermes = Path.home() / ".hermes" / "config.yaml"
        if hermes.exists():
            with open(hermes) as f:
                config = yaml.safe_load(f)
            mc = config.get("model", {})
            provider = mc.get("provider", "")
            if provider == "deepseek":
                return "deepseek"
            if provider == "openai":
                return "openai"
            if provider == "openrouter":
                return "openrouter"
    except Exception:
        pass
    return ""


def _detect_base_url_from_hermes() -> str:
    try:
        import yaml
        hermes = Path.home() / ".hermes" / "config.yaml"
        if hermes.exists():
            with open(hermes) as f:
                config = yaml.safe_load(f)
            mc = config.get("model", {})
            url = mc.get("base_url", "")
            if url:
                return url
            for cp in config.get("custom_providers", []):
                url = cp.get("base_url", "")
                if url:
                    return url
    except Exception:
        pass
    return ""


def _detect_model_from_hermes() -> str:
    try:
        import yaml
        hermes = Path.home() / ".hermes" / "config.yaml"
        if hermes.exists():
            with open(hermes) as f:
                config = yaml.safe_load(f)
            mc = config.get("model", {})
            model = mc.get("default", "")
            if model:
                return model
            for cp in config.get("custom_providers", []):
                model = cp.get("model", "")
                if model:
                    return model
    except Exception:
        pass
    return ""


def _detect_api_key_from_hermes() -> str:
    try:
        import yaml
        hermes = Path.home() / ".hermes" / "config.yaml"
        if hermes.exists():
            with open(hermes) as f:
                config = yaml.safe_load(f)
            mc = config.get("model", {})
            key = mc.get("api_key", "")
            if key:
                return key
            for cp in config.get("custom_providers", []):
                key = cp.get("api_key", "")
                if key:
                    return key
    except Exception:
        pass
    return ""


EXTRACTION_PROMPT = """你是一个专业的酒店数据分析师。请从以下酒店页面内容中，提取所有房型的关键信息。

要求：
1. 返回严格合法的JSON数组，每个元素包含：
   - room_name: 房型名称（保留原名）
   - price: 当前价格（数字，单位：元）
   - original_price: 划线原价（数字，若无则为0）
   - includes_breakfast: 是否含早（true/false）
   - cancellation: 取消政策简述
   - bed_type: 床型（如"大床1.8m"、"双床1.2m×2"）
   - room_area: 面积（如"28㎡"）
   - stock_info: 库存信息（如"仅剩2间"，无则为空字符串）

2. 如果页面内容中没有房价信息，返回空数组 []

页面内容：
{page_content}

只返回JSON，不要任何解释。"""


class LLMParser:
    """多厂商 LLM 驱动的数据解析器"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        cfg = resolve_llm_config(provider, model, api_key, base_url)
        self._provider = cfg["provider"]
        self._model = cfg["model"]
        self._api_key = cfg["api_key"]
        self._base_url = cfg["base_url"]
        self.client = httpx.Client(timeout=httpx.Timeout(60.0))

        logger.info(
            f"LLM 解析器: provider={self._provider}, model={self._model}"
        )

    @property
    def config(self) -> dict:
        """返回当前配置（供 CLI --list-providers 查看）"""
        return {
            "provider": self._provider,
            "model": self._model,
            "base_url": self._base_url,
            "has_key": bool(self._api_key),
        }

    def extract_rooms(
        self,
        page_content: str,
        platform: str,
        truncate_chars: int = 8000,
    ) -> List[RoomInfo]:
        if not page_content.strip():
            return []

        content = page_content[:truncate_chars]

        try:
            raw_json = self._call_llm(content)
            rooms = self._parse_response(raw_json, platform)
            logger.info(f"LLM 从 {platform} 解析出 {len(rooms)} 个房型")
            return rooms
        except Exception as e:
            logger.error(f"LLM 解析失败: {e}")
            return []

    def _call_llm(self, page_content: str) -> str:
        prompt = EXTRACTION_PROMPT.format(page_content=page_content)

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": "你是一个酒店数据提取工具，始终返回合法JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        })

        headers = ["-H", "Content-Type: application/json"]
        if self._api_key:
            headers += ["-H", f"Authorization: Bearer {self._api_key}"]

        cmd = [
            "curl", "-s", "--max-time", "50",
            f"{self._base_url}/chat/completions",
        ] + headers + ["-d", payload]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(f"curl failed (code {result.returncode}): {result.stderr[:200]}")

        data = json.loads(result.stdout)

        if "error" in data:
            raise RuntimeError(f"API error: {data['error']}")

        return data["choices"][0]["message"]["content"]

    def _parse_response(self, raw: str, platform: str) -> List[RoomInfo]:
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not json_match:
            logger.warning("LLM 返回内容中未找到 JSON 数组")
            return []

        try:
            items = json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("JSON 解析失败，尝试修复...")
            items = self._repair_json(json_match.group())

        rooms = []
        for item in items:
            try:
                rooms.append(RoomInfo(
                    platform=platform,
                    room_name=item.get("room_name", "未知房型"),
                    price=float(item.get("price", 0)),
                    original_price=float(item.get("original_price", 0)),
                    includes_breakfast=item.get("includes_breakfast", False),
                    cancellation=item.get("cancellation", ""),
                    bed_type=item.get("bed_type", ""),
                    room_area=item.get("room_area", ""),
                    stock_info=item.get("stock_info", ""),
                    raw_data=item,
                ))
            except (ValueError, TypeError) as e:
                logger.debug(f"跳过无效房型: {e}")
                continue

        return rooms

    def _repair_json(self, bad_json: str) -> list:
        fixed = re.sub(r",\s*]", "]", bad_json)
        fixed = re.sub(r",\s*}", "}", fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return []
