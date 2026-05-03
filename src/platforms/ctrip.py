"""
携程 (Ctrip) 采集器

URL 格式: https://hotels.ctrip.com/hotel/{hotel_id}.html?checkin=2024-01-01&checkout=2024-01-02
"""
import logging
from datetime import date
from typing import List
from urllib.parse import urlencode

from src.platforms.base import BaseScraper, RoomInfo, ScrapeResult

logger = logging.getLogger(__name__)


class CtripScraper(BaseScraper):
    """携程酒店采集器"""
    platform_name = "ctrip"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://hotels.ctrip.com/hotel/{hotel_id}.html"
            f"?checkin={checkin.isoformat()}&checkout={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        """从携程页面提取房型"""
        rooms = []
        try:
            # 携程房型列表通常在一个容器内
            room_cards = page.eles("css:.room-card, .roomlist-room, .J_roomList [data-roomid]")
            if not room_cards:
                # 备选：提取全部可见文本交给 LLM 处理
                text_content = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name,
                    room_name="原始数据",
                    price=0.0,
                    raw_data={"page_text": text_content[:5000]}
                )]

            for card in room_cards[:20]:  # 最多取20个房型
                try:
                    name = self._safe_extract_text(card, "css:.roomname, .room-type-name, h3")
                    price_ele = card.ele("css:.price, .real-price, .J_price")
                    price_text = price_ele.text if price_ele else ""
                    price = self._safe_price(price_text)

                    rooms.append(RoomInfo(
                        platform=self.platform_name,
                        room_name=name,
                        price=price,
                        raw_data={"element_html": card.html[:2000]}
                    ))
                except Exception as e:
                    logger.debug(f"解析单个房型失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"携程数据提取失败: {e}")

        return rooms
