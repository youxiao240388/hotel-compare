"""
Agoda 采集器

Agoda 相对好抓，支持按酒店名搜索，API 较开放
"""
import logging
from datetime import date
from urllib.parse import quote

from src.platforms.base import BaseScraper, RoomInfo

logger = logging.getLogger(__name__)


class AgodaScraper(BaseScraper):
    """Agoda 酒店采集器"""
    platform_name = "agoda"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        # Agoda 用酒店名搜索比 ID 更可靠
        name = quote(getattr(self, '_hotel_name', hotel_id))
        return (
            f"https://www.agoda.com/search"
            f"?city=16490"  # 苏州 city ID
            f"&hotel={name}"
            f"&checkIn={checkin.isoformat()}"
            f"&checkOut={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            self.browser.human_scroll()

            # Agoda 房型列表
            room_blocks = page.eles("css:[data-selenium='room-card'], .RoomCard, .room-item")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name,
                    room_name="原始数据",
                    price=0.0,
                    raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name_ele = block.ele("css:[data-selenium='room-name'], .roomname, h3")
                    price_ele = block.ele("css:[data-selenium='room-price'], .price, .Price")
                    name = name_ele.text.strip() if name_ele else ""
                    price = self._safe_price(price_ele.text) if price_ele else 0.0

                    rooms.append(RoomInfo(
                        platform=self.platform_name,
                        room_name=name,
                        price=price,
                        raw_data={"element_html": block.html[:2000]}
                    ))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Agoda 提取失败: {e}")

        return rooms


class BookingScraper(BaseScraper):
    """Booking.com 采集器"""
    platform_name = "booking"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://www.booking.com/searchresults.html"
            f"?ss={quote(hotel_id)}"
            f"&checkin={checkin.isoformat()}"
            f"&checkout={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            room_blocks = page.eles("css:[data-testid='room'], .room-paragraph, .hprt-table-row")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name, room_name="原始数据",
                    price=0.0, raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name = self._safe_extract_text(block, "css:.room-link, .hprt-roomtype-link, h3")
                    price_ele = block.ele("css:.prco-valign-middle-helper, .bui-price-display__value, .roomPrice")
                    price = self._safe_price(price_ele.text) if price_ele else 0.0
                    rooms.append(RoomInfo(platform=self.platform_name, room_name=name, price=price,
                                          raw_data={"element_html": block.html[:2000]}))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Booking 提取失败: {e}")
        return rooms


class ExpediaScraper(BaseScraper):
    """Expedia 采集器"""
    platform_name = "expedia"

    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        return (
            f"https://www.expedia.com/Hotel-Search"
            f"?destination={quote(hotel_id)}"
            f"&startDate={checkin.isoformat()}"
            f"&endDate={checkout.isoformat()}"
        )

    def extract_rooms(self, page) -> list[RoomInfo]:
        rooms = []
        try:
            self.browser.human_delay(2, 4)
            self.browser.human_scroll()

            room_blocks = page.eles("css:[data-stid='property-offer'], .uitk-card, .room-rate")
            if not room_blocks:
                text = page.ele("tag:body").text
                return [RoomInfo(
                    platform=self.platform_name, room_name="原始数据",
                    price=0.0, raw_data={"page_text": text[:5000]}
                )]

            for block in room_blocks[:20]:
                try:
                    name = self._safe_extract_text(block, "css:.uitk-heading, .room-name, h3")
                    price_ele = block.ele("css:[data-stid='price-lockup'], .price, .uitk-lockup-price")
                    price = self._safe_price(price_ele.text) if price_ele else 0.0
                    rooms.append(RoomInfo(platform=self.platform_name, room_name=name, price=price,
                                          raw_data={"element_html": block.html[:2000]}))
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Expedia 提取失败: {e}")
        return rooms
