"""
酒店搜索引擎 - 自动获取酒店在各平台的 ID

流程：
1. 搜狗搜索 "酒店名 + 携程"
2. 提取携程酒店 ID
3. 构建各平台 URL
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from src.browser import AutoBrowser

logger = logging.getLogger(__name__)


@dataclass
class HotelInfo:
    """酒店信息"""
    name: str
    ctrip_id: Optional[str] = None
    meituan_id: Optional[str] = None
    fliggy_id: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

    def to_urls(self, checkin: str, checkout: str) -> dict:
        """生成各平台预订链接"""
        urls = {}
        if self.ctrip_id:
            urls["ctrip"] = (
                f"https://hotels.ctrip.com/hotel/{self.ctrip_id}.html"
                f"?checkin={checkin}&checkout={checkout}"
            )
        if self.fliggy_id:
            urls["fliggy"] = (
                f"https://hotel.fliggy.com/hotel_detail.htm"
                f"?hotelId={self.fliggy_id}"
                f"&checkIn={checkin}&checkOut={checkout}"
            )
        return urls


class HotelSearch:
    """酒店搜索引擎"""

    def __init__(self, browser: AutoBrowser = None):
        self.browser = browser
        self._known_hotels = {
            # 预置已知酒店
            "凯里亚德酒店苏州观前街店": HotelInfo(
                name="凯里亚德酒店(苏州网狮园十全街店)",
                ctrip_id="44111878",
                address="苏州市姑苏区南园北路79号",
            ),
            "凯里亚德酒店": HotelInfo(
                name="凯里亚德酒店(苏州网狮园十全街店)",
                ctrip_id="44111878",
                address="苏州市姑苏区南园北路79号",
            ),
        }

    def search(self, hotel_name: str) -> Optional[HotelInfo]:
        """
        搜索酒店，自动获取 ID

        优先级：
        1. 本地已知酒店库
        2. 搜狗搜索 → 提取携程 ID
        """
        # 1. 查本地库（精确匹配 → 模糊匹配）
        if hotel_name in self._known_hotels:
            return self._known_hotels[hotel_name]

        for name, info in self._known_hotels.items():
            if hotel_name in name or name in hotel_name:
                logger.info(f"本地模糊匹配: '{hotel_name}' → '{name}'")
                return info

        # 2. 搜狗搜索
        if self.browser:
            return self._sogou_search(hotel_name)

        return None

    def _sogou_search(self, hotel_name: str) -> Optional[HotelInfo]:
        """
        通过搜狗搜索获取携程酒店 ID

        搜索词: "酒店名 + 携程"
        从搜索结果页提取 hotels.ctrip.com/hotel/<ID>.html
        """
        query = f"{hotel_name} 携程"
        url = f"https://www.sogou.com/web?query={quote(query)}"

        logger.info(f"🔍 搜狗搜索: '{query}'")

        try:
            page = self.browser.page
            if not page:
                logger.warning("浏览器未连接，无法搜索")
                return None

            page.get(url)
            self.browser.human_delay(2, 4)

            # 提取页面文本
            html = page.html

            # 提取携程酒店 URL
            ctrip_patterns = [
                r'https?://hotels?\.ctrip\.com/hotel/(\d+)\.html',
                r'ctrip\.com/hotel/(\d+)',
                r'hotels\.ctrip\.com/hotel/(\d+)',
            ]

            ctrip_id = None
            for pattern in ctrip_patterns:
                match = re.search(pattern, html)
                if match:
                    ctrip_id = match.group(1)
                    logger.info(f"✅ 找到携程 ID: {ctrip_id}")
                    break

            if not ctrip_id:
                logger.warning(f"未在搜索结果中找到 '{hotel_name}' 的携程 ID")
                return None

            info = HotelInfo(name=hotel_name, ctrip_id=ctrip_id)
            self._known_hotels[hotel_name] = info
            return info

        except Exception as e:
            logger.error(f"搜狗搜索失败: {e}")
            return None

    def add_known(self, name: str, ctrip_id: str, **kwargs):
        """手动添加已知酒店"""
        self._known_hotels[name] = HotelInfo(
            name=name, ctrip_id=ctrip_id, **kwargs
        )


def search_hotel(hotel_name: str, browser: AutoBrowser = None) -> Optional[HotelInfo]:
    """快捷函数：搜索酒店"""
    searcher = HotelSearch(browser)
    return searcher.search(hotel_name)
