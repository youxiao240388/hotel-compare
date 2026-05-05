"""
Cookie 管理模块 - 解决平台登录态问题

工作流：
1. 用户在自己的浏览器中登录各平台
2. 通过浏览器扩展（EditThisCookie / Cookie-Editor）导出 cookie JSON
3. 在 Web 界面粘贴 JSON → 保存到本地
4. 采集前自动注入到 headless Chrome

支持的 cookie 格式：
- EditThisCookie 导出格式 (数组)
- Cookie-Editor 导出格式 (数组)
- 手动 JSON: {"name": "xx", "value": "yy", "domain": ".xxx.com"}
- 简单 key=value 字符串
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Cookie 存储目录
COOKIE_DIR = Path.home() / ".hotel-compare" / "cookies"

# 平台 → cookie 域名映射（用于注入时匹配）
PLATFORM_DOMAINS = {
    "ctrip": [".ctrip.com", ".ctrip.cn", "hotels.ctrip.com"],
    "meituan": [".meituan.com", "hotel.meituan.com", "i.meituan.com"],
    "fliggy": [".fliggy.com", ".taobao.com", ".tmall.com", "login.taobao.com"],
    "qunar": [".qunar.com", "hotel.qunar.com", "user.qunar.com"],
    "agoda": [".agoda.com", "www.agoda.com"],
    "booking": [".booking.com", "www.booking.com"],
    "expedia": [".expedia.com", "www.expedia.com"],
    "douyin": [".douyin.com", "www.douyin.com"],
    "jd": [".jd.com", "hotel.jd.com", "passport.jd.com"],
    "luke": [".lukeclub.com", "www.lukeclub.com"],
}


def _ensure_cookie_dir():
    """确保 cookie 目录存在"""
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)


def _cookie_path(platform: str) -> Path:
    """获取平台 cookie 文件路径"""
    _ensure_cookie_dir()
    return COOKIE_DIR / f"{platform}.json"


def save_cookies(platform: str, cookies: list[dict]) -> dict:
    """
    保存平台 cookie 到本地文件

    参数:
        platform: 平台 ID (ctrip, meituan, ...)
        cookies: cookie 列表，每项至少有 name, value

    返回:
        {"ok": True, "count": N, "path": "..."}
    """
    path = _cookie_path(platform)

    # 标准化 cookie 格式
    normalized = []
    for c in cookies:
        if not isinstance(c, dict):
            continue
        name = c.get("name", "").strip()
        value = c.get("value", "").strip()
        if not name:
            continue

        entry = {
            "name": name,
            "value": value,
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
        }
        # 保留过期时间（如果有）
        if "expirationDate" in c:
            entry["expirationDate"] = c["expirationDate"]
        elif "expires" in c:
            entry["expirationDate"] = c["expires"]

        normalized.append(entry)

    if not normalized:
        return {"ok": False, "error": "未解析到有效 cookie"}

    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[cookie] 已保存 {platform} 的 {len(normalized)} 条 cookie → {path}")
    return {"ok": True, "count": len(normalized), "path": str(path)}


def load_cookies(platform: str) -> list[dict]:
    """
    从本地文件加载平台 cookie

    返回 cookie 列表，文件不存在则返回空列表
    """
    path = _cookie_path(platform)
    if not path.exists():
        return []

    try:
        cookies = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(cookies, list):
            return cookies
        return []
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"[cookie] 加载 {platform} cookie 失败: {e}")
        return []


def get_cookie_status(platform: str) -> dict:
    """
    检查平台 cookie 状态

    返回:
        {"has_cookies": bool, "count": N, "expired_count": N, "last_modified": "..."}
    """
    path = _cookie_path(platform)
    if not path.exists():
        return {"has_cookies": False, "count": 0, "expired_count": 0, "last_modified": None}

    cookies = load_cookies(platform)
    now = time.time()
    expired = 0
    for c in cookies:
        exp = c.get("expirationDate")
        if exp and isinstance(exp, (int, float)) and exp < now:
            expired += 1

    mtime = path.stat().st_mtime
    from datetime import datetime
    last_mod = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    return {
        "has_cookies": len(cookies) > 0,
        "count": len(cookies),
        "expired_count": expired,
        "last_modified": last_mod,
    }


def inject_cookies(page, platform: str) -> int:
    """
    将保存的 cookie 注入到浏览器页面

    通过 DrissionPage 的 CDP 接口注入 cookie，
    必须在 page.get(url) 之前调用。

    参数:
        page: DrissionPage ChromiumPage 实例
        platform: 平台 ID

    返回:
        成功注入的 cookie 数量
    """
    cookies = load_cookies(platform)
    if not cookies:
        logger.debug(f"[cookie] {platform} 无 cookie 可注入")
        return 0

    # 获取平台域名列表
    domains = PLATFORM_DOMAINS.get(platform, [])

    injected = 0
    for c in cookies:
        try:
            name = c.get("name", "")
            value = c.get("value", "")
            if not name:
                continue

            # 确定 cookie 域名
            domain = c.get("domain", "")
            if not domain and domains:
                domain = domains[0]  # 用平台默认域名

            # 通过 CDP 设置 cookie
            cookie_params = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
            }
            # 设置过期时间
            exp = c.get("expirationDate")
            if exp and isinstance(exp, (int, float)):
                cookie_params["expires"] = exp

            # DrissionPage 底层用 CDP
            page.run_cdp("Network.setCookie", **cookie_params)
            injected += 1

        except Exception as e:
            logger.debug(f"[cookie] 注入失败 {c.get('name', '?')}: {e}")
            continue

    logger.info(f"[cookie] 已向 {platform} 注入 {injected}/{len(cookies)} 条 cookie")
    return injected


def clear_cookies(platform: str) -> bool:
    """清除平台 cookie 文件"""
    path = _cookie_path(platform)
    if path.exists():
        path.unlink()
        logger.info(f"[cookie] 已清除 {platform} 的 cookie")
        return True
    return False


def parse_cookie_string(cookie_str: str) -> list[dict]:
    """
    解析各种格式的 cookie 输入

    支持:
    1. JSON 数组 (EditThisCookie / Cookie-Editor 导出)
    2. JSON 对象 {"key": "value", ...}
    3. key=value; key2=value2 字符串
    """
    cookie_str = cookie_str.strip()
    if not cookie_str:
        return []

    # 尝试 JSON 解析
    try:
        data = json.loads(cookie_str)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 可能是 {name: value} 简单格式
            if "name" in data and "value" in data:
                return [data]
            # 也可能是 {"key1": "val1", "key2": "val2"} 格式
            return [{"name": k, "value": v} for k, v in data.items() if isinstance(v, str)]
    except json.JSONDecodeError:
        pass

    # 尝试 key=value; key2=value2 格式
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({"name": name, "value": value})

    return cookies


def list_all_cookies() -> dict:
    """列出所有平台的 cookie 状态"""
    result = {}
    for platform in PLATFORM_DOMAINS:
        status = get_cookie_status(platform)
        result[platform] = status
    return result
