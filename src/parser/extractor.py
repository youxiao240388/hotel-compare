"""
LLM 数据解析器 - 利用大模型从非结构化页面内容中提取标准化房型信息

设计依据（文档第四章）：
- 将页面HTML/文本发送给LLM，以JSON格式返回结构化数据
- Prompt 工程：要求LLM扮演酒店数据分析师角色
"""
import json
import logging
import re
from typing import List

import httpx

from config.settings import LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from src.platforms.base import RoomInfo

logger = logging.getLogger(__name__)

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
    """LLM 驱动的数据解析器"""

    def __init__(self):
        self._api_key = self._detect_api_key()
        self._base_url = self._detect_base_url()
        self._model = self._detect_model()
        self.client = httpx.Client(timeout=httpx.Timeout(60.0))

    def _detect_base_url(self) -> str:
        """检测 API Base URL，优先级：环境变量 > DeepSeek官方 > SiliconFlow备用 > settings"""
        import os, yaml
        from pathlib import Path

        # 1. 环境变量
        for var in ["LLM_BASE_URL", "OPENAI_BASE_URL"]:
            val = os.getenv(var, "")
            if val:
                return val

        # 2. Hermes config
        hermes_config = Path.home() / ".hermes" / "config.yaml"
        if hermes_config.exists():
            try:
                with open(hermes_config) as f:
                    config = yaml.safe_load(f)
                # 优先 DeepSeek 官方
                mc = config.get("model", {})
                if mc.get("provider") == "deepseek":
                    url = mc.get("base_url", "")
                    key = mc.get("api_key", "")
                    if url and key:
                        return url
                # 备用: custom_providers (SiliconFlow)
                for cp in config.get("custom_providers", []):
                    url = cp.get("base_url", "")
                    key = cp.get("api_key", "")
                    if url and key:
                        return url
            except Exception:
                pass

        if LLM_BASE_URL:
            return LLM_BASE_URL

        return "https://api.deepseek.com"

    def _detect_model(self) -> str:
        """检测模型名称"""
        import os, yaml
        from pathlib import Path

        for var in ["LLM_MODEL", "OPENAI_MODEL"]:
            val = os.getenv(var, "")
            if val:
                return val

        hermes_config = Path.home() / ".hermes" / "config.yaml"
        if hermes_config.exists():
            try:
                with open(hermes_config) as f:
                    config = yaml.safe_load(f)
                # 优先 DeepSeek 官方
                mc = config.get("model", {})
                if mc.get("provider") == "deepseek":
                    model = mc.get("default", "")
                    if model:
                        return model
                for cp in config.get("custom_providers", []):
                    model = cp.get("model", "")
                    if model:
                        return model
            except Exception:
                pass

        if LLM_MODEL:
            return LLM_MODEL

        return "deepseek-chat"

    def _detect_api_key(self) -> str:
        """尝试从环境变量或 Hermes 配置文件自动检测 API Key"""
        import os
        import yaml
        from pathlib import Path

        # 1. 环境变量
        for key in ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"]:
            val = os.getenv(key, "")
            if val:
                return val

        # 2. Hermes config.yaml（优先 DeepSeek 官方 → SiliconFlow 备用）
        hermes_config = Path.home() / ".hermes" / "config.yaml"
        if hermes_config.exists():
            try:
                with open(hermes_config) as f:
                    config = yaml.safe_load(f)
                # 优先: 顶层 model 配置 (DeepSeek 官方)
                mc = config.get("model", {})
                if mc.get("provider") == "deepseek":
                    api_key = mc.get("api_key", "")
                    if api_key:
                        return api_key
                # 备用: custom_providers (SiliconFlow)
                for cp in config.get("custom_providers", []):
                    api_key = cp.get("api_key", "")
                    if api_key:
                        return api_key
            except Exception as e:
                logger.debug(f"读取 Hermes 配置失败: {e}")

        return ""

    def extract_rooms(
        self,
        page_content: str,
        platform: str,
        truncate_chars: int = 8000,
    ) -> List[RoomInfo]:
        """
        从页面内容中提取房型信息

        Args:
            page_content: 页面文本或HTML片段
            platform: 平台名称
            truncate_chars: 截断长度（控制 token 消耗）

        Returns:
            标准化房型列表
        """
        if not page_content.strip():
            return []

        # 截断以控制 token
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
        """调用 LLM API（通过 curl 子进程，绕过 httpx chunked-encoding 超时问题）"""
        import subprocess

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

        headers = [
            "-H", "Content-Type: application/json",
        ]
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
        """解析 LLM 返回的 JSON"""
        # 提取 JSON 数组
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
        """尝试修复损坏的 JSON"""
        # 简单修复：去掉尾部多余逗号
        fixed = re.sub(r",\s*]", "]", bad_json)
        fixed = re.sub(r",\s*}", "}", fixed)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return []
