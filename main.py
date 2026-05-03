#!/usr/bin/env python3
"""
酒店多平台比价工具 - CLI 入口 v2.1（Web + CLI 双模式）

用法:
    # Web 可视化界面（推荐）
    python main.py --web

    # CLI 模式
    python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --checkout 2024-06-02
    python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --login
    python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --monitor --interval 6h
"""
import argparse
import json
import logging
import sys
import time
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.browser import AutoBrowser
from src.search import search_hotel
from src.platforms import get_scraper, PLATFORM_SCRAPERS, PLATFORM_NAMES
from src.parser.extractor import LLMParser
from src.comparator.engine import PriceComparator
from src.notifier.feishu import FeishuNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("hotel-compare")
console = Console()


def parse_args():
    p = argparse.ArgumentParser(
        description="🏨 酒店多平台比价工具 - Web + CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Web 模式:
  python main.py --web                        # 打开可视化界面（推荐）
  python main.py --web --port 9999            # 指定端口

CLI 模式:
  python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --checkout 2024-06-02
  python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --login
  python main.py --hotel "凯里亚德酒店" --checkin 2024-06-01 --monitor --interval 6h
        """,
    )
    p.add_argument("--web", action="store_true", help="启动 Web 可视化界面")
    p.add_argument("--port", type=int, default=8888, help="Web 端口 (默认 8888)")
    p.add_argument("--hotel", help="酒店名称")
    p.add_argument("--checkin", help="入住日期 YYYY-MM-DD")
    p.add_argument("--checkout", help="离店日期 YYYY-MM-DD")
    p.add_argument("--platforms", nargs="+", help="目标平台")
    p.add_argument("--login", action="store_true", help="引导登录各平台")
    p.add_argument("--monitor", action="store_true", help="持续监控模式")
    p.add_argument("--interval", default="6h", help="监控间隔")
    p.add_argument("--no-llm", action="store_true", help="禁用 LLM")
    p.add_argument("--output", help="输出 JSON 路径")
    p.add_argument("--no-notify", action="store_true", help="禁用通知")
    return p.parse_args()


def parse_interval(interval: str) -> int:
    """解析监控间隔为秒数"""
    import re
    m = re.match(r"(\d+)\s*(m|min|h|hour|d|day)", interval.lower())
    if not m:
        raise ValueError(f"无法解析间隔: {interval}")
    val = int(m.group(1))
    unit = m.group(2)
    if unit in ("m", "min"):
        return val * 60
    elif unit in ("h", "hour"):
        return val * 3600
    else:
        return val * 86400


def scrape_platforms(browser, hotel_info, checkin, checkout, platforms, use_llm=True):
    """采集所有平台"""
    rooms_by_platform = {}
    llm_parser = LLMParser() if use_llm else None

    for plat in platforms:
        name = PLATFORM_NAMES.get(plat, plat)
        console.print(f"\n🔍 [{name}] 采集中...")

        try:
            scraper = get_scraper(plat, browser)
            result = scraper.scrape(
                hotel_info.ctrip_id, checkin, checkout, hotel_info.name
            )

            if not result.success:
                console.print(f"  ⚠️ [{name}] {result.error}")
                continue

            rooms = result.rooms

            # LLM 解析原始数据
            if use_llm and rooms and "page_text" in getattr(rooms[0], 'raw_data', {}):
                raw_text = rooms[0].raw_data["page_text"]
                rooms = llm_parser.extract_rooms(raw_text, plat)

            if rooms:
                rooms_by_platform[plat] = rooms
                console.print(f"  ✅ [{name}] {len(rooms)} 个房型")
            else:
                console.print(f"  ⚠️ [{name}] 无房型数据")

        except Exception as e:
            console.print(f"  ❌ [{name}] {e}")

    return rooms_by_platform


def display(comparison):
    """显示比价结果"""
    console.print("\n" + "─" * 50)
    console.print(Panel.fit(
        f"[bold cyan]{comparison['hotel']}[/]\n{comparison['summary']}",
        title="🏨 比价结果",
    ))

    rooms = comparison.get("rooms", [])
    if rooms:
        table = Table(show_header=True, header_style="bold")
        table.add_column("房型", style="cyan")
        table.add_column("最低价", style="green", justify="right")
        table.add_column("平台", style="yellow")
        table.add_column("全平台价格", style="dim")
        for r in rooms:
            all_p = " | ".join(
                f"{p}: ¥{v:.0f}" for p, v in r.get("all_prices", {}).items()
            )
            table.add_row(
                r["room_name"],
                f"¥{r['cheapest_price']:.0f}",
                r["cheapest_platform"],
                all_p,
            )
        console.print(table)

    alerts = comparison.get("alerts", [])
    if alerts:
        console.print("\n🚨 [bold red]价格预警[/]")
        for a in alerts:
            console.print(f"  {a['level']} {a['room']}: ¥{a['current_price']} "
                          f"(均价¥{a['avg_price']:.0f}, 降{a['drop_percent']})")

    console.print("─" * 50)


def main():
    args = parse_args()

    # === Web 模式 ===
    if args.web:
        from src.web.app import start_web
        start_web(port=args.port)
        return

    # === CLI 模式 ===
    if not args.hotel or not args.checkin or not args.checkout:
        console.print("[red]CLI 模式需要 --hotel --checkin --checkout 参数[/]")
        console.print("[dim]或使用 python main.py --web 打开可视化界面[/]")
        sys.exit(1)

    checkin = date.fromisoformat(args.checkin)
    checkout = date.fromisoformat(args.checkout)
    platforms = args.platforms or list(PLATFORM_SCRAPERS.keys())

    if checkin >= checkout:
        console.print("[red]离店日期需晚于入住日期[/red]")
        sys.exit(1)

    console.print(f"""
╔══════════════════════════════════════╗
║  🏨 酒店多平台比价工具 v2.0        ║
║  AutoBrowser + DeepSeek LLM         ║
╚══════════════════════════════════════╝
🏨 {args.hotel}  📅 {checkin} → {checkout}  🎯 {', '.join(platforms)}
""")

    # === 阶段 1: 自动搜索酒店 ===
    console.print("[bold]📡 搜索酒店...[/]")
    hotel_info = search_hotel(args.hotel)
    if not hotel_info:
        console.print(f"[red]未找到酒店 '{args.hotel}'，请用 --hotel-id 指定[/red]")
        sys.exit(1)
    console.print(f"  ✅ 找到: {hotel_info.name} (携程ID: {hotel_info.ctrip_id})")

    # === 阶段 2: 自动管理浏览器 ===
    console.print("\n[bold]🌐 启动浏览器...[/]")
    browser = AutoBrowser()

    try:
        browser.connect()

        if args.login:
            browser.guide_login()

        # 检测登录态
        for plat in platforms:
            if browser.check_login_status(plat):
                console.print(f"  ✅ {PLATFORM_NAMES.get(plat, plat)} 已登录")
            else:
                console.print(f"  ⚠️ {PLATFORM_NAMES.get(plat, plat)} 可能需要登录")

        # === 阶段 3: 采集 + 比价 ===
        def run_once():
            console.print("\n[bold]📡 采集数据...[/]")
            rooms = scrape_platforms(
                browser, hotel_info, checkin, checkout, platforms,
                use_llm=not args.no_llm,
            )

            if not rooms:
                console.print("[red]所有平台采集失败[/red]")
                return

            console.print("\n[bold]🔬 比价分析...[/]")
            comparator = PriceComparator()
            result = comparator.compare(rooms, hotel_info.name)
            display(result)

            # 保存
            out = args.output or f"{hotel_info.ctrip_id}_{args.checkin}.json"
            Path(out).write_text(
                json.dumps(result, ensure_ascii=False, indent=2, default=str)
            )

            # 飞书通知
            if not args.no_notify:
                notifier = FeishuNotifier()
                msg = notifier.send_alert(result)
                if isinstance(msg, str) and (result.get("alerts")):
                    console.print(f"\n📤 飞书通知: {msg[:100]}...")

        if args.monitor:
            interval_sec = parse_interval(args.interval)
            console.print(f"\n🔄 监控模式启动（间隔 {args.interval}）")
            while True:
                run_once()
                console.print(f"\n⏳ 等待 {args.interval}...")
                time.sleep(interval_sec)
        else:
            run_once()

    except KeyboardInterrupt:
        console.print("\n👋 用户中断")
    finally:
        browser._cleanup()

    console.print("\n[green]✅ 完成[/green]")


if __name__ == "__main__":
    main()
