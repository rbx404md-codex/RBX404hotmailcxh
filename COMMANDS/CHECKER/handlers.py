import io
import threading
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, pre,
    E_FILE, E_CHART, E_CHECK, E_CROSS, E_BOLT, E_GLOBE, E_GEAR, E_MEMO,
    E_WARN, E_HOURGLASS, E_BAN, E_STOP, E_PLAY, E_PIN, E_FIRE
)
from HOME.session import CheckerSession
from HOME.runner import run_checker
from HOME.results import build_hits_text
from DATABASE.database import load_db, update_user_info, is_banned, is_approved
from PROXY.proxy import init_proxies
from API.checker_engine import parse_combos
from CONFIG.config import ADMIN_ID, MAX_LINES, MAX_FILE_SIZE_MB, MASTER_THREADS, DEFAULT_THREADS

_COOKIE_FILE_SIZE_MB = 10  # quota for cookie checker


def _answer(bot, call_id, text=None, alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=alert)
    except:
        pass


def register():
    bot = state.bot

    @bot.message_handler(content_types=['document'])
    def handle_document(message):
        user = message.from_user
        db_inst = load_db()
        update_user_info(db_inst, user)

        banned, reason = is_banned(db_inst, user.id)
        if banned:
            bot.reply_to(message, f"{E_BAN} {bold('You are banned!')}\n{E_MEMO} Reason: {mono(reason)}", parse_mode="HTML")
            return

        doc = message.document
        fname = doc.file_name or ""
        is_txt = fname.lower().endswith('.txt')
        is_zip = fname.lower().endswith('.zip')

        if not is_txt and not is_zip:
            bot.reply_to(message, f"{E_CROSS} {bold('Only .txt or .zip files are supported!')}", parse_mode="HTML")
            return

        # Size check
        max_bytes = max(MAX_FILE_SIZE_MB, _COOKIE_FILE_SIZE_MB) * 1024 * 1024
        if doc.file_size > max_bytes:
            bot.reply_to(
                message,
                f"{E_CROSS} {bold('You are allowed 10MB in your current quota')}\n"
                f"{E_MEMO} File size: {mono(f'{doc.file_size/1024/1024:.1f} MB')}",
                parse_mode="HTML"
            )
            return

        is_admin = user.id == ADMIN_ID
        with state.active_checks_lock:
            has_ms = user.id in state.active_checks and not is_admin
            has_ck = f"ck_{user.id}" in state.active_checks and not is_admin
            if has_ms or has_ck:
                bot.reply_to(message, f"{E_WARN} {bold('You already have an active check running!')}\n{E_MEMO} use /stop", parse_mode="HTML")
                return

        loading_msg = bot.reply_to(message, f"{E_HOURGLASS} {bold('Loading file...')} {E_GEAR}", parse_mode="HTML")

        try:
            file_info = bot.get_file(doc.file_id)
            file_content = bot.download_file(file_info.file_path)
        except Exception as e:
            bot.edit_message_text(f"{E_CROSS} Error reading file: {mono(str(e))}", loading_msg.chat.id, loading_msg.message_id, parse_mode="HTML")
            return

        # Store raw file bytes for later use by either mode
        with state.active_checks_lock:
            state.active_checks[f"file_{user.id}"] = {
                "content": file_content,
                "filename": fname,
                "size": doc.file_size,
                "message": message,
                "is_txt": is_txt,
                "is_zip": is_zip,
            }

        # Show mode selection
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 M-HOTMAIL", callback_data=f"mode_hotmail_{user.id}"),
            types.InlineKeyboardButton("🍪 Cookies",   callback_data=f"mode_cookies_{user.id}"),
        )
        markup.add(
            types.InlineKeyboardButton("📬 Inboxer",  callback_data=f"mode_inboxer_{user.id}"),
            types.InlineKeyboardButton("❌ Exit",      callback_data=f"mode_exit_{user.id}"),
        )

        bot.edit_message_text(
            f"{E_FILE} {bold('File received')}\n"
            f"{E_MEMO} Name: {mono(fname)}\n"
            f"{E_CHART} Size: {mono(f'{doc.file_size/1024:.1f} KB')}\n\n"
            f"Choose checker mode:",
            loading_msg.chat.id, loading_msg.message_id,
            parse_mode="HTML", reply_markup=markup
        )

    # ── M-HOTMAIL mode ────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mode_hotmail_"))
    def cb_mode_hotmail(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return

        # ── Answer callback IMMEDIATELY — stops Telegram from resending it ──
        _answer(bot, call.id)

        with state.active_checks_lock:
            fd = state.active_checks.get(f"file_{uid}")
            # Guard: if already parsing this uid, ignore duplicate callback
            if f"parsing_{uid}" in state.active_checks:
                return
            if not fd:
                return
            if fd.get("is_zip"):
                return
            # Mark as parsing to block any duplicate triggers
            state.active_checks[f"parsing_{uid}"] = True

        try:
            bot.edit_message_text(
                f"{E_HOURGLASS} {bold('Parsing combos...')} {E_GEAR}",
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

        def do_parse():
            try:
                db_inst = load_db()
                is_admin = call.from_user.id == ADMIN_ID
                lines = fd["content"].decode("utf-8", errors="ignore").splitlines()
                combos, total_lines, bad_lines = parse_combos(lines)
                valid = len(combos)
                approved = is_approved(db_inst, uid) or is_admin
                over_limit = not approved and total_lines > MAX_LINES

                sep = "\u2501" * 20
                summary_text = (
                    f"{E_FILE} {bold('File Summary')}\n"
                    f"{sep}\n"
                    f"{E_MEMO} File: {mono(fd['filename'])}\n"
                    f"{E_CHART} Total Lines: {mono(str(total_lines))}\n"
                    f"{E_CHECK} Valid Combos: {mono(str(valid))}\n"
                    f"{E_CROSS} Invalid/Skipped: {mono(str(bad_lines))}\n"
                    f"{E_BOLT} Threads: {mono(str(MASTER_THREADS))}\n"
                    f"{E_GLOBE} Proxies: {mono(str(len(init_proxies())))}\n"
                    f"{sep}"
                )

                if over_limit:
                    summary_text += (
                        f"\n{E_WARN} {bold(f'More than {MAX_LINES} lines!')}\n"
                        f"{E_MEMO} Only first {MAX_LINES} will be processed."
                    )
                    combos = combos[:MAX_LINES]
                    valid = len(combos)
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(f"{E_PLAY} Proceed (First {MAX_LINES})", callback_data=f"proceed_check_{uid}"),
                        types.InlineKeyboardButton(f"{E_STOP} Abort", callback_data=f"abort_check_{uid}")
                    )
                else:
                    if valid == 0:
                        try:
                            bot.edit_message_text(
                                f"{E_CROSS} {bold('No valid combos found!')}",
                                call.message.chat.id, call.message.message_id, parse_mode="HTML"
                            )
                        except Exception:
                            pass
                        return
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton(f"{E_PLAY} Start Checking", callback_data=f"proceed_check_{uid}"),
                        types.InlineKeyboardButton(f"{E_STOP} Abort", callback_data=f"abort_check_{uid}")
                    )

                summary_text += f"\n{E_GEAR} {italic('Dev: @RBX404')}"
                try:
                    bot.edit_message_text(
                        summary_text, call.message.chat.id, call.message.message_id,
                        parse_mode="HTML", reply_markup=markup
                    )
                except Exception:
                    pass

                with state.active_checks_lock:
                    state.active_checks[f"pending_{uid}"] = {
                        "combos": combos,
                        "total_lines": total_lines,
                        "bad_lines": bad_lines,
                        "message": fd["message"],
                        "loading_msg_id": call.message.message_id,
                    }
            finally:
                # Always release the parsing guard
                with state.active_checks_lock:
                    state.active_checks.pop(f"parsing_{uid}", None)

        threading.Thread(target=do_parse, daemon=True).start()

    @bot.callback_query_handler(func=lambda call: call.data.startswith("proceed_check_"))
    def cb_proceed_check(call):
        user = call.from_user
        uid = int(call.data.split("_")[-1])
        if user.id != uid:
            _answer(bot, call.id, "Not your check!", alert=True)
            return

        with state.active_checks_lock:
            pending_key = f"pending_{uid}"
            if pending_key not in state.active_checks:
                _answer(bot, call.id, "No pending check found!", alert=True)
                return
            if uid in state.active_checks:
                _answer(bot, call.id, "Already checking!", alert=True)
                return
            pending = state.active_checks.pop(pending_key)

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        cs = CheckerSession(uid, pending["combos"], pending["total_lines"], pending["bad_lines"])
        with state.active_checks_lock:
            state.active_checks[uid] = cs

        threading.Thread(target=run_checker, args=(cs, pending["message"], call.from_user), daemon=True).start()
        _answer(bot, call.id, f"Checking started! {MASTER_THREADS} threads")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("abort_check_"))
    def cb_abort_check(call):
        user = call.from_user
        uid = int(call.data.split("_")[-1])
        if user.id != uid:
            _answer(bot, call.id, "Not your check!", alert=True)
            return

        with state.active_checks_lock:
            pending_key = f"pending_{uid}"
            if pending_key in state.active_checks:
                del state.active_checks[pending_key]

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        bot.send_message(call.message.chat.id, f"{E_STOP} {bold('Check aborted!')}\n{E_GEAR} {italic('Dev: @RBX404')}", parse_mode="HTML")
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("get_hits_"))
    def cb_get_hits(call):
        user = call.from_user
        uid = int(call.data.split("_")[-1])
        if user.id != uid:
            _answer(bot, call.id, "Not your check!", alert=True)
            return

        with state.active_checks_lock:
            cs = state.active_checks.get(uid)

        if not cs:
            _answer(bot, call.id, "No active check found!", alert=True)
            return

        hits_text = build_hits_text(cs)
        if len(hits_text) > 4000:
            try:
                f = io.BytesIO(hits_text.encode("utf-8"))
                f.name = "current_hits.txt"
                bot.send_document(call.message.chat.id, f,
                                  caption=f"{E_FIRE} {bold('Current Hits')} ({len(cs.stats.all_hits)} total)\n{E_GEAR} {italic('Dev: @RBX404')}",
                                  parse_mode="HTML", reply_to_message_id=call.message.message_id)
            except:
                pass
        else:
            if hits_text == "No hits found yet.":
                _answer(bot, call.id, "No hits found yet!", alert=True)
                return
            bot.send_message(call.message.chat.id,
                             f"{E_FIRE} {bold('Current Hits:')}\n\n{pre(hits_text)}\n\n{E_GEAR} {italic('Dev: @RBX404')}",
                             parse_mode="HTML", reply_to_message_id=call.message.message_id)
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("stop_check_"))
    def cb_stop_check(call):
        user = call.from_user
        uid = int(call.data.split("_")[-1])
        if user.id != uid:
            _answer(bot, call.id, "Not your check!", alert=True)
            return

        with state.active_checks_lock:
            cs = state.active_checks.get(uid)

        if not cs:
            _answer(bot, call.id, "No active check found!", alert=True)
            return

        cs.stop_event.set()
        # Cancel all pending futures and shut down executor immediately
        if cs.executor:
            try:
                for fut in getattr(cs, 'futures', []):
                    fut.cancel()
                cs.executor.shutdown(wait=False, cancel_futures=True)
            except TypeError:
                cs.executor.shutdown(wait=False)
            except Exception:
                pass
        _answer(bot, call.id, "⛔ Stopped instantly!")

    @bot.message_handler(commands=['stop'])
    def cmd_stop(message):
        user = message.from_user
        uid = user.id
        db_inst = load_db()
        banned, reason = is_banned(db_inst, uid)
        if banned:
            bot.reply_to(message, f"{E_BAN} {bold('You are banned!')}\n{E_MEMO} Reason: {mono(reason)}", parse_mode="HTML")
            return

        def _kill_executor(cs):
            """Instantly cancel all pending futures and shut down executor."""
            cs.stop_event.set()
            if cs.executor:
                try:
                    for fut in getattr(cs, 'futures', []):
                        fut.cancel()
                    cs.executor.shutdown(wait=False, cancel_futures=True)
                except TypeError:
                    cs.executor.shutdown(wait=False)
                except Exception:
                    pass

        stopped_count = 0
        with state.active_checks_lock:
            pending_key = f"pending_{uid}"
            if pending_key in state.active_checks:
                del state.active_checks[pending_key]
                stopped_count += 1
            if uid in state.active_checks:
                _kill_executor(state.active_checks[uid])
                stopped_count += 1
            ck_pending_key = f"ck_pending_{uid}"
            if ck_pending_key in state.active_checks:
                del state.active_checks[ck_pending_key]
                stopped_count += 1
            ck_key = f"ck_{uid}"
            if ck_key in state.active_checks:
                _kill_executor(state.active_checks[ck_key])
                stopped_count += 1
            ib_pending_key = f"ib_pending_{uid}"
            if ib_pending_key in state.active_checks:
                del state.active_checks[ib_pending_key]
                stopped_count += 1
            ib_key = f"ib_{uid}"
            if ib_key in state.active_checks:
                _kill_executor(state.active_checks[ib_key])
                stopped_count += 1
            file_key = f"file_{uid}"
            if file_key in state.active_checks:
                del state.active_checks[file_key]

        if stopped_count > 0:
            bot.reply_to(message, f"{E_STOP} {bold('All active checks stopped!')}\n{E_GEAR} {italic('Dev: @RBX404')}", parse_mode="HTML")
        else:
            bot.reply_to(message, f"{E_WARN} {bold('No active check found!')}\n{E_GEAR} {italic('Dev: @RBX404')}", parse_mode="HTML")
