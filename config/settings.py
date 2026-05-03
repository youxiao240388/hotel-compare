"""
配置中心 - 所有可配置项

通过环境变量或 config.yaml 覆盖默认值。
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# ====== 浏览器配置 ======
BROWSER_EXECUTABLE = os.getenv("CHROME_PATH", "")  # 留空自动查找
BROWSER_PORT = int(os.getenv("BROWSER_PORT", "9222"))
BROWSER_USER_DATA = os.getenv(
    "BROWSER_USER_DATA",
    str(Path.home() / ".hotel-compare" / "chrome-profile"),
)

# ====== LLM 配置 ======
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# ====== 向量库配置 ======
CHROMA_PERSIST_DIR = str(PROJECT_ROOT / "data" / "embeddings")
ROOM_SIMILARITY_THRESHOLD = float(os.getenv("ROOM_SIMILARITY_THRESHOLD", "0.50"))  # n-gram 模式阈值较宽松
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
)

# ====== 采集配置 ======
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "1.5"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "4.0"))
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
CONSECUTIVE_FAILURE_LIMIT = int(os.getenv("CONSECUTIVE_FAILURE_LIMIT", "5"))

# ====== 比价配置 ======
PRICE_ALERT_THRESHOLD = float(os.getenv("PRICE_ALERT_THRESHOLD", "0.30"))  # 低于历史均价30%即为Bug价
TREND_LOOKBACK_DAYS = int(os.getenv("TREND_LOOKBACK_DAYS", "30"))

# ====== 飞书通知 ======
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_USER_ID = os.getenv("FEISHU_USER_ID", "ou_9f3dc85ba24de8c9d2bee97266cfc257")

# ====== 目标平台 ======
PLATFORMS = ["ctrip", "meituan", "fliggy", "booking"]
