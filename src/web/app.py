"""
Web 可视化界面 - Flask 后端

路由：
  GET  /                → 仪表盘主页
  POST /api/search      → 搜索酒店
  POST /api/compare     → 执行比价
  GET  /api/status      → 检查各平台 Cookie 状态
  POST /api/cookie/import → 导入平台 Cookie
  POST /api/cookie/clear  → 清除平台 Cookie
  POST /api/navigate    → 在浏览器中打开 URL（点击价格跳转）
  GET  /api/result/{id} → 获取比价结果
"""
import json
import logging
import threading
from datetime import date, datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_from_directory

from src.browser import AutoBrowser
from src.search import search_hotel
from src.cookies import (
    save_cookies, load_cookies, get_cookie_status,
    clear_cookies, parse_cookie_string, list_all_cookies,
    PLATFORM_DOMAINS,
)
from src.platforms import (
    get_scraper, PLATFORM_SCRAPERS, PLATFORM_NAMES, PLATFORM_TAGS,
    PLATFORM_EMOJI, LOGIN_URLS as ALL_LOGIN_URLS, build_platform_urls,
)
from src.parser.extractor import LLMParser
from src.comparator.engine import PriceComparator

logger = logging.getLogger(__name__)

app = Flask(__name__, 
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# 全局状态
browser: AutoBrowser | None = None
comparison_cache: dict = {}
_task_lock = threading.Lock()


def get_browser() -> AutoBrowser:
    global browser
    if browser is None:
        browser = AutoBrowser()
        browser.connect()
    return browser


# ====== 页面路由 ======

@app.route("/")
def index():
    """仪表盘主页"""
    platforms = [
        {"id": p, "name": PLATFORM_NAMES.get(p, p), "url": ALL_LOGIN_URLS.get(p, ""), "emoji": PLATFORM_EMOJI.get(p, "⚪")}
        for p in PLATFORM_TAGS
    ]
    return render_template("dashboard.html", platforms=platforms)


# ====== API 路由 ======

@app.route("/api/status")
def api_status():
    """检查各平台 Cookie 状态"""
    statuses = {}
    for plat in PLATFORM_TAGS:
        status = get_cookie_status(plat)
        statuses[plat] = {
            "name": PLATFORM_NAMES.get(plat, plat),
            "logged_in": status["has_cookies"] and status["count"] > status["expired_count"],
            "cookie_count": status["count"],
            "expired_count": status["expired_count"],
            "last_modified": status["last_modified"],
        }
    return jsonify(statuses)


@app.route("/api/cookie/import", methods=["POST"])
def api_cookie_import():
    """导入平台 Cookie"""
    data = request.get_json()
    platform = data.get("platform", "").strip()
    cookie_text = data.get("cookies", "").strip()

    if not platform:
        return jsonify({"error": "请选择平台"}), 400
    if platform not in PLATFORM_DOMAINS:
        return jsonify({"error": f"不支持的平台: {platform}"}), 400
    if not cookie_text:
        return jsonify({"error": "请粘贴 Cookie 内容"}), 400

    # 解析各种格式
    cookies = parse_cookie_string(cookie_text)
    if not cookies:
        return jsonify({"error": "无法解析 Cookie，请检查格式"}), 400

    # 保存
    result = save_cookies(platform, cookies)
    if not result["ok"]:
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "ok": True,
        "message": f"已保存 {result['count']} 条 Cookie 到 {PLATFORM_NAMES.get(platform, platform)}",
        "count": result["count"],
    })


@app.route("/api/cookie/clear", methods=["POST"])
def api_cookie_clear():
    """清除平台 Cookie"""
    data = request.get_json()
    platform = data.get("platform", "").strip()

    if not platform:
        return jsonify({"error": "请指定平台"}), 400

    cleared = clear_cookies(platform)
    return jsonify({
        "ok": True,
        "message": f"已清除 {PLATFORM_NAMES.get(platform, platform)} 的 Cookie" if cleared else "该平台无 Cookie",
    })


