"""
飞猪 (Fliggy) 采集器

飞猪需通过淘宝账号登录，接管模式下利用已登录会话。
搜索入口: https://travelsearch.fliggy.com/index.htm
"""
import logging
from datetime import date
from urllib.parse import quote

from src.platforms.base import BaseScraper, RoomInfo

logger = logging.getLogger(__name__)


class FliggyScraper(BaseScraper):
    """飞猪酒店采集器"""
    platform_name = "fliggy"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        # 飞猪酒店详情页
        return (
            f"https://hotel.fliggy.com/hotel_detail.htm"
            f"?hotelId={hotel_id}"
            f"&checkIn={checkin.isoformat()}"
            f"&checkOut={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        """从飞猪页面提取房型"""
        rooms = []
        try:
            self.browser.wait_for_element("css:.room-list, .hotel-room-item, .J_RoomList")
            self.browser.human_scroll()

            room_items = page.eles("css:.room-list-item, .J_RoomItem, [data-spm='room']")
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
                    name = self._safe_extract_text(item, "css:.room-title, .name, .room-name")
                    price_ele = item.ele("css:.price, .room-price, .J_Price")
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
            logger.error(f"飞猪数据提取失败: {e}")

        return rooms
