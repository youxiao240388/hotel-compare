"""
美团 (Meituan) 酒店采集器

美团移动端 WAP 版相对好抓: https://hotel.meituan.com/
"""
import logging
from datetime import date
from urllib.parse import quote

from src.platforms.base import BaseScraper, RoomInfo

logger = logging.getLogger(__name__)


class MeituanScraper(BaseScraper):
    """美团酒店采集器"""
    platform_name = "meituan"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        # 美团搜索页
        return f"https://hotel.meituan.com/search?keyword={hotel_id}"

    def extract_rooms(self, page) -> list[RoomInfo]:
        """从美团页面提取房型"""
        rooms = []
        try:
            # 等待价格列表加载
            self.browser.wait_for_element("css:.hotel-room-list, .room-item")
            self.browser.human_scroll()

            room_items = page.eles("css:.room-item, .room-list-item, li[data-poiid]")
            if not room_items:
                text_content = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name,
                    room_name="原始数据",
                    price=0.0,
                    raw_data={"page_text": text_content[:5000]}
                )]

            for item in room_items[:20]:
                try:
                    name = self._safe_extract_text(item, "css:.room-name, .name, h3")
                    price_ele = item.ele("css:.price, .current-price, .sale-price")
                    price_text = price_ele.text if price_ele else ""
                    price = self._safe_price(price_text)

                    rooms.append(RoomInfo(
                        platform=self.platform_name,
                        room_name=name,
                        price=price,
                        raw_data={"element_html": item.html[:2000]}
                    ))
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"美团数据提取失败: {e}")

        return rooms
