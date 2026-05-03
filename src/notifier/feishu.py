"""
飞书通知模块 - 价格预警推送到飞书

支持：
1. 价格低于阈值预警
2. Bug价实时推送
3. Cookie失效提醒
"""
import logging
from typing import Dict, List

from config.settings import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_ID

logger = logging.getLogger(__name__)


class FeishuNotifier:
    """飞书消息通知"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.user_id = FEISHU_USER_ID

    def send_alert(self, comparison_result: Dict) -> bool:
        """
        发送比价结果通知

        格式：富文本消息，包含酒店名、各房型最低价平台、预警信息
        """
        alerts = comparison_result.get("alerts", [])
        trends = comparison_result.get("trends", [])
        rooms = comparison_result.get("rooms", [])
        hotel = comparison_result.get("hotel", "")
        summary = comparison_result.get("summary", "")

        # 构建消息
        lines = [f"🏨 **{hotel}** 比价结果", ""]

        # 摘要
        lines.append(f"📊 {summary}")
        lines.append("")

        # 房型详情
        lines.append("**各房型最低价：**")
        for room in rooms:
            name = room["room_name"]
            platform = room["cheapest_platform"]
            price = room["cheapest_price"]
            confidence = room.get("confidence", 1.0)
            match_q = room.get("match_quality", "")

            flag = ""
            if match_q == "medium":
                flag = " ⚠️低置信度"
            elif match_q == "high":
                flag = ""

            lines.append(f"• {name}: **¥{price}** @ {platform}{flag}")

        # 预警信息
        if alerts:
            lines.append("")
            lines.append("🚨 **价格预警：**")
            for alert in alerts:
                lines.append(
                    f"• {alert['level']} {alert['room']}: "
                    f"¥{alert['current_price']} "
                    f"(历史均价 ¥{alert['avg_price']:.0f}, "
                    f"降幅 {alert['drop_percent']}) @ {alert['platform']}"
                )

        if trends:
            lines.append("")
            lines.append("📈 **趋势提醒：**")
            for t in trends:
                lines.append(f"• {t['room']}: {t['advice']}")

        message = "\n".join(lines)

        # 当前在飞书对话中，直接回复即可
        # 如需通过 API 发送（独立部署场景），使用飞书 IM API
        logger.info("📤 飞书通知已准备")
        return message
