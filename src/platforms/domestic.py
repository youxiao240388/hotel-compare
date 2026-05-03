"""
国内新增平台采集器：去哪儿 / 抖音 / 京东 / 路客
"""
import logging
from datetime import date
from urllib.parse import quote

from src.platforms.base import BaseScraper, RoomInfo

logger = logging.getLogger(__name__)


class QunarScraper(BaseScraper):
    """去哪儿采集器（与携程同属一组，酒店 ID 可能通用）"""
    platform_name = "qunar"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://hotel.qunar.com/city/suzhou/dt-{hotel_id}/"
            f"?checkInDate={checkin.isoformat()}&checkOutDate={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            self.browser.human_scroll()

            room_blocks = page.eles("css:.room-item, .e_room_item, [data-room]")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name, room_name="原始数据",
                    price=0.0, raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name = self._safe_extract_text(block, "css:.roomname, .room-type, h3")
                    price_ele = block.ele("css:.price, .room_price, .e_price")
                    price = self._safe_price(price_ele.text) if price_ele else 0.0
                    rooms.append(RoomInfo(platform=self.platform_name, room_name=name, price=price,
                                          raw_data={"element_html": block.html[:2000]}))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"去哪儿 提取失败: {e}")
        return rooms


class DouyinScraper(BaseScraper):
    """抖音/抖音生活服务 采集器"""
    platform_name = "douyin"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://www.douyin.com/search/{quote(hotel_id)}%20酒店"
            f"?type=general"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            text = page.ele("tag:body").text
            return [RoomInfo(
                platform=self.platform_name, room_name="原始数据",
                price=0.0, raw_data={"page_text": text[:5000]}
            )]
        except Exception as e:
            logger.error(f"抖音 提取失败: {e}")
        return rooms


class JDScraper(BaseScraper):
    """京东旅行 采集器"""
    platform_name = "jd"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://hotel.jd.com/search.html"
            f"?keyword={quote(hotel_id)}"
            f"&checkin={checkin.isoformat()}&checkout={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            self.browser.human_scroll()

            room_blocks = page.eles("css:.room-item, .hotel-room, [data-roomid]")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name, room_name="原始数据",
                    price=0.0, raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name = self._safe_extract_text(block, "css:.room-name, .name, h3")
                    price_ele = block.ele("css:.price, .jd-price, .room-price")
                    price = self._safe_price(price_ele.text) if price_ele else 0.0
                    rooms.append(RoomInfo(platform=self.platform_name, room_name=name, price=price,
                                          raw_data={"element_html": block.html[:2000]}))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"京东 提取失败: {e}")
        return rooms


class LukeScraper(BaseScraper):
    """路客(Locumundo)精品民宿 采集器"""
    platform_name = "luke"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return f"https://www.lukeclub.com/search?keyword={quote(hotel_id)}"

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            self.browser.human_scroll()

            room_blocks = page.eles("css:.room-card, .house-item, [data-id]")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name, room_name="原始数据",
                    price=0.0, raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name = self._safe_extract_text(block, "css:.name, .title, h3")
                    price_ele = block.ele("css:.price, .unit-price, .now-price")
                    price = self._safe_price(price_ele.text) if price_ele else 0.0
                    rooms.append(RoomInfo(platform=self.platform_name, room_name=name, price=price,
                                          raw_data={"element_html": block.html[:2000]}))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"路客 提取失败: {e}")
        return rooms