@app.route("/api/search", methods=["POST"])
def api_search():
    """搜索酒店"""
    data = request.get_json()
    hotel_name = data.get("hotel", "").strip()
    
    if not hotel_name:
        return jsonify({"error": "请输入酒店名称"}), 400
    
    b = get_browser()
    hotel_info = search_hotel(hotel_name, b)
    
    if not hotel_info:
        return jsonify({"error": f"未找到酒店 '{hotel_name}'"}), 404
    
    return jsonify({
        "name": hotel_info.name,
        "ctrip_id": hotel_info.ctrip_id,
        "address": hotel_info.address or "",
        "city": hotel_info.city or "苏州",
    })


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """执行多平台比价"""
    with _task_lock:
        data = request.get_json()
        hotel_name = data.get("hotel", "")
        checkin_str = data.get("checkin", "")
        checkout_str = data.get("checkout", "")
        platforms = data.get("platforms", list(PLATFORM_SCRAPERS.keys()))
        
        if not all([hotel_name, checkin_str, checkout_str]):
            return jsonify({"error": "缺少必要参数"}), 400
        
        try:
            checkin = date.fromisoformat(checkin_str)
            checkout = date.fromisoformat(checkout_str)
        except ValueError:
            return jsonify({"error": "日期格式错误"}), 400
        
        # 搜索酒店
        b = get_browser()
        hotel_info = search_hotel(hotel_name, b)
        if not hotel_info:
            return jsonify({"error": f"未找到酒店 '{hotel_name}'"}), 404
        
        # 采集各平台
        rooms_by_platform = {}
        llm_parser = LLMParser()
        
        for plat in platforms:
            try:
                scraper = get_scraper(plat, b)
                result = scraper.scrape(
                    hotel_info.ctrip_id, checkin, checkout, hotel_info.name
                )
                
                if not result.success:
                    continue
                
                rooms = result.rooms
                # LLM 解析
                if rooms and "page_text" in getattr(rooms[0], 'raw_data', {}):
                    raw_text = rooms[0].raw_data["page_text"]
                    rooms = llm_parser.extract_rooms(raw_text, plat)
                
                if rooms:
                    rooms_by_platform[plat] = rooms
            except Exception as e:
                logger.error(f"{plat} 采集失败: {e}")
        
        if not rooms_by_platform:
            return jsonify({"error": "所有平台采集失败"}), 500
        
        # 比价
        comparator = PriceComparator()
        result = comparator.compare(rooms_by_platform, hotel_info.name)

        # 生成各平台预订链接
        platform_urls = build_platform_urls(hotel_info.ctrip_id, checkin_str, checkout_str, hotel_name)

        # 缓存结果
        task_id = f"{hotel_info.ctrip_id}_{checkin_str}"
        comparison_cache[task_id] = result

        return jsonify({
            "task_id": task_id,
            "hotel": result["hotel"],
            "summary": result["summary"],
            "rooms": result["rooms"],
            "platform_urls": platform_urls,
            "alerts": result.get("alerts", []),
            "trends": result.get("trends", []),
        })


@app.route("/api/result/<task_id>")
def api_result(task_id):
    """获取缓存的比价结果"""
    result = comparison_cache.get(task_id)
    if not result:
        return jsonify({"error": "结果已过期，请重新比价"}), 404
    return jsonify(result)


@app.route("/api/navigate", methods=["POST"])
def api_navigate():
    """在 Chrome 浏览器中打开指定 URL（点击价格跳转）"""
    data = request.get_json()
    url = data.get("url", "")
    platform = data.get("platform", "")

    if not url:
        return jsonify({"error": "缺少 URL"}), 400

    b = get_browser()
    try:
        # 在新标签页打开平台页面
        b.page.new_tab(url)
        name = PLATFORM_NAMES.get(platform, platform) or "平台"
        return jsonify({
            "ok": True,
            "message": f"已在浏览器中打开 {name} 实时价格页面",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_web(port: int = 8888, open_browser: bool = True):
    """启动 Web 服务"""
    if open_browser:
        import webbrowser
        import time
        def _open():
            time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open, daemon=True).start()
    
    print(f"\n🏨 酒店比价工具 Web 界面")
    print(f"   浏览器访问: http://127.0.0.1:{port}")
    print(f"   按 Ctrl+C 退出\n")
    
    app.run(host="127.0.0.1", port=port, debug=False)
