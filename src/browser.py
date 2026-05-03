"""
浏览器自动管理器 - Chrome 生命周期全自动

功能：
1. 自动检测 Chrome 安装位置
2. 自动启动 Chrome（debug mode）+ 持久化用户目录
3. 检测已有实例并复用
4. 平台登录态保持（一次登录，长期有效）
5. 退出时优雅关闭
"""
import atexit
import logging
import os
import random
import shutil
import signal
import subprocess
import time
from pathlib import Path

from DrissionPage import ChromiumPage, ChromiumOptions

from config.settings import (
    BROWSER_PORT,
    BROWSER_USER_DATA,
    PAGE_TIMEOUT,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)

logger = logging.getLogger(__name__)

# 常见 Chrome 安装路径
_CHROME_PATHS = [
    # Linux
    "google-chrome", "google-chrome-stable", "chromium-browser", "chromium",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser", "/usr/bin/chromium", "/snap/bin/chromium",
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    # Windows
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
]

# 登录引导页面
_LOGIN_PAGES = {
    "ctrip": "https://passport.ctrip.com/user/login",
    "meituan": "https://i.meituan.com/awp/h5/hotel/login",
    "fliggy": "https://login.taobao.com/member/login.jhtml",
    "qunar": "https://user.qunar.com/passport/login.jsp",
}


