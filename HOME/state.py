import threading

bot = None
active_checks = {}
active_checks_lock = threading.Lock()
BOT_START_TIME = 0.0

# Global proxy pool - updated when proxies refresh
global_proxy_pool = []
global_proxy_pool_lock = threading.Lock()
