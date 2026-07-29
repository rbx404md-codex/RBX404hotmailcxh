import threading
import time
from PROXY.proxy import init_proxies


class InboxStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.checked = 0
        self.hits = 0
        self.bad = 0
        self.errors = 0
        self.retries = 0
        self.proxy_err = 0
        # Category counters
        self.psn = 0
        self.games = 0
        self.social = 0
        self.apps = 0
        self.payment = 0
        self.proxy_svc = 0
        self.streaming = 0
        # Social link counters
        self.tiktok_links = 0
        self.instagram_links = 0
        self.facebook_links = 0
        self.twitter_links = 0
        # Result lists
        self.hits_list: list = []   # list of result dicts (status=hit)
        self.bad_list: list = []    # list of "email:pass"
        self.error_list: list = []  # list of "email:pass"


class InboxCheckerSession:
    def __init__(self, user_id: int, combos: list):
        """
        combos: list of (email, password) tuples
        """
        self.user_id = user_id
        self.combos = combos
        self.stats = InboxStats()
        self.stats.total = len(combos)
        self.proxies = init_proxies()
        self.stop_event = threading.Event()
        self.finished = False
        self.started = time.time()
        self.msg_id = None
        self.chat_id = None
        self.executor = None
        self.futures = []