class AutoBrowser:
    """全自动 Chrome 浏览器管理"""

    def __init__(self):
        self.page: ChromiumPage | None = None
        self._chrome_process: subprocess.Popen | None = None
        self._chrome_path: str = ""

        # 注册退出清理（仅主线程）
        import threading
        if threading.current_thread() is threading.main_thread():
            atexit.register(self._cleanup)
            try:
                signal.signal(signal.SIGTERM, lambda *_: self._cleanup())
                signal.signal(signal.SIGINT, lambda *_: self._cleanup())
            except ValueError:
                pass  # 非主线程会抛异常

    def _find_chrome(self) -> str:
        """自动查找 Chrome 可执行文件"""
        import os as _os
        env_path = _os.getenv("CHROME_PATH", "")
        if env_path and Path(env_path).exists():
            return env_path

        # Windows: 检查 LOCALAPPDATA
        local_appdata = _os.getenv("LOCALAPPDATA", "")
        if local_appdata:
            win_path = Path(local_appdata) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if win_path.exists():
                return str(win_path)

        for path in _CHROME_PATHS:
            if shutil.which(path):
                return path

        raise RuntimeError(
            "未找到 Chrome/Chromium。请安装或设置 CHROME_PATH 环境变量。\n"
            "下载: https://www.google.com/chrome/"
        )

    def _is_chrome_running(self) -> bool:
        """检测 Chrome debug port 是否已就绪"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", BROWSER_PORT))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _launch_chrome(self):
        """启动 Chrome 并开启 debug 端口"""
        self._chrome_path = self._find_chrome()
        Path(BROWSER_USER_DATA).mkdir(parents=True, exist_ok=True)

        cmd = [
            self._chrome_path,
            f"--remote-debugging-port={BROWSER_PORT}",
            f"--user-data-dir={BROWSER_USER_DATA}",
            "--headless",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
            "--remote-allow-origins=*",
        ]

        logger.info(f"🚀 启动 Chrome: {self._chrome_path}")
        kwargs = dict(
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Windows 不支持 start_new_session
        import platform
        if platform.system() != "Windows":
            kwargs["start_new_session"] = True
        self._chrome_process = subprocess.Popen(cmd, **kwargs)

        # 等待 debug port 就绪
        for i in range(15):
            time.sleep(1)
            if self._is_chrome_running():
                logger.info("✅ Chrome debug port 就绪")
                return
        raise RuntimeError("Chrome 启动超时（15秒）")

    def connect(self) -> ChromiumPage:
        """
        自动连接 Chrome

        优先级：
        1. 已有 Chrome 实例 → 直接接管
        2. 无实例 → 自动启动新实例
        3. 首次启动 → 打开各平台登录页引导登录
        """
        chrome_path = self._find_chrome()
        
        if self._is_chrome_running():
            logger.info("♻️  检测到已有 Chrome 实例，直接接管")
        else:
            logger.info("🆕 无 Chrome 实例，自动启动...")
        
        try:
            co = ChromiumOptions()
            co.set_browser_path(chrome_path)
            co.set_local_port(BROWSER_PORT)
            co.set_user_data_path(BROWSER_USER_DATA)
            co.set_argument("--headless")  # 旧版 headless，兼容性更好
            co.set_argument("--no-first-run")
            co.set_argument("--no-default-browser-check")
            co.set_argument("--disable-background-networking")
            co.set_argument("--disable-sync")
            co.set_argument("--disable-blink-features=AutomationControlled")
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-dev-shm-usage")
            co.set_argument("--disable-gpu")
            co.set_argument("--window-size=1280,800")
            co.set_argument("--remote-allow-origins=*")
            
            self.page = ChromiumPage(addr_or_opts=co)
            logger.info(f"✅ 已连接到浏览器 (port {BROWSER_PORT})")
        except Exception as e:
            logger.error(f"连接浏览器失败: {e}")
            raise

        return self.page

    def guide_login(self, platform: str = None):
        """
        引导用户登录各平台

        自动打开登录页，提示用户完成登录。
        用户目录持久化，登录一次即可长期使用。
        """
        if not self.page:
            self.connect()

        if platform:
            pages = {platform: _LOGIN_PAGES.get(platform, "")}
        else:
            pages = _LOGIN_PAGES

        logger.info("=" * 50)
        logger.info("🔐 请在浏览器中完成各平台登录（仅首次需要）")
        logger.info("   登录后状态将持久保留，后续全自动运行")
        logger.info("=" * 50)

        tabs = []
        for plat, url in pages.items():
            if not url:
                continue
            try:
                tab = self.page.new_tab(url)
                tabs.append((plat, tab))
                logger.info(f"  📄 已打开 {plat} 登录页")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"  打开 {plat} 失败: {e}")

        logger.info("\n⏳ 请在浏览器中完成登录后按回车继续...")
        input()

        # 关闭登录标签页
        for plat, tab in tabs:
            try:
                tab.close()
            except Exception:
                pass

        logger.info("✅ 登录完成，开始自动化监控")

    def check_login_status(self, platform: str) -> bool:
        """
        检测平台登录态是否有效

        简单方法：访问平台首页，检查是否跳转到登录页
        """
        if not self.page:
            return False

        check_urls = {
            "ctrip": "https://hotels.ctrip.com/",
            "meituan": "https://i.meituan.com/",
            "fliggy": "https://www.fliggy.com/",
        }

        url = check_urls.get(platform)
        if not url:
            return True  # 未知平台默认认为已登录

        try:
            tab = self.page.new_tab(url)
            time.sleep(3)
            current_url = tab.url.lower()
            tab.close()

            # 如果 URL 包含 login/passport，说明未登录
            no_login_indicators = ["login", "passport", "signin", "auth"]
            return not any(ind in current_url for ind in no_login_indicators)
        except Exception:
            return False

    def is_blocked(self) -> bool:
        """检测是否被反爬封锁"""
        if not self.page:
            return True
        try:
            html = self.page.html.lower()
            blocks = [
                "验证码", "captcha", "滑块", "verify", "security check",
                "人机验证", "访问过于频繁", "403 forbidden",
            ]
            return any(b in html for b in blocks)
        except Exception:
            return False

    def human_delay(self, min_s: float = None, max_s: float = None):
        """模拟人类操作的随机延迟（正态分布）"""
        min_s = min_s or REQUEST_DELAY_MIN
        max_s = max_s or REQUEST_DELAY_MAX
        delay = random.gauss((min_s + max_s) / 2, (max_s - min_s) / 4)
        delay = max(min_s, min(max_s, delay))
        time.sleep(delay)

    def human_scroll(self):
        """模拟人类浏览滚动"""
        if not self.page:
            return
        try:
            for _ in range(random.randint(1, 3)):
                self.page.scroll.down(random.randint(200, 800))
                time.sleep(random.uniform(0.3, 1.0))
        except Exception:
            pass

    def _cleanup(self):
        """清理资源（不杀 Chrome，保留给用户）"""
        if self.page:
            try:
                self.page.quit()
            except Exception:
                pass
            self.page = None

        # 注意：不杀 Chrome 进程，保留给用户继续使用
        logger.debug("浏览器连接已释放（Chrome 进程保留）")

    def kill_chrome(self):
        """强制关闭 Chrome（仅 Docker/无头环境）"""
        if self._chrome_process:
            try:
                self._chrome_process.terminate()
                self._chrome_process.wait(timeout=5)
            except Exception:
                try:
                    self._chrome_process.kill()
                except Exception:
                    pass
        self._chrome_process = None
