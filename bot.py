#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║          𝐇𝐨𝐭𝐦𝐚𝐢𝐥 𝐌𝐚𝐬𝐭𝐞𝐫 𝐂𝐡𝐞𝐜𝐤𝐞𝐫 𝐁𝐨𝐭                    ║
║          𝐃𝐞𝐯: @RBX404                                    ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import time
import random
import threading
import telebot

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.columns import Columns
    _rich = True
except ImportError:
    import sys
    os.system(f"{sys.executable} -m pip install rich -q")
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.columns import Columns
    _rich = True

console = Console()

from CONFIG.config import (
    BOT_TOKEN, ADMIN_ID, PROXIES_FILE, FILES_DIR,
    PROXY_BATCH_INTERVAL, PROXY_CLEAR_AFTER_BATCHES, BACKUP_INTERVAL,
    BUILTIN_PROXIES,
)
from proxy_hunter import scrape_all, find_live_proxies
from HOME import state
from HOME.helpers import bold, italic, mono, E_ROBOT, E_GREEN, E_CLOCK, E_GLOBE, E_USER, E_GEAR
from HOME.logger import log as file_log
from DATABASE.database import load_db
from PROXY.proxy import init_proxies, load_proxies_from_file
from PROXY.fetcher import fetch_urban_vpn_proxies

from COMMANDS.START import start
from COMMANDS.CHECKER import handlers
from COMMANDS.CHECKER import cookie_handlers
from COMMANDS.CHECKER import inbox_handlers
from COMMANDS.ADMIN import admin
from COMMANDS.ADMIN.admin import send_backup


BANNER = """[bold red]
  ██╗  ██╗ ██████╗ ████████╗███╗   ███╗ █████╗ ██╗██╗
  ██║  ██║██╔═══██╗╚══██╔══╝████╗ ████║██╔══██╗██║██║
  ███████║██║   ██║   ██║   ██╔████╔██║███████║██║██║
  ██╔══██║██║   ██║   ██║   ██║╚██╔╝██║██╔══██║██║██║
  ██║  ██║╚██████╔╝   ██║   ██║ ╚═╝ ██║██║  ██║██║███████╗
  ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝[/bold red]
[bold magenta]  ╔══════════════════════════════════════════════════════╗
  ║    🔥 Blackout Zone CHECKER BOT  •  Dev: @RBX404    ║
  ╚══════════════════════════════════════════════════════╝[/bold magenta]"""


def _log(emoji, color, label, msg):
    ts = time.strftime("%H:%M:%S")
    console.print(f"[dim]{ts}[/dim]  [{color}]{emoji} {label}[/{color}]  {msg}")
    # Also write to file logger
    clean_msg = msg.replace("[/bold]", "").replace("[bold green]", "").replace("[/bold green]", "").replace("[bold cyan]", "").replace("[/cyan]", "").replace("[cyan]", "").replace("[yellow]", "").replace("[/yellow]", "").replace("[bold]", "").replace("[/bold]", "").replace("[dim]", "").replace("[/dim]", "").replace("[red]", "").replace("[/red]", "").replace("[green]", "").replace("[/green]", "").replace("[magenta]", "").replace("[/magenta]", "")
    file_log(f"{emoji} {label}: {clean_msg}")


# ── Proxy hunter — hunt a live free proxy to auth Urban VPN ──────────────────

def _hunt_live_proxy() -> str:
    """Scrape public proxies and return the first live one found."""
    _log("🔍", "bold yellow", "PROXY HUNT", "Scraping public proxies...")
    raw = scrape_all()
    if not raw:
        _log("⚠️ ", "yellow", "PROXY HUNT", "No proxies scraped.")
        return None
    _log("⚡", "bold yellow", "PROXY HUNT",
         f"Checking {len(raw):,} proxies (300 threads) — stops at 4 live...")
    live_list = find_live_proxies(raw, max_live=4)
    if live_list:
        live = live_list[0]
        _log("✅", "bold green", "PROXY HUNT", f"Live proxy found: [bold cyan]{live}[/bold cyan] ({len(live_list)} total live)")
    else:
        _log("⚠️ ", "yellow", "PROXY HUNT", "No live proxy found.")
    return live


