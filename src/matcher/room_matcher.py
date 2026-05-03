"""
房型匹配引擎 - 基于向量相似度的跨平台房型对齐

文档第四章：利用 Embedding 模型将房型名称转化为向量，
计算余弦相似度，超过阈值判定为同一房型。

实现：
- 使用 sentence-transformers 生成 embedding
- ChromaDB 存储历史映射关系
- 低置信度匹配记录日志供人工审核
"""
import logging
from typing import List, Dict, Tuple, Optional

import numpy as np

from config.settings import (
    ROOM_SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    CHROMA_PERSIST_DIR,
)
from src.platforms.base import RoomInfo

logger = logging.getLogger(__name__)


class RoomMatcher:
    """房型向量匹配器 - 基于字符 n-gram 的中文文本相似度"""

    def __init__(self):
        self._model = "ngram"  # ngram 模式，轻量零依赖

    @property
    def model(self):
        return self._model

    def embed(self, text: str) -> str:
        """轻量模式直接返回文本本身（相似度计算在 cosine_similarity 中处理）"""
        return text

    def cosine_similarity(self, a: str, b: str) -> float:
        """
        中文房型名称相似度计算
        使用 2-gram + 3-gram Jaccard 相似度，对房型名称匹配效果好
        """
        if not a or not b:
            return 0.0

        # 提取 2-gram 和 3-gram
        def ngrams(s, n):
            return {s[i:i+n] for i in range(len(s) - n + 1)}

        a_ngrams = ngrams(a, 2) | ngrams(a, 3)
        b_ngrams = ngrams(b, 2) | ngrams(b, 3)

        if not a_ngrams or not b_ngrams:
            return 0.0

        # Jaccard 相似度
        intersection = a_ngrams & b_ngrams
        union = a_ngrams | b_ngrams
        jaccard = len(intersection) / len(union) if union else 0.0

        # 加权：字符级重合加分
        char_overlap = len(set(a) & set(b)) / max(len(set(a)), len(set(b)), 1)

        # 综合得分：Jaccard 70% + 字符重合 30%
        return 0.7 * jaccard + 0.3 * char_overlap

    def match_rooms(
        self,
        rooms_by_platform: Dict[str, List[RoomInfo]],
        threshold: float = None,
    ) -> List[Dict]:
        """
        跨平台房型匹配

        算法：
        1. 取第一个平台的所有房型作为基准
        2. 对每个基准房型，与其他平台的房型计算相似度
        3. 超过阈值则视为同一房型
        4. 返回匹配组，每组包含各平台对应房型及价格

        Returns:
            [
                {
                    "room_name": "豪华大床房",
                    "confidence": 0.95,
                    "prices": {"ctrip": 388, "meituan": 368, "fliggy": 399},
                    "details": {"ctrip": RoomInfo, ...}
                },
                ...
            ]
        """
        threshold = threshold or ROOM_SIMILARITY_THRESHOLD
        platforms = list(rooms_by_platform.keys())

        if not platforms:
            return []

        # 以第一个平台为基准
        base_platform = platforms[0]
        base_rooms = rooms_by_platform[base_platform]

        matched_groups = []

        for base_room in base_rooms:
            base_vec = self.embed(base_room.room_name)
            group = {
                "room_name": base_room.room_name,
                "confidence": 1.0,
                "prices": {base_platform: base_room.price},
                "details": {base_platform: base_room},
                "match_quality": "exact",
            }

            # 与其他平台比对
            for platform in platforms[1:]:
                other_rooms = rooms_by_platform.get(platform, [])
                best_match = None
                best_score = 0.0

                for other_room in other_rooms:
                    other_vec = self.embed(other_room.room_name)
                    score = self.cosine_similarity(base_vec, other_vec)

                    if score > best_score:
                        best_score = score
                        best_match = other_room

                if best_match and best_score >= threshold:
                    group["prices"][platform] = best_match.price
                    group["details"][platform] = best_match
                    group["confidence"] = min(group["confidence"], best_score)

                    if best_score < 0.95:
                        group["match_quality"] = "high"
                    if best_score < threshold + 0.05:
                        group["match_quality"] = "medium"
                        logger.info(
                            f"低置信度匹配: '{base_room.room_name}' ↔ "
                            f"'{best_match.room_name}' ({best_score:.3f})"
                        )

            matched_groups.append(group)

        # 按最低价格排序
        matched_groups.sort(key=lambda g: min(g["prices"].values()))

        return matched_groups

    def find_cheapest_per_room(self, matched_groups: List[Dict]) -> List[Dict]:
        """找出每个房型组的最便宜平台"""
        results = []
        for group in matched_groups:
            prices = group["prices"]
            if not prices:
                continue

            cheapest_platform = min(prices, key=prices.get)
            cheapest_price = prices[cheapest_platform]

            results.append({
                "room_name": group["room_name"],
                "cheapest_platform": cheapest_platform,
                "cheapest_price": cheapest_price,
                "all_prices": prices,
                "confidence": group["confidence"],
                "match_quality": group.get("match_quality", "unknown"),
            })

        return results
