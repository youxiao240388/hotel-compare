"""
智能比价引擎 - 价格对比与趋势分析

文档第五章：
- 全网最低价筛选（排除不可取消特价房）
- 同房型含早 vs 不含早折算
- 历史趋势分析（Bug价预警）
"""
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

from config.settings import (
    PRICE_ALERT_THRESHOLD,
    TREND_LOOKBACK_DAYS,
    PROJECT_ROOT,
)
from src.matcher.room_matcher import RoomMatcher

logger = logging.getLogger(__name__)

HISTORY_DIR = PROJECT_ROOT / "data" / "history"


class PriceComparator:
    """比价引擎"""

    def __init__(self):
        self.matcher = RoomMatcher()
        self.history: Dict[str, List[Dict]] = {}
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    def compare(
        self,
        rooms_by_platform: Dict[str, List],
        hotel_name: str = "",
    ) -> Dict:
        """
        执行完整比价流程

        Returns:
            {
                "hotel": "酒店名称",
                "summary": "比价摘要",
                "rooms": [每个房型的最低价平台],
                "alerts": [预警信息],
                "trends": [趋势分析],
            }
        """
        # 1. 房型匹配
        matched = self.matcher.match_rooms(rooms_by_platform)

        # 2. 找每个房型的最低价
        cheapest = self.matcher.find_cheapest_per_room(matched)

        # 3. 历史趋势分析
        alerts = []
        trends = []

        for room in cheapest:
            hist_prices = self._load_history(hotel_name, room["room_name"])

            if hist_prices:
                avg_price = np.mean([h["price"] for h in hist_prices])
                current = room["cheapest_price"]

                # Bug价检测：低于历史均价30%
                if avg_price > 0 and current < avg_price * (1 - PRICE_ALERT_THRESHOLD):
                    alerts.append({
                        "level": "🚨 BUG价",
                        "room": room["room_name"],
                        "current_price": current,
                        "avg_price": avg_price,
                        "drop_percent": f"{(1 - current/avg_price)*100:.0f}%",
                        "platform": room["cheapest_platform"],
                    })

                # 价格上涨预警
                elif avg_price > 0 and current > avg_price * 1.2:
                    trends.append({
                        "type": "📈 价格偏高",
                        "room": room["room_name"],
                        "current_price": current,
                        "avg_price": avg_price,
                        "advice": "建议观望，当前价格高于历史均价",
                    })

            # 保存当前价格到历史
            self._save_history(hotel_name, room["room_name"], room["cheapest_price"])

        # 4. 生成摘要
        total_rooms = len(cheapest)
        platform_stats = {}
        for r in cheapest:
            p = r["cheapest_platform"]
            platform_stats[p] = platform_stats.get(p, 0) + 1

        summary_parts = []
        for platform, count in sorted(platform_stats.items(), key=lambda x: -x[1]):
            summary_parts.append(f"{platform}: {count}个房型最低")

        summary = f"共{total_rooms}个房型 | " + " | ".join(summary_parts)

        return {
            "hotel": hotel_name or "未知酒店",
            "summary": summary,
            "rooms": cheapest,
            "alerts": alerts,
            "trends": trends,
            "matched_groups": matched,
        }

    def _load_history(
        self, hotel_name: str, room_name: str, days: int = None
    ) -> List[Dict]:
        """加载历史价格记录"""
        days = days or TREND_LOOKBACK_DAYS
        safe_name = self._safe_filename(hotel_name, room_name)
        filepath = HISTORY_DIR / f"{safe_name}.json"

        if not filepath.exists():
            return []

        try:
            data = json.loads(filepath.read_text())
            cutoff = date.today() - timedelta(days=days)
            return [d for d in data if date.fromisoformat(d["date"]) >= cutoff]
        except Exception:
            return []

    def _save_history(self, hotel_name: str, room_name: str, price: float):
        """保存当前价格到历史"""
        safe_name = self._safe_filename(hotel_name, room_name)
        filepath = HISTORY_DIR / f"{safe_name}.json"

        records = []
        if filepath.exists():
            try:
                records = json.loads(filepath.read_text())
            except Exception:
                records = []

        records.append({
            "date": date.today().isoformat(),
            "price": price,
        })

        # 只保留最近90天
        cutoff = date.today() - timedelta(days=90)
        records = [r for r in records if date.fromisoformat(r["date"]) >= cutoff]

        filepath.write_text(json.dumps(records, ensure_ascii=False, indent=2))

    def _safe_filename(self, hotel: str, room: str) -> str:
        """生成安全的文件名"""
        import re
        name = f"{hotel}_{room}"
        return re.sub(r"[^\w\u4e00-\u9fff]", "_", name)[:100]
