"""
平台采集器注册表 - 统一管理 9 大平台采集器

平台列表：
  国内: 携程 / 美团 / 飞猪 / 去哪儿 / 抖音 / 京东 / 路客
  国际: Agoda / Booking.com / Expedia
"""
from src.platforms.ctrip import CtripScraper
from src.platforms.meituan import MeituanScraper
from src.platforms.fliggy import FliggyScraper
from src.platforms.international import AgodaScraper, BookingScraper, ExpediaScraper
from src.platforms.domestic import QunarScraper, DouyinScraper, JDScraper, LukeScraper

PLATFORM_SCRAPERS = {
    "ctrip": CtripScraper,
    "meituan": MeituanScraper,
    "fliggy": FliggyScraper,
    "qunar": QunarScraper,
    "agoda": AgodaScraper,
    "booking": BookingScraper,
    "expedia": ExpediaScraper,
    "douyin": DouyinScraper,
    "jd": JDScraper,
    "luke": LukeScraper,
}

PLATFORM_NAMES = {
    "ctrip": "携程",
    "meituan": "美团",
    "fliggy": "飞猪",
    "qunar": "去哪儿",
    "agoda": "Agoda",
    "booking": "Booking.com",
    "expedia": "Expedia",
    "douyin": "抖音",
    "jd": "京东",
    "luke": "路客",
}

PLATFORM_TAGS = ["ctrip", "meituan", "fliggy", "qunar", "agoda", "booking", "expedia", "douyin", "jd", "luke"]
PLATFORM_EMOJI = {
    "ctrip": "🔵", "meituan": "🟡", "fliggy": "🟠", "qunar": "🟢",
    "agoda": "🔴", "booking": "🔷", "expedia": "🟣",
    "douyin": "⚫", "jd": "🔴", "luke": "🟤",
}

# 登录页面
LOGIN_URLS = {
    "ctrip": "https://passport.ctrip.com/user/login",
    "meituan": "https://i.meituan.com/awp/h5/hotel/login",
    "fliggy": "https://login.taobao.com/member/login.jhtml",
    "qunar": "https://user.qunar.com/passport/login.jsp",
    "agoda": "https://www.agoda.com/account/signin.html",
    "booking": "https://account.booking.com/sign-in",
    "expedia": "https://www.expedia.com/user/signin",
    "douyin": "https://www.douyin.com/",
    "jd": "https://passport.jd.com/new/login.aspx",
    "luke": "https://www.lukeclub.com/login",
}


def get_scraper(platform: str, browser_manager):
    """获取平台采集器实例"""
    scraper_class = PLATFORM_SCRAPERS.get(platform.lower())
    if not scraper_class:
        raise ValueError(f"不支持的平台: {platform}. 支持: {list(PLATFORM_SCRAPERS.keys())}")
    return scraper_class(browser_manager)


def build_platform_urls(ctrip_id: str, checkin: str, checkout: str, hotel_name: str = "") -> dict:
    """构造 10 个平台的酒店预订 URL"""
    name_enc = __import__('urllib.parse').quote(hotel_name or ctrip_id)
    return {
        "ctrip": f"https://hotels.ctrip.com/hotel/{ctrip_id}.html?checkin={checkin}&checkout={checkout}",
        "meituan": f"https://hotel.meituan.com/search?keyword={ctrip_id}&checkin={checkin}&checkout={checkout}",
        "fliggy": f"https://travelsearch.fliggy.com/index.htm?searchType=hotel&keyword={name_enc}&checkIn={checkin}&checkOut={checkout}",
        "qunar": f"https://hotel.qunar.com/city/suzhou/dt-{ctrip_id}/?checkInDate={checkin}&checkOutDate={checkout}",
        "agoda": f"https://www.agoda.com/search?city=16490&hotel={name_enc}&checkIn={checkin}&checkOut={checkout}",
        "booking": f"https://www.booking.com/searchresults.html?ss={name_enc}&checkin={checkin}&checkout={checkout}",
        "expedia": f"https://www.expedia.com/Hotel-Search?destination={name_enc}&startDate={checkin}&endDate={checkout}",
        "douyin": f"https://www.douyin.com/search/{name_enc}%20酒店?type=general",
        "jd": f"https://hotel.jd.com/search.html?keyword={name_enc}&checkin={checkin}&checkout={checkout}",
        "luke": f"https://www.lukeclub.com/search?keyword={name_enc}",
    }
