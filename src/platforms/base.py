"""
平台采集基类 - 定义统一的数据采集接口

所有平台采集器必须继承此类，实现统一的采集流程。
"""
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

from src.cookies import inject_cookies

logger = logging.getLogger(__name__)


@dataclass
class RoomInfo:
    """标准化房型信息"""
    platform: str                    # 平台名称
    room_name: str                   # 房型名称
    price: float                     # 价格（元）
    original_price: float = 0.0      # 原价/划线价
    includes_breakfast: bool = False # 是否含早
    cancellation: str = ""           # 取消政策
    bed_type: str = ""               # 床型
    room_area: str = ""              # 面积
    available: bool = True           # 是否有房
    stock_info: str = ""             # 库存信息（如"仅剩2间"）
    booking_url: str = ""            # 预订链接
    raw_data: dict = field(default_factory=dict)  # 原始数据


@dataclass
class ScrapeResult:
    """采集结果"""
    platform: str
    hotel_name: str
    checkin: date
    checkout: date
    rooms: list[RoomInfo] = field(default_factory=list)
    screenshot_path: str = ""
    timestamp: str = ""
    success: bool = True
    error: str = ""


class BaseScraper(ABC):
    """平台采集器基类"""

    platform_name: str = "base"

    def __init__(self, browser_manager):
        self.browser: AutoBrowser = browser_manager

    @abstractmethod
    def build_url(self, hotel_id: str, checkin: date, checkout: date) -> str:
        """构造平台搜索 URL"""
        ...

    @abstractmethod
    def extract_rooms(self, page) -> list[RoomInfo]:
        """从页面提取房型信息"""
        ...

    def scrape(
        self,
        hotel_id: str,
        checkin: date,
        checkout: date,
        hotel_name: str = "",
    ) -> ScrapeResult:
        """
        采集流程：
        1. 构造 URL 并导航
        2. 等待关键元素加载
        3. 模拟人类行为触发懒加载
        4. 截取全屏快照
        5. 提取房型数据
        6. 返回标准化结果
        """
        result = ScrapeResult(
            platform=self.platform_name,
            hotel_name=hotel_name,
            checkin=checkin,
            checkout=checkout,
        )

        try:
            page = self.browser.connect()

            # 0. 注入 cookie（必须在导航前）
            n_cookies = inject_cookies(page, self.platform_name)
            if n_cookies:
                logger.info(f"[{self.platform_name}] 已注入 {n_cookies} 条 cookie")
            else:
                logger.warning(f"[{self.platform_name}] 无 cookie，可能无法获取价格")

            # 1. 导航
            url = self.build_url(hotel_id, checkin, checkout)
            logger.info(f"[{self.platform_name}] 导航到: {url}")
            page.get(url)
            self.browser.human_delay(2, 4)

            # 2. 检测反爬
            if self.browser.is_blocked():
                result.success = False
                result.error = "触发反爬封锁"
                logger.warning(f"[{self.platform_name}] 触发反爬")
                return result

            # 3. 等待加载 + 模拟行为
            self._wait_and_simulate(page)

            # 4. 提取数据
            result.rooms = self.extract_rooms(page)
            logger.info(f"[{self.platform_name}] 提取到 {len(result.rooms)} 个房型")

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"[{self.platform_name}] 采集失败: {e}")

        return result

    def _wait_and_simulate(self, page):
        """等待页面加载 + 模拟人类行为"""
        # 等待主体内容加载
        time.sleep(2)
        self.browser.human_scroll()
        self.browser.human_delay()

    def _safe_extract_text(self, page, selector: str) -> str:
        """安全提取文本"""
        try:
            ele = page.ele(selector, timeout=3)
            return ele.text.strip() if ele else ""
        except Exception:
            return ""

    def _safe_price(self, text: str) -> float:
        """安全解析价格字符串为浮点数"""
        import re
        if not text:
            return 0.0
        match = re.search(r"[\d,]+\.?\d*", str(text).replace(",", ""))
        return float(match.group()) if match else 0.0
