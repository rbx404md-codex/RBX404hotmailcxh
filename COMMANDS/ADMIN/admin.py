import io
import os
import time
import shutil
import tempfile
import threading
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, make_progress_bar,
    E_CROWN, E_GEAR, E_BAN, E_UNLOCK, E_CHECK, E_CROSS, E_BELL, E_CHART,
    E_GLOBE, E_BOLT, E_SHIELD, E_FILE, E_USER, E_MEMO, E_CLOCK, E_WARN,
    E_GREEN, E_RED, E_STOP, E_HOURGLASS, E_FIRE, E_PIN, E_ROCKET
)
from DATABASE.database import load_db, save_db
from PROXY.proxy import (init_proxies, save_proxies_to_file, test_single_proxy,
                         load_admin_proxies, save_admin_proxies_to_file)
from PROXY.fetcher import fetch_urban_vpn_proxies, get_country_summary
from CONFIG.config import (
    ADMIN_ID, DB_FILE, PROXIES_FILE, ADMIN_PROXIES_FILE,
    MASTER_THREADS, INBOXER_THREADS, COOKIES_THREADS
)


def _bq(text):
    """Wrap in Telegram blockquote."""
    return f"<blockquote>{text}</blockquote>"


def register():
    bot = state.bot

    @bot.message_handler(commands=['adm'])
    def cmd_adm(message):
        if message.from_user.id != ADMIN_ID:
            return
        cmds = "\n".join([
            f"{E_BAN} <code>/ban &lt;id&gt; &lt;reason&gt; [days]</code>",
            f"{E_UNLOCK} <code>/unban &lt;id&gt; [reason]</code>",
            f"{E_CHECK} <code>/approve &lt;id&gt; [days]</code>",
            f"{E_CROSS} <code>/demote &lt;id&gt;</code>",
            f"{E_BELL} <code>/broadcast</code> — Reply to broadcast",
            f"{E_CHART} <code>/status</code> — Full stats",
            f"{E_GLOBE} <code>/get_proxies</code> — Get proxy list",
            f"{E_BOLT} <code>/addproxy &lt;proxy&gt;</code> — Add proxy",
            f"{E_GEAR} <code>/updatep</code> — Reply to proxy file",
            f"{E_SHIELD} <code>/test</code> — Test all proxies",
            f"{E_ROCKET} <code>/scrap</code> — Fetch Urban VPN proxies",
            f"{E_FILE} <code>/fetch</code> — DB backup",
            f"📦 <code>/fetch_full</code> — Full bot source + DB zip",
            "🧹 <code>/clear_cache</code> — Clear bot cache",
            "👥 <code>/users</code> — List users",
            "🔍 <code>/userinfo &lt;id&gt;</code> — User details",
            "🗑️ <code>/deleteuser &lt;id&gt;</code> — Remove from DB",
            "🌐 <code>/myip</code> — Bot's current IP",
            "🧵 <code>/threads</code> — Thread config",
            "📊 <code>/globalstats</code> — Global stats",
            "🔄 <code>/restart_proxy</code> — Force proxy refresh",
            "♻️ <code>/refresh</code> — Refresh bot (keep checks running)",
            "📜 <code>/logs [mins]</code> — Get last N mins of logs (default: 5)",
            "📡 <code>/pool_status</code> — Proxy fetch info",
        ])
        text = (
            f"{E_CROWN} {bold('Admin Panel')}\n"
            f"{_bq(cmds)}\n"
            f"{E_GEAR} {italic('Dev: @RBX404')}"
        )
        bot.reply_to(message, text, parse_mode="HTML")

    @bot.message_handler(commands=['ban'])
    def cmd_ban(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/ban &lt;id&gt; &lt;reason&gt; [days]</code>", parse_mode="HTML")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.reply_to(message, f"{E_CROSS} Invalid user ID!", parse_mode="HTML")
            return
        reason = parts[2] if len(parts) > 2 else "No reason"
        days = None
        if len(parts) > 3:
            try:
                days = int(parts[3])
            except:
                pass
        db_inst = load_db()
        db_inst.setdefault("banned", {})[str(target_id)] = {
            "reason": reason, "days": days, "date": datetime.now().isoformat(), "by": ADMIN_ID
        }
        save_db(db_inst)
        duration = f"{days} days" if days else "Lifetime"
        info = f"{E_USER} ID: {mono(str(target_id))}\n{E_MEMO} Reason: {mono(reason)}\n{E_CLOCK} Duration: {mono(duration)}"
        bot.reply_to(message,
            f"{E_BAN} {bold('User Banned!')}\n{_bq(info)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")
        try:
            info2 = f"{E_MEMO} Reason: {mono(reason)}\n{E_CLOCK} Duration: {mono(duration)}"
            bot.send_message(target_id,
                f"{E_BAN} {bold('You have been banned!')}\n{_bq(info2)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except:
            pass

    @bot.message_handler(commands=['unban'])
    def cmd_unban(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/unban &lt;id&gt; [reason]</code>", parse_mode="HTML")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.reply_to(message, f"{E_CROSS} Invalid user ID!", parse_mode="HTML")
            return
        reason = parts[2] if len(parts) > 2 else "No reason"
        db_inst = load_db()
        if str(target_id) in db_inst.get("banned", {}):
            del db_inst["banned"][str(target_id)]
            save_db(db_inst)
        info = f"{E_USER} ID: {mono(str(target_id))}\n{E_MEMO} Reason: {mono(reason)}"
        bot.reply_to(message,
            f"{E_UNLOCK} {bold('User Unbanned!')}\n{_bq(info)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")
        try:
            bot.send_message(target_id,
                f"{E_UNLOCK} {bold('You have been unbanned!')}\n{_bq(f'{E_MEMO} Reason: {mono(reason)}')}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except:
            pass

    @bot.message_handler(commands=['approve'])
    def cmd_approve(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/approve &lt;id&gt; [days]</code>", parse_mode="HTML")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.reply_to(message, f"{E_CROSS} Invalid user ID!", parse_mode="HTML")
            return
        days = None
        if len(parts) > 2:
            try:
                days = int(parts[2])
            except:
                pass
        db_inst = load_db()
        db_inst.setdefault("approved", {})[str(target_id)] = {
            "days": days, "date": datetime.now().isoformat(), "by": ADMIN_ID
        }
        save_db(db_inst)
        duration = f"{days} days" if days else "Lifetime"
        info = f"{E_USER} ID: {mono(str(target_id))}\n{E_CLOCK} Duration: {mono(duration)}"
        bot.reply_to(message,
            f"{E_CROWN} {bold('User Approved!')}\n{_bq(info)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")
        try:
            info2 = f"{E_GEAR} Line limit removed!\n{E_CLOCK} Duration: {mono(duration)}"
            bot.send_message(target_id,
                f"{E_CROWN} {bold('You have been approved!')}\n{_bq(info2)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except:
            pass

    @bot.message_handler(commands=['demote'])
    def cmd_demote(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/demote &lt;id&gt;</code>", parse_mode="HTML")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.reply_to(message, f"{E_CROSS} Invalid user ID!", parse_mode="HTML")
            return
        db_inst = load_db()
        if str(target_id) in db_inst.get("approved", {}):
            del db_inst["approved"][str(target_id)]
            save_db(db_inst)
        bot.reply_to(message,
            f"{E_CROSS} {bold('User Demoted!')}\n{_bq(f'{E_USER} ID: {mono(str(target_id))}')}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")
        try:
            bot.send_message(target_id,
                f"{E_CROSS} {bold('You have been demoted to normal rank.')}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except:
            pass

    @bot.message_handler(commands=['broadcast'])
    def cmd_broadcast(message):
        if message.from_user.id != ADMIN_ID:
            return
        if not message.reply_to_message:
            bot.reply_to(message, f"{E_WARN} Reply to a message to broadcast it!", parse_mode="HTML")
            return
        db_inst = load_db()
        users = list(db_inst.get("users", {}).keys())
        total = len(users)
        sent = 0
        failed = 0
        progress_msg = bot.reply_to(message, f"{E_BELL} Broadcasting... 0/{total}", parse_mode="HTML")
        for uid in users:
            try:
                bot.copy_message(int(uid), message.chat.id, message.reply_to_message.message_id)
                sent += 1
            except:
                failed += 1
            if (sent + failed) % 10 == 0:
                try:
                    pbar = make_progress_bar(sent + failed, total, 15)
                    body = f"{mono(pbar)}\n{E_CHECK} Sent: {sent}  {E_CROSS} Failed: {failed}"
                    bot.edit_message_text(
                        f"{E_BELL} {bold('Broadcasting...')}\n{_bq(body)}",
                        progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")
                except:
                    pass
        body = f"{E_CHECK} Sent: {mono(str(sent))}\n{E_CROSS} Failed: {mono(str(failed))}\n{E_CHART} Total: {mono(str(total))}"
        bot.edit_message_text(
            f"{E_BELL} {bold('Broadcast Complete!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")

    @bot.message_handler(commands=['status'])
    def cmd_status(message):
        if message.from_user.id != ADMIN_ID:
            return
        db_inst = load_db()
        uptime = time.time() - state.BOT_START_TIME
        uptime_str    = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime))
        total_users   = len(db_inst.get("users", {}))
        banned_users  = len(db_inst.get("banned", {}))
        approved_users= len(db_inst.get("approved", {}))
        g             = db_inst.get("global_stats", {})
        total_proxies = len(init_proxies())
        with state.active_checks_lock:
            current_checks = len([k for k in state.active_checks if not str(k).startswith("pending_")])

        body = (
            f"{E_GREEN} Status: {mono('Online')}\n"
            f"{E_CLOCK} Uptime: {mono(uptime_str)}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{E_USER} Users: {mono(str(total_users))}\n"
            f"{E_BAN} Banned: {mono(str(banned_users))}\n"
            f"{E_CROWN} Approved: {mono(str(approved_users))}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{E_CHECK} Checked: {mono(str(g.get('total_checked', 0)))}\n"
            f"{E_FIRE} Hits: {mono(str(g.get('total_hits', 0)))}\n"
            f"{E_BOLT} Active Checks: {mono(str(current_checks))}\n"
            f"{E_GLOBE} Proxies: {mono(str(total_proxies))}"
        )
        bot.reply_to(message,
            f"{E_CHART} {bold('Admin Status Panel')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")

    @bot.message_handler(commands=['get_proxies'])
    def cmd_get_proxies(message):
        if message.from_user.id != ADMIN_ID:
            return
        proxies = init_proxies()
        f = io.BytesIO("\n".join(proxies).encode("utf-8"))
        f.name = "proxies.txt"
        body = f"Total: {mono(str(len(proxies)))}\nSource: FILES/proxy.txt"
        bot.send_document(message.chat.id, f,
                          caption=f"{E_GLOBE} {bold('Current Proxies')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                          parse_mode="HTML", reply_to_message_id=message.message_id)

    @bot.message_handler(commands=['addproxy'])
    def cmd_addproxy(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/addproxy &lt;proxy&gt;</code>", parse_mode="HTML")
            return
        proxy_str = parts[1].strip()
        testing_msg = bot.reply_to(message, f"{E_HOURGLASS} Testing proxy...", parse_mode="HTML")
        alive = False
        for _ in range(2):
            if test_single_proxy(proxy_str):
                alive = True
                break
            time.sleep(1)
        if alive:
            admin_proxies = load_admin_proxies()
            if proxy_str not in admin_proxies:
                admin_proxies.append(proxy_str)
                save_admin_proxies_to_file(admin_proxies)
            body = f"{E_GLOBE} {mono(proxy_str)}\n{E_GREEN} Status: Live\n💾 Saved to admin list"
            bot.edit_message_text(
                f"{E_CHECK} {bold('Proxy Added!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                testing_msg.chat.id, testing_msg.message_id, parse_mode="HTML")
        else:
            body = f"{E_GLOBE} {mono(proxy_str)}\n{E_RED} Dead — not added"
            bot.edit_message_text(
                f"{E_CROSS} {bold('Proxy Dead!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                testing_msg.chat.id, testing_msg.message_id, parse_mode="HTML")

    @bot.message_handler(commands=['updatep'])
    def cmd_updatep(message):
        if message.from_user.id != ADMIN_ID:
            return
        if not message.reply_to_message or not message.reply_to_message.document:
            bot.reply_to(message, f"{E_WARN} Reply to a proxy .txt file!", parse_mode="HTML")
            return
        try:
            file_info    = bot.get_file(message.reply_to_message.document.file_id)
            file_content = bot.download_file(file_info.file_path)
            new_proxies  = [l.strip() for l in file_content.decode("utf-8", errors="ignore").splitlines() if l.strip()]
            save_admin_proxies_to_file(new_proxies)
            body = (
                f"{E_GLOBE} Total: {mono(str(len(new_proxies)))}\n"
                f"{E_SHIELD} Saved to FILES/admin_proxies.txt\n"
                "⚡ Auto-fetch will not remove these"
            )
            bot.reply_to(message,
                f"{E_CHECK} {bold('Admin Proxies Updated!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"{E_CROSS} Error: {mono(str(e))}", parse_mode="HTML")

    @bot.message_handler(commands=['test'])
    def cmd_test_proxies(message):
        if message.from_user.id != ADMIN_ID:
            return
        proxies = init_proxies()
        total = len(proxies)
        if total == 0:
            bot.reply_to(message, f"{E_CROSS} No proxies to test!", parse_mode="HTML")
            return
        progress_msg = bot.reply_to(message, f"{E_HOURGLASS} Testing {total} proxies...", parse_mode="HTML")
        alive_list = []
        dead_list  = []
        tested     = 0
        test_lock  = threading.Lock()

        def test_one(p):
            nonlocal tested
            result = test_single_proxy(p)
            with test_lock:
                tested += 1
                (alive_list if result else dead_list).append(p)

        with ThreadPoolExecutor(max_workers=10) as ex:
            futs = [ex.submit(test_one, p) for p in proxies]
            last_update = 0
            for f in as_completed(futs):
                now = time.time()
                if now - last_update > 3:
                    last_update = now
                    try:
                        pbar = make_progress_bar(tested, total, 15)
                        body = f"{mono(pbar)}\n{E_GREEN} Alive: {len(alive_list)}  {E_RED} Dead: {len(dead_list)}"
                        bot.edit_message_text(
                            f"{E_HOURGLASS} {bold('Testing Proxies...')}\n{_bq(body)}",
                            progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")
                    except:
                        pass

        summary_lines = (
            ["Proxy Test Results", f"Total: {total}", f"Alive: {len(alive_list)}", f"Dead: {len(dead_list)}", "", "=== ALIVE ==="]
            + alive_list + ["", "=== DEAD ==="] + dead_list
        )
        f = io.BytesIO("\n".join(summary_lines).encode("utf-8"))
        f.name = "proxy_test_results.txt"

        body = f"{E_GREEN} Alive: {mono(str(len(alive_list)))}\n{E_RED} Dead: {mono(str(len(dead_list)))}\n{E_CHART} Total: {mono(str(total))}"
        bot.edit_message_text(
            f"{E_SHIELD} {bold('Proxy Test Complete!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")
        bot.send_document(message.chat.id, f,
                          caption=f"{E_SHIELD} Proxy test results\n{E_GEAR} {italic('Dev: @RBX404')}",
                          parse_mode="HTML")

    @bot.message_handler(commands=['scrap'])
    def cmd_scrap(message):
        if message.from_user.id != ADMIN_ID:
            return
        status_msg = bot.reply_to(message,
            f"{E_HOURGLASS} {bold('Fetching Urban VPN proxies...')}\n"
            f"{_bq('This may take 1-2 minutes...')}",
            parse_mode="HTML")

        def do_scrap():
            start_time    = time.time()
            fetched_count = [0]
            total_servers = [0]

            def progress(step_type, *args):
                if step_type == "total":
                    total_servers[0] = args[0]
                elif step_type == "complete":
                    fetched_count[0] = args[0]

            proxies = fetch_urban_vpn_proxies(progress)
            elapsed = time.time() - start_time

            if not proxies:
                try:
                    bot.edit_message_text(
                        f"{E_CROSS} {bold('Failed to fetch proxies!')}\n{_bq(f'{E_WARN} Urban VPN API may be down.')}",
                        status_msg.chat.id, status_msg.message_id, parse_mode="HTML")
                except:
                    pass
                return

            content = "\n".join(f"{p['ip']}:{p['port']}:{p['user']}:{p['pass']}" for p in proxies)
            country_summary = get_country_summary(proxies)
            top_countries   = sorted(country_summary.items(), key=lambda x: x[1], reverse=True)[:10]
            country_lines   = "\n".join(f"  {cc}: {cnt}" for cc, cnt in top_countries)
            if len(country_summary) > 10:
                country_lines += f"\n  ...and {len(country_summary) - 10} more"

            speed_str = f"{len(proxies)/elapsed:.1f} prx/s" if elapsed > 0 else "N/A"
            body = (
                f"{E_CHECK} Fetched: {mono(str(len(proxies)))}\n"
                f"{E_GLOBE} Servers: {mono(str(total_servers[0]))}\n"
                f"{E_CLOCK} Time: {mono(f'{elapsed:.1f}s')}\n"
                f"{E_BOLT} Speed: {mono(speed_str)}\n"
                f"━━━━━━━━━━━━━━\n"
                f"{bold('Top Countries:')}\n"
                f"<pre>{country_lines}</pre>"
            )
            caption = f"{E_ROCKET} {bold('Proxy Scrape Complete!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}"

            f = io.BytesIO(content.encode("utf-8"))
            f.name = f"scraped_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            try:
                bot.delete_message(status_msg.chat.id, status_msg.message_id)
            except:
                pass
            bot.send_document(ADMIN_ID, f, caption=caption, parse_mode="HTML")

        threading.Thread(target=do_scrap, daemon=True).start()

    @bot.message_handler(commands=['fetch'])
    def cmd_fetch(message):
        if message.from_user.id != ADMIN_ID:
            return
        send_backup(message.chat.id, "Manual backup requested")

    @bot.message_handler(commands=['fetch_full'])
    def cmd_fetch_full(message):
        if message.from_user.id != ADMIN_ID:
            return
        progress_msg = bot.reply_to(message,
            f"📦 {bold('Creating full bot backup...')}\n{_bq('Zipping all source files + database...')}",
            parse_mode="HTML")

        def do_full_backup():
            try:
                send_full_bot_backup(message.chat.id, "Manual full backup requested")
                try:
                    bot.delete_message(progress_msg.chat.id, progress_msg.message_id)
                except:
                    pass
            except Exception as e:
                try:
                    bot.edit_message_text(
                        f"{E_CROSS} Full backup failed: {mono(str(e))}",
                        progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")
                except:
                    pass

        threading.Thread(target=do_full_backup, daemon=True).start()

    # ── NEW COMMANDS ──────────────────────────────────────────────────────────

    @bot.message_handler(commands=['clear_cache'])
    def cmd_clear_cache(message):
        if message.from_user.id != ADMIN_ID:
            return
        progress_msg = bot.reply_to(message,
            f"🧹 {bold('Clearing cache...')}\n{_bq('Removing __pycache__, .pyc, logs...')}",
            parse_mode="HTML")

        def do_clear():
            try:
                from clear_cache import run_cache_clear

                def _human(b):
                    for u in ["B", "KB", "MB", "GB"]:
                        if b < 1024:
                            return f"{b:.2f} {u}"
                        b /= 1024
                    return f"{b:.2f} GB"

                r   = run_cache_clear()
                body = (
                    f"📁 <b>__pycache__ dirs:</b> {mono(str(r['pycache_dirs']))}  freed {mono(_human(r['freed_pycache']))}\n"
                    f"🐍 <b>.pyc files:</b> {mono(str(r['pyc_files']))}\n"
                    f"📋 <b>bot.log:</b> truncated  freed {mono(_human(r['freed_log']))}\n"
                    f"🗑️ <b>Temp files:</b> {mono(str(r['tmp_files']))}  freed {mono(_human(r['freed_tmp']))}\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"💾 <b>Total freed:</b> {mono(_human(r['total_freed']))}"
                )
                bot.edit_message_text(
                    f"🧹 {bold('Cache Cleared!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                    progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")
            except Exception as e:
                bot.edit_message_text(
                    f"{E_CROSS} Cache clear failed: {mono(str(e))}",
                    progress_msg.chat.id, progress_msg.message_id, parse_mode="HTML")

        threading.Thread(target=do_clear, daemon=True).start()

    @bot.message_handler(commands=['users'])
    def cmd_users(message):
        if message.from_user.id != ADMIN_ID:
            return
        db_inst  = load_db()
        users    = db_inst.get("users", {})
        banned   = set(db_inst.get("banned", {}).keys())
        approved = set(db_inst.get("approved", {}).keys())

        lines = []
        for uid, u in list(users.items())[:30]:
            name  = u.get("first_name", "?")
            uname = u.get("username", "")
            rank  = "👑" if uid in approved else ("🚫" if uid in banned else "👤")
            entry = f"{rank} {name} {mono(uid)}"
            if uname:
                entry += f" @{uname}"
            lines.append(entry)

        body = "\n".join(lines) if lines else "No users yet."
        text = (
            f"👥 {bold(f'Users ({len(users)} total)')}\n"
            f"{_bq(body)}\n"
            f"{E_GEAR} {italic('Dev: @RBX404')}"
        )
        if len(text) > 4000:
            content = "\n".join(
                f"{uid}: {u.get('first_name','?')} @{u.get('username','')}"
                for uid, u in users.items()
            )
            f_obj = io.BytesIO(content.encode("utf-8"))
            f_obj.name = "users.txt"
            bot.send_document(message.chat.id, f_obj,
                caption=f"👥 {bold('All Users')} ({len(users)} total)\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        else:
            bot.reply_to(message, text, parse_mode="HTML")

    @bot.message_handler(commands=['myip'])
    def cmd_myip(message):
        if message.from_user.id != ADMIN_ID:
            return
        msg = bot.reply_to(message, f"{E_HOURGLASS} Checking IP...", parse_mode="HTML")

        def do_check():
            try:
                import requests as req
                r  = req.get("https://httpbin.org/ip", timeout=10)
                ip = r.json().get("origin", "unknown")
                body = f"🔍 IP: {mono(ip)}\n⚡ Direct connection"
                bot.edit_message_text(
                    f"🌐 {bold('Bot IP Address')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                    msg.chat.id, msg.message_id, parse_mode="HTML")
            except Exception as e:
                bot.edit_message_text(
                    f"{E_CROSS} Failed: {mono(str(e))}",
                    msg.chat.id, msg.message_id, parse_mode="HTML")

        threading.Thread(target=do_check, daemon=True).start()

    @bot.message_handler(commands=['threads'])
    def cmd_threads(message):
        if message.from_user.id != ADMIN_ID:
            return
        body = (
            f"⚔️ <b>M-Hotmail:</b> {mono(str(MASTER_THREADS))} threads\n"
            f"📬 <b>Inboxer:</b> {mono(str(INBOXER_THREADS))} threads\n"
            f"🍪 <b>Cookies:</b> {mono(str(COOKIES_THREADS))} threads\n"
            f"━━━━━━━━━━━━━━\n"
            f"📝 Edit: <code>CONFIG/config.py</code>"
        )
        bot.reply_to(message,
            f"🧵 {bold('Thread Configuration')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")

    @bot.message_handler(commands=['globalstats'])
    def cmd_globalstats(message):
        if message.from_user.id != ADMIN_ID:
            return
        db_inst = load_db()
        g       = db_inst.get("global_stats", {})
        uptime  = time.time() - state.BOT_START_TIME
        body = (
            f"{E_CHECK} Total Checked: {mono(str(g.get('total_checked', 0)))}\n"
            f"{E_FIRE} Total Hits: {mono(str(g.get('total_hits', 0)))}\n"
            f"{E_GLOBE} Total Lines: {mono(str(g.get('total_lines_checked', 0)))}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{E_USER} Users: {mono(str(len(db_inst.get('users', {}))))}\n"
            f"{E_BAN} Banned: {mono(str(len(db_inst.get('banned', {}))))}\n"
            f"{E_CROWN} Approved: {mono(str(len(db_inst.get('approved', {}))))}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{E_CLOCK} Uptime: {mono(time.strftime('%Hh %Mm %Ss', time.gmtime(uptime)))}\n"
            f"{E_GLOBE} Proxies: {mono(str(len(init_proxies())))}"
        )
        bot.reply_to(message,
            f"{E_CHART} {bold('Global Statistics')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")

    @bot.message_handler(commands=['restart_proxy'])
    def cmd_restart_proxy(message):
        if message.from_user.id != ADMIN_ID:
            return
        msg = bot.reply_to(message,
            f"🔄 {bold('Force refreshing proxies...')}\n{_bq('Clearing FILES/proxy.txt and fetching fresh...')}",
            parse_mode="HTML")

        def do_restart():
            try:
                from PROXY.webshare_fetcher import fetch_webshare_proxies, clear_proxy_file, append_proxies_to_file
                clear_proxy_file()
                proxies, used_own = fetch_webshare_proxies(notify_admin_fn=None)
                if proxies:
                    append_proxies_to_file(proxies)
                    body = f"{E_GLOBE} Fetched: {mono(str(len(proxies)))} proxies\n💾 Saved to FILES/proxy.txt"
                    bot.edit_message_text(
                        f"✅ {bold('Proxy Refresh Done!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                        msg.chat.id, msg.message_id, parse_mode="HTML")
                else:
                    bot.edit_message_text(
                        f"{E_WARN} {bold('Webshare Failed!')}\n{_bq('Using own IP as fallback.')}\n{E_GEAR} {italic('Dev: @RBX404')}",
                        msg.chat.id, msg.message_id, parse_mode="HTML")
            except Exception as e:
                bot.edit_message_text(
                    f"{E_CROSS} Error: {mono(str(e))}",
                    msg.chat.id, msg.message_id, parse_mode="HTML")

        threading.Thread(target=do_restart, daemon=True).start()

    @bot.message_handler(commands=['userinfo'])
    def cmd_userinfo(message):
        if message.from_user.id != ADMIN_ID:
            return
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, f"{E_WARN} Usage: <code>/userinfo &lt;id&gt;</code>", parse_mode="HTML")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.reply_to(message, f"{E_CROSS} Invalid ID!", parse_mode="HTML")
            return
        db_inst  = load_db()
        users    = db_inst.get("users", {})
        banned   = db_inst.get("banned", {})
        approved = db_inst.get("approved", {})
        u = users.get(str(target_id), {})
        if not u:
            bot.reply_to(message, f"{E_CROSS} User not found in DB.", parse_mode="HTML")
            return
        rank = "👑 Approved" if str(target_id) in approved else ("🚫 Banned" if str(target_id) in banned else "👤 Normal")
        ban_info = banned.get(str(target_id), {})
        ban_extra = f"\n━━━━━━━━━━━━━━\n🚫 Ban reason: {mono(ban_info.get('reason','?'))}" if str(target_id) in banned else ""
        body = (
            f"🪪 <b>Name:</b> {mono(u.get('first_name','?'))} {u.get('last_name','')}\n"
            f"🔗 <b>Username:</b> @{u.get('username','N/A')}\n"
            f"🔑 <b>ID:</b> {mono(str(target_id))}\n"
            f"🏅 <b>Rank:</b> {rank}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{E_CHECK} <b>Checked:</b> {mono(str(u.get('total_checked',0)))}\n"
            f"{E_FIRE} <b>Hits:</b> {mono(str(u.get('total_hits',0)))}\n"
            f"━━━━━━━━━━━━━━\n"
            f"{E_CLOCK} <b>First seen:</b> {mono(u.get('first_seen','?')[:19])}\n"
            f"{E_CLOCK} <b>Last seen:</b> {mono(u.get('last_seen','?')[:19])}"
            f"{ban_extra}"
        )
        bot.reply_to(message,
            f"{E_USER} {bold('User Info')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
            parse_mode="HTML")

    @bot.message_handler(commands=['refresh'])
    def cmd_refresh(message):
        """Refresh bot internals without stopping any active checks."""
        if message.from_user.id != ADMIN_ID:
            return
        import importlib, sys
        msg = bot.reply_to(message,
            f"🔄 {bold('Refreshing Bot...')}\n{_bq('Reloading config & modules (active checks kept running)...')}",
            parse_mode="HTML")

        def do_refresh():
            results = []
            modules_to_reload = [
                "CONFIG.config",
                "DATABASE.database",
                "PROXY.proxy",
            ]
            for mod_name in modules_to_reload:
                try:
                    if mod_name in sys.modules:
                        importlib.reload(sys.modules[mod_name])
                        results.append(f"✅ {mod_name}")
                    else:
                        results.append(f"⚪ {mod_name} (not loaded)")
                except Exception as e:
                    results.append(f"❌ {mod_name}: {str(e)[:40]}")

            # Refresh proxy list in memory
            proxy_count = 0
            try:
                from PROXY.proxy import init_proxies
                proxies = init_proxies()
                proxy_count = len(proxies)
                results.append(f"🌐 Proxies reloaded: {proxy_count}")
            except Exception as e:
                results.append(f"⚠️ Proxy reload failed: {str(e)[:40]}")

            with state.active_checks_lock:
                active = len([k for k in state.active_checks if not str(k).startswith(("pending_", "file_"))])

            body = "\n".join(results) + f"\n━━━━━━━━━━━━━━\n⚡ Active checks kept: {mono(str(active))}\n🌐 Proxies: {mono(str(proxy_count))}"
            try:
                bot.edit_message_text(
                    f"✅ {bold('Refresh Done!')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                    msg.chat.id, msg.message_id, parse_mode="HTML")
            except Exception:
                pass

        threading.Thread(target=do_refresh, daemon=True).start()

    @bot.message_handler(commands=['pool_status'])
    def cmd_pool_status(message):
        if message.from_user.id != ADMIN_ID:
            return
        try:
            from bot import proxy_fetch_state
            from CONFIG.config import PROXY_BATCH_INTERVAL
            
            now = time.time()
            next_run = proxy_fetch_state.get("next_run", 0)
            batch = proxy_fetch_state.get("batch_num", 0)
            
            if next_run == 0:
                status = f"{E_HOURGLASS} Starting up..."
                time_str = "Wait..."
            elif now < next_run:
                time_left = int(next_run - now)
                status = f"{E_GREEN} Active"
                time_str = f"{time_left // 60}m {time_left % 60}s"
            else:
                status = f"{E_BOLT} {bold('Fetching now...')}"
                time_str = "0s"
                
            body = (
                f"{E_GLOBE} <b>Status:</b> {status}\n"
                f"{E_CLOCK} <b>Next run in:</b> {mono(time_str)}\n"
                f"{E_BOLT} <b>Next batch:</b> {mono(str(batch + 1))}\n"
                f"{E_HOURGLASS} <b>Interval:</b> {mono(f'{PROXY_BATCH_INTERVAL//60}m')}"
            )
            bot.reply_to(message,
                f"📡 {bold('Proxy Pool Status')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"{E_CROSS} Error: {mono(str(e))}", parse_mode="HTML")


    @bot.message_handler(commands=['logs'])
    def cmd_logs(message):
        if message.from_user.id != ADMIN_ID:
            return
        from HOME.logger import get_last_minutes, get_log_file_path
        import tempfile

        parts = message.text.split()
        try:
            mins = int(parts[1]) if len(parts) > 1 else 5
            mins = max(1, min(60, mins))  # Clamp between 1-60 minutes
        except ValueError:
            mins = 5

        log_content = get_last_minutes(mins)

        if not log_content or log_content.startswith("No logs"):
            bot.reply_to(message, f"{E_CROSS} {log_content}", parse_mode="HTML")
            return

        # Write to temp file and send as document
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        tmp_file = os.path.join(tempfile.gettempdir(), f"bot_logs_{mins}min_{ts}.txt")
        try:
            with open(tmp_file, "w", encoding="utf-8", errors="replace") as f:
                f.write(f"=== Bot Logs (Last {mins} minutes) ===\n")
                f.write(f"=== Generated: {ts} ===\n\n")
                f.write(log_content)

            caption = (
                f"{E_FILE} {bold('Bot Logs — Last {mins} min')}\n"
                f"{_bq(f'📊 Lines: {len(log_content.splitlines())}')}\n"
                f"{E_GEAR} {italic('Dev: @RBX404')}"
            )
            with open(tmp_file, "rb") as f:
                bot.send_document(message.chat.id, f, caption=caption, parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"{E_CROSS} Error sending logs: {mono(str(e))}", parse_mode="HTML")
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)


def send_backup(chat_id, reason=""):
    from HOME import state
    try:
        db_inst     = load_db()
        g           = db_inst.get("global_stats", {})
        total_users = len(db_inst.get("users", {}))
        tmpdir      = tempfile.mkdtemp(prefix="backup_")
        ts          = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, os.path.join(tmpdir, os.path.basename(DB_FILE)))
        if os.path.exists(PROXIES_FILE):
            shutil.copy2(PROXIES_FILE, os.path.join(tmpdir, "proxy.txt"))

        with open(os.path.join(tmpdir, "backup_info.txt"), "w") as f:
            f.write(
                f"Backup Date: {ts}\nReason: {reason}\nTotal Users: {total_users}\n"
                f"Total Checked: {g.get('total_checked', 0)}\n"
                f"Total Hits: {g.get('total_hits', 0)}\nBot by @RBX404\n"
            )

        zip_path = os.path.join(tmpdir, f"backup_{ts}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fn in os.listdir(tmpdir):
                fp = os.path.join(tmpdir, fn)
                if fp != zip_path:
                    zf.write(fp, fn)

        with open(zip_path, 'rb') as f:
            body = (
                f"{E_CLOCK} {mono(ts)}\n"
                f"{E_MEMO} {reason}\n"
                f"{E_USER} Users: {mono(str(total_users))}\n"
                f"{E_CHART} Checked: {mono(str(g.get('total_checked', 0)))}\n"
                f"{E_FIRE} Hits: {mono(str(g.get('total_hits', 0)))}"
            )
            state.bot.send_document(
                chat_id, f,
                caption=f"{E_FILE} {bold('Database Backup')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")
        shutil.rmtree(tmpdir)
    except Exception as e:
        try:
            state.bot.send_message(chat_id, f"{E_CROSS} Backup error: {mono(str(e))}", parse_mode="HTML")
        except:
            pass


def send_full_bot_backup(chat_id, reason=""):
    """Send complete bot source code + database as zip."""
    from HOME import state
    try:
        db_inst     = load_db()
        g           = db_inst.get("global_stats", {})
        total_users = len(db_inst.get("users", {}))
        tmpdir      = tempfile.mkdtemp(prefix="full_backup_")
        ts          = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Get bot root directory
        bot_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Create zip with all bot files
        zip_path = os.path.join(tmpdir, f"bot_full_backup_{ts}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add backup info
            info_content = (
                f"Full Bot Backup\n"
                f"Date: {ts}\n"
                f"Reason: {reason}\n"
                f"Total Users: {total_users}\n"
                f"Total Checked: {g.get('total_checked', 0)}\n"
                f"Total Hits: {g.get('total_hits', 0)}\n"
                f"Bot by @RBX404\n"
            )
            zf.writestr("BACKUP_INFO.txt", info_content)

            # Walk through bot directory and add all files
            exclude_dirs = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules'}
            exclude_exts = {'.pyc', '.pyo', '.log', '.tmp'}

            for root, dirs, files in os.walk(bot_root):
                # Remove excluded directories from traversal
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    file_path = os.path.join(root, file)
                    _, ext = os.path.splitext(file)

                    # Skip excluded extensions
                    if ext in exclude_exts:
                        continue

                    # Get relative path from bot root
                    arcname = os.path.relpath(file_path, bot_root)

                    try:
                        zf.write(file_path, arcname)
                    except Exception:
                        pass  # Skip files that can't be read

        # Get zip file size
        zip_size = os.path.getsize(zip_path)
        size_mb = zip_size / (1024 * 1024)

        with open(zip_path, 'rb') as f:
            body = (
                f"{E_CLOCK} {mono(ts)}\n"
                f"{E_MEMO} {reason}\n"
                f"📦 Size: {mono(f'{size_mb:.2f} MB')}\n"
                f"{E_USER} Users: {mono(str(total_users))}\n"
                f"{E_CHART} Checked: {mono(str(g.get('total_checked', 0)))}\n"
                f"{E_FIRE} Hits: {mono(str(g.get('total_hits', 0)))}"
            )
            state.bot.send_document(
                chat_id, f,
                caption=f"📦 {bold('Full Bot Backup (Source + DB)')}\n{_bq(body)}\n{E_GEAR} {italic('Dev: @RBX404')}",
                parse_mode="HTML")

        shutil.rmtree(tmpdir)
    except Exception as e:
        try:
            state.bot.send_message(chat_id, f"{E_CROSS} Full backup error: {mono(str(e))}", parse_mode="HTML")
        except:
            pass
