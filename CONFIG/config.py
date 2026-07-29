import os
import time

# Base directory = folder where config.py lives (i.e. the bot root)
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _p(*parts):
    """Build an absolute path relative to the bot root."""
    return os.path.join(_BASE, *parts)

BOT_TOKEN = "8882043243:AAF8tMF5iRahflh-G6Hj4Hh42IfTs3OFTqI" #Bot father token
ADMIN_ID = 7294948308 #YOU ID HERE

# ── Thread counts (edit these to tune performance) ──────────────────────────
MASTER_THREADS       = 30    # M-Hotmail checker threads
INBOXER_THREADS      = 30    # Inboxer checker threads
COOKIES_THREADS      = 30    # Cookie checker threads
DEFAULT_THREADS      = MASTER_THREADS   # alias used in legacy code

# ── File / DB limits ─────────────────────────────────────────────────────────
MAX_LINES            = 10000
MAX_FILE_SIZE_MB     = 20

# ── Paths (always absolute, works on Termux, Ubuntu, any VPS) ───────────────
DB_FILE              = _p("DB", "bot_database.json")
FILES_DIR            = _p("FILES")
PROXIES_FILE         = _p("FILES", "proxy.txt")
ADMIN_PROXIES_FILE   = _p("FILES", "admin_proxies.txt")

# ── Webshare rotating proxy credentials ──────────────────────────────────────
WEBSHARE_HOST        = "p.webshare.io"
WEBSHARE_PORT        = 80
WEBSHARE_USER        = "bicmkxza-rotate"
WEBSHARE_PASS        = "6a643oynf17r"

# Webshare country-specific variants (appended after main)
WEBSHARE_COUNTRIES   = ["us", "gb", "de", "fr", "nl", "ca", "au"]

# ── Proxy refresh timing ─────────────────────────────────────────────────────
PROXY_BATCH_INTERVAL      = 1200  # 20 minutes between each batch
PROXY_CLEAR_AFTER_BATCHES = 1     # clear proxy.txt and fetch fresh every 20 minutes
PROXY_REFRESH_INTERVAL    = 360   # legacy — kept for compat

# ── Backup ───────────────────────────────────────────────────────────────────
BACKUP_INTERVAL      = 86400   # 24 h

# ── Built-in fallback proxies ────────────────────────────────────────────────
BUILTIN_PROXIES = [
    "895803e88e09d774.fjt.na.novada.pro:7777:novada194rkD_76nJGA-zone-res:lXm7rbh22AjU",
    "87.248.148.1:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "87.248.148.166:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "31.193.191.114:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "31.193.191.115:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "31.193.191.116:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "193.36.187.169:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "193.36.187.170:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "193.36.187.171:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
    "87.248.148.2:3128:sub_crypto_1t4by0jb4g9i6pkhqvtmzyhv:stat382",
]

MAX_RETRIES = 4
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

USER_AGENTS = [
    'Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
]