def _proxy_str_to_url(proxy_str: str):
    """Convert ip:port:user:pass to proxy URL string, or None."""
    if not proxy_str:
        return None
    try:
        parts = proxy_str.strip().split(":")
        if len(parts) == 4:
            h, po, u, pw = parts
            return f"http://{u}:{pw}@{h}:{po}"
        if "@" in proxy_str:
            return f"http://{proxy_str}" if not proxy_str.startswith("http") else proxy_str
        if len(parts) == 2:
            return f"http://{proxy_str}"
    except Exception:
        pass
    return None


# ── Urban VPN fetch with live Rich progress ───────────────────────────────────

def _do_proxy_fetch(reason="AUTO", batch_num=0):
    """
    Fetch Urban VPN proxies using a live hunted proxy as auth.
    - STARTUP   : clear FILES/proxy.txt, then fetch
    - Clear batch (every PROXY_CLEAR_AFTER_BATCHES): clear, then fetch
    - Normal batch: APPEND to existing (don't remove old proxies)
    Hunts a fresh live proxy each time before fetching.
    """
    os.makedirs(FILES_DIR, exist_ok=True)

    is_clear_batch = (batch_num % PROXY_CLEAR_AFTER_BATCHES == 0) and batch_num > 0

    # ── Decide whether to clear ───────────────────────────────────────────
    if reason == "STARTUP":
        _log("🗑️ ", "yellow", "PROXY", "Startup — clearing FILES/proxy.txt...")
        open(PROXIES_FILE, "w").close()

    elif is_clear_batch:
        _log("🗑️ ", "yellow", f"PROXY [B{batch_num}]",
             f"Batch {batch_num} → every {PROXY_CLEAR_AFTER_BATCHES} batches — clearing proxy file...")
        open(PROXIES_FILE, "w").close()

    action = "CLEAR+FETCH" if (reason == "STARTUP" or is_clear_batch) else f"APPEND [B{batch_num}]"

    # ── Hunt a live proxy to use as auth ─────────────────────────────────
    auth_proxy = _hunt_live_proxy()
    if auth_proxy:
        proxy_label = f"[bold cyan](auth via ProxyHunter: {auth_proxy})[/bold cyan]"
    else:
        auth_proxy = None
        proxy_label = "[yellow](no live proxy found — direct IP)[/yellow]"

    _log("⚡", "bold yellow", f"PROXY [{action}]",
         f"Urban VPN fetch — 50 threads... {proxy_label}")

    # ── Rich live progress ────────────────────────────────────────────────
    data = {
        "done": 0, "ok": 0, "fail": 0, "total": 0,
        "status": "Connecting...", "start": time.time()
    }

    def cb(step, *args):
        if step == "status":
            data["status"] = args[0]
        elif step == "total":
            data["total"] = args[0]
        elif step == "progress":
            data["done"], _, data["ok"], data["fail"] = args
        elif step == "error":
            data["status"] = f"ERR: {args[0][:60]}"

    def make_panel():
        elapsed = time.time() - data["start"]
        done, total, ok, fail = data["done"], data["total"], data["ok"], data["fail"]
        pct = (done / total * 100) if total else 0
        speed = ok / elapsed if elapsed > 0 else 0
        bar_len = 28
        filled = int(bar_len * done / total) if total else 0
        bar = "[green]" + "█" * filled + "[/green][dim]" + "░" * (bar_len - filled) + "[/dim]"

        t = Table(box=None, show_header=False, padding=(0, 1))
        t.add_column("k", style="bold cyan", no_wrap=True, width=13)
        t.add_column("v", style="white")
        t.add_row("📡 Status",   f"[yellow]{data['status']}[/yellow]")
        t.add_row("📊 Progress", f"{bar} [bold]{done}[/bold]/[cyan]{total}[/cyan] [magenta]({pct:.1f}%)[/magenta]")
        t.add_row("✅ Fetched",  f"[bold green]{ok}[/bold green]")
        t.add_row("❌ Failed",   f"[red]{fail}[/red]")
        t.add_row("⚡ Speed",    f"[yellow]{speed:.1f}[/yellow] prx/s")
        t.add_row("⏱  Elapsed",  f"[dim]{elapsed:.1f}s[/dim]")
        src_lbl = f"ProxyHunter ({auth_proxy}) → Urban VPN" if auth_proxy else "Direct → Urban VPN"
        t.add_row("🌐 Auth",     f"[cyan]{src_lbl}[/cyan]")
        return Panel(
            t,
            title=f"[bold magenta]🔄 PROXY FETCH [{action}] #{batch_num}[/bold magenta]",
            border_style="magenta", expand=False
        )

    result_holder = [None]
    done_event = threading.Event()
    _current_proxy = [auth_proxy]   # mutable so run_fetch can update it

    MAX_RETRIES = 100

    def run_fetch():
        for attempt in range(MAX_RETRIES):
            cur = _current_proxy[0]
            data.update({"done": 0, "ok": 0, "fail": 0, "total": 0,
                         "status": "Connecting...", "start": time.time()})
            proxies = fetch_urban_vpn_proxies(cb, auth_proxy=cur)

            # If we got any proxies — done
            if proxies:
                result_holder[0] = proxies
                done_event.set()
                return

            # If auth succeeded (server list was fetched) but credentials all failed
            # — don't retry, just finish with empty result and wait for next batch
            if data["total"] > 0:
                data["status"] = f"Auth OK but 0 credentials — moving to next batch"
                done_event.set()
                return

            # Auth itself failed — only then retry with a new proxy
            err = data["status"]
            needs_new_proxy = any(x in err for x in ("429", "Too Many", "403", "400", "Forbidden"))
            last_attempt = (attempt == MAX_RETRIES - 1)
            if not last_attempt:
                if needs_new_proxy:
                    code = "429" if "429" in err or "Too Many" in err else "403" if "403" in err else "400"
                    data["status"] = f"{code} blocked — hunting new proxy (attempt {attempt+2}/{MAX_RETRIES})..."
                    # Wait 15s for 429 rate limit to cool down
                    if code == "429":
                        data["status"] = f"429 rate limit — waiting 15s cooldown..."
                        time.sleep(15)
                    new_proxy = _hunt_live_proxy()
                    _current_proxy[0] = new_proxy
                    lbl = new_proxy if new_proxy else "direct IP"
                    data["status"] = f"Retrying with {lbl}..."
                else:
                    data["status"] = f"Auth failed, retrying... (attempt {attempt+2}/{MAX_RETRIES})"
                    time.sleep(3)
            else:
                data["status"] = f"All {MAX_RETRIES} auth attempts failed: {err}"
        done_event.set()

    threading.Thread(target=run_fetch, daemon=True).start()

    try:
        with Live(make_panel(), console=console, refresh_per_second=4, transient=False) as live:
            while not done_event.is_set():
                live.update(make_panel())
                time.sleep(0.25)
            live.update(make_panel())
    except Exception:
        done_event.wait()

    proxies = result_holder[0] or []
    elapsed = time.time() - data["start"]

    if proxies:
        # Read existing lines to avoid exact duplicates when appending
        existing = set()
        if os.path.exists(PROXIES_FILE):
            try:
                with open(PROXIES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    for ln in f:
                        ln = ln.strip()
                        if ln:
                            existing.add(ln)
            except Exception:
                pass

        new_lines = []
        for p in proxies:
            entry = f"{p['ip']}:{p['port']}:{p['user']}:{p['pass']}"
            if entry not in existing:
                new_lines.append(entry)

        with open(PROXIES_FILE, "a", encoding="utf-8") as f:
            for ln in new_lines:
                f.write(ln + "\n")

        # Update global proxy pool for active checks
        from PROXY.proxy import update_global_proxy_pool
        pool_size = update_global_proxy_pool()

        _log("✅", "bold green", f"PROXY [{action}]",
             f"[bold green]{len(new_lines)}[/bold green] new / "
             f"[cyan]{len(proxies)}[/cyan] total Urban VPN proxies  •  "
             f"servers: [cyan]{data['total']}[/cyan]  •  "
             f"time: [yellow]{elapsed:.1f}s[/yellow]  •  "
             f"speed: [magenta]{len(proxies)/elapsed:.1f}[/magenta] prx/s  •  "
             f"pool: [green]{pool_size}[/green]")

        # Refresh proxy rotators in active checks
        with state.active_checks_lock:
            for uid, cs in state.active_checks.items():
                if not str(uid).startswith(("pending_", "file_")):
                    try:
                        if hasattr(cs, 'pxr') and cs.pxr:
                            refreshed = cs.pxr.refresh_from_global_pool()
                            if refreshed:
                                _log("🔄", "cyan", "PROXY", f"Refreshed proxy pool for user {uid}")
                    except Exception:
                        pass

        # Telegram notification + full backup for auto batches (not startup)
        if reason != "STARTUP":
            def _notify_done():
                try:
                    cleared_note = "🗑️ Cleared old list first\n" if is_clear_batch else "➕ Appended to existing\n"
                    state.bot.send_message(
                        ADMIN_ID,
                        f"✅ <b>Proxy Batch #{batch_num} Done</b>\n"
                        f"<blockquote>🌐 Source: Urban VPN (auth via {'ProxyHunter' if auth_proxy else 'own IP'})\n"
                        f"📦 New: <code>{len(new_lines)}</code> / Total fetched: <code>{len(proxies)}</code>\n"
                        f"{cleared_note}"
                        f"⏱️ Time: <code>{elapsed:.1f}s</code>\n"
                        f"📦 Sending full bot backup...</blockquote>",
                        parse_mode="HTML"
                    )

                    # Send full bot backup
                    from COMMANDS.ADMIN.admin import send_full_bot_backup
                    send_full_bot_backup(ADMIN_ID, f"Auto proxy refresh - Batch #{batch_num}")

                    # Notify active users that proxies refreshed
                    with state.active_checks_lock:
                        active_user_ids = [uid for uid in state.active_checks.keys()
                                         if not str(uid).startswith(("pending_", "file_"))]

                    for uid in active_user_ids:
                        try:
                            state.bot.send_message(
                                uid,
                                f"🔄 <b>Proxies Refreshed!</b>\n"
                                f"<blockquote>🌐 New proxies loaded: <code>{len(new_lines)}</code>\n"
                                f"✅ Your check continues from where it was\n"
                                f"⚡ Now using fresh proxies</blockquote>",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass

                except Exception:
                    pass
            threading.Thread(target=_notify_done, daemon=True).start()
        return True
    else:
        _log("⚠️ ", "yellow", f"PROXY [{action}]",
             "No proxies returned — keeping existing list")
        return False


# ── Proxy refresh loop ────────────────────────────────────────────────────────

proxy_fetch_state = {
    "last_run": 0,
    "next_run": 0,
    "batch_num": 0
}

def auto_proxy_fetch_loop():
    """
    Proxy fetch schedule:
      Startup  → clear FILES/proxy.txt → hunt live proxy → fetch Urban VPN
      Batch 1  → +20 min → CLEAR + fetch fresh + send full bot backup
      ...repeat (retries indefinitely until success)

    Active checks continue running during proxy refresh - they seamlessly
    pick up new proxies from the refreshed pool.
    """
    time.sleep(5)

    # Initial fetch on startup - retry until success
    proxy_fetch_state["next_run"] = time.time()
    while True:
        success = _do_proxy_fetch("STARTUP", batch_num=0)
        if success:
            break
        _log("⏳", "yellow", "PROXY", "Startup fetch failed, retrying in 60s...")
        time.sleep(60)

    proxy_fetch_state["last_run"] = time.time()
    proxy_fetch_state["next_run"] = time.time() + PROXY_BATCH_INTERVAL
    proxy_fetch_state["batch_num"] = 1

    while True:
        time.sleep(PROXY_BATCH_INTERVAL)   # 20 minutes

        # Auto refresh - retry until success
        # Active checks keep running - they'll use new proxies automatically
        while True:
            success = _do_proxy_fetch("AUTO", batch_num=proxy_fetch_state["batch_num"])
            if success:
                break
            _log("⏳", "yellow", "PROXY", f"Batch {proxy_fetch_state['batch_num']} failed, retrying in 60s...")
            time.sleep(60)

        proxy_fetch_state["last_run"] = time.time()
        proxy_fetch_state["next_run"] = time.time() + PROXY_BATCH_INTERVAL
        proxy_fetch_state["batch_num"] += 1



# ── Backup loop ───────────────────────────────────────────────────────────────

def auto_backup_loop():
    time.sleep(8)
    send_backup(ADMIN_ID, "Bot started - initial backup")
    while True:
        time.sleep(BACKUP_INTERVAL)
        send_backup(ADMIN_ID, "Scheduled 24h backup")


# ── Startup panel ─────────────────────────────────────────────────────────────

def print_startup_panel(db, proxy_count):
    users    = len(db.get("users", {}))
    banned   = len(db.get("banned", {}))
    approved = len(db.get("approved", {}))
    g        = db.get("global_stats", {})

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("key", style="bold cyan", no_wrap=True)
    table.add_column("val", style="bold white")

    table.add_row("🟢 Status",    "[bold green]ONLINE[/bold green]")
    table.add_row("🕐 Started",   time.strftime("%Y-%m-%d  %H:%M:%S"))
    table.add_row("👤 Users",     str(users))
    table.add_row("🚫 Banned",    str(banned))
    table.add_row("✅ Approved",  str(approved))
    table.add_row("🌐 Proxies",   f"[yellow]{proxy_count}[/yellow]")
    table.add_row("📊 Checked",   str(g.get("total_checked", 0)))
    table.add_row("🔥 Hits",      str(g.get("total_hits", 0)))

    console.print(Panel(table,
        title="[bold magenta]⚙️  BOT STATUS[/bold magenta]",
        border_style="magenta", expand=False))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    os.makedirs(FILES_DIR, exist_ok=True)

    console.print(BANNER)

    _log("⚙️ ", "cyan", "INIT", "Loading database...")
    db = load_db()

    _log("⚙️ ", "cyan", "INIT", "Loading proxies from FILES/proxy.txt...")
    proxies = init_proxies()

    # Initialize global proxy pool
    from PROXY.proxy import update_global_proxy_pool
    update_global_proxy_pool()
    _log("⚙️ ", "cyan", "INIT", f"Global proxy pool initialized with {len(proxies)} proxies")

    _log("⚙️ ", "cyan", "INIT", "Connecting to Telegram...")
    state.bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    state.BOT_START_TIME = time.time()

    _log("⚙️ ", "cyan", "INIT", "Registering handlers...")
    start.register()
    handlers.register()
    cookie_handlers.register()
    inbox_handlers.register()
    admin.register()

    print_startup_panel(db, len(proxies))

    threading.Thread(target=auto_backup_loop,      daemon=True).start()
    threading.Thread(target=auto_proxy_fetch_loop, daemon=True).start()

    _log("📡", "bold cyan", "TELEGRAM", "Notifying admin...")
    try:
        state.bot.send_message(
            ADMIN_ID,
            f"{E_ROBOT} {bold('Bot Started!')}\n"
            f"<blockquote>{E_GREEN} Status: Online\n"
            f"{E_CLOCK} Time: {mono(time.strftime('%Y-%m-%d %H:%M:%S'))}\n"
            f"{E_GLOBE} Proxies: {mono(str(len(proxies)))}\n"
            f"{E_USER} DB Users: {mono(str(len(db.get('users', {}))))}\n"
            f"🌐 Auth: <code>ProxyHunter → Urban VPN</code>\n"
            f"{E_GEAR} {italic('Dev: @RBX404')}</blockquote>",
            parse_mode="HTML"
        )
    except Exception as e:
        _log("⚠️ ", "yellow", "TELEGRAM", f"Could not notify admin: {e}")

    _log("🚀", "bold green", "BOT", "[bold green]Running! Listening for updates...[/bold green]")
    console.print()

    # Auto-reconnect on network drops
    while True:
        try:
            state.bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                logger_level=None,
            )
        except KeyboardInterrupt:
            _log("🛑", "red", "BOT", "Stopped by user.")
            break
        except Exception as e:
            err = str(e)[:100]
            _log("⚠️ ", "yellow", "POLLING", f"Connection dropped: {err}")
            _log("🔄", "cyan",   "POLLING", "Reconnecting in 5s...")
            time.sleep(5)


if __name__ == "__main__":
    main()
