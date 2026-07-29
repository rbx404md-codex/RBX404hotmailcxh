import io
import threading
from telebot import types
from HOME import state


def _answer(bot, call_id, text=None, alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=alert)
    except:
        pass
from HOME.helpers import (
    bold, italic, mono, pre,
    E_FILE, E_CHART, E_CHECK, E_CROSS, E_BOLT, E_GEAR, E_MEMO,
    E_WARN, E_HOURGLASS, E_STOP, E_PLAY, E_FIRE
)
from HOME.cookie_session import CookieCheckerSession
from HOME.cookie_runner import run_cookie_checker, SERVICE_LABELS
from API.cookie_engine import (
    extract_cookie_files,
    count_valid_netflix, count_valid_chatgpt, count_valid_tiktok,
)
from CONFIG.config import ADMIN_ID


def _show_service_buttons(bot, chat_id, msg_id, uid, text="🍪 Choose cookie service to check:"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎬 Netflix",  callback_data=f"ck_svc_netflix_{uid}"),
        types.InlineKeyboardButton("🤖 ChatGPT",  callback_data=f"ck_svc_chatgpt_{uid}"),
    )
    markup.add(
        types.InlineKeyboardButton("🎵 TikTok",   callback_data=f"ck_svc_tiktok_{uid}"),
        types.InlineKeyboardButton("◀️ Back",      callback_data=f"mode_back_{uid}"),
    )
    bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id,
                          parse_mode="HTML", reply_markup=markup)


def register():
    bot = state.bot

    # ── Exit ──────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mode_exit_"))
    def cb_mode_exit(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "👋 Good Bye :)")
        # Clean up stored file
        with state.active_checks_lock:
            state.active_checks.pop(f"file_{uid}", None)
        _answer(bot, call.id)

    # ── Back to mode selection (M-HOTMAIL / Cookies / Exit) ───────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mode_back_"))
    def cb_mode_back(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            fd = state.active_checks.get(f"file_{uid}")
        if not fd:
            _answer(bot, call.id, "Session expired. Send file again.", alert=True)
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return
        fname = fd["filename"]
        fsize = fd["size"]
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 M-HOTMAIL", callback_data=f"mode_hotmail_{uid}"),
            types.InlineKeyboardButton("🍪 Cookies",   callback_data=f"mode_cookies_{uid}"),
        )
        markup.add(
            types.InlineKeyboardButton("📬 Inboxer",  callback_data=f"mode_inboxer_{uid}"),
            types.InlineKeyboardButton("❌ Exit",      callback_data=f"mode_exit_{uid}"),
        )
        bot.edit_message_text(
            f"{E_FILE} {bold('File received')}\n"
            f"{E_MEMO} Name: {mono(fname)}\n"
            f"{E_CHART} Size: {mono(f'{fsize/1024:.1f} KB')}\n\n"
            f"Choose checker mode:",
            chat_id=call.message.chat.id, message_id=call.message.message_id,
            parse_mode="HTML", reply_markup=markup
        )
        _answer(bot, call.id)

    # ── Cookies mode → show service selection ─────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mode_cookies_"))
    def cb_mode_cookies(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            fd = state.active_checks.get(f"file_{uid}")
        if not fd:
            _answer(bot, call.id, "Session expired. Send file again.", alert=True)
            return
        _show_service_buttons(bot, call.message.chat.id, call.message.message_id, uid)
        _answer(bot, call.id)

    # ── Service selected → count cookies ──────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ck_svc_"))
    def cb_ck_service(call):
        parts = call.data.split("_")
        # format: ck_svc_{service}_{uid}
        uid = int(parts[-1])
        service = parts[2]
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return

        # Answer IMMEDIATELY — stops Telegram from resending the callback
        _answer(bot, call.id)

        with state.active_checks_lock:
            fd = state.active_checks.get(f"file_{uid}")
            guard_key = f"ck_parsing_{uid}_{service}"
            if guard_key in state.active_checks:
                return
            if not fd:
                return
            state.active_checks[guard_key] = True

        try:
            bot.edit_message_text(
                f"{E_HOURGLASS} {bold('Processing file...')} {E_GEAR}",
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                parse_mode="HTML"
            )
        except Exception:
            pass

        def do_count():
            try:
                content = fd["content"]
                filename = fd["filename"]
                files = extract_cookie_files(content, filename)

                if service == "netflix":
                    count, cookie_list = count_valid_netflix(files)
                elif service == "chatgpt":
                    count, cookie_list = count_valid_chatgpt(files)
                elif service == "tiktok":
                    count, cookie_list = count_valid_tiktok(files)
                else:
                    count, cookie_list = 0, []

                svc_label = SERVICE_LABELS.get(service, service.upper())

                if count == 0:
                    markup = types.InlineKeyboardMarkup(row_width=2)
                    markup.add(
                        types.InlineKeyboardButton("◀️ Back", callback_data=f"mode_cookies_{uid}"),
                        types.InlineKeyboardButton("❌ Exit",  callback_data=f"mode_exit_{uid}"),
                    )
                    try:
                        bot.edit_message_text(
                            f"{E_CROSS} {bold(f'No valid {svc_label} cookies found!')}\n"
                            f"{E_MEMO} Check file format and try another service.",
                            chat_id=call.message.chat.id, message_id=call.message.message_id,
                            parse_mode="HTML", reply_markup=markup
                        )
                    except Exception:
                        pass
                    return

                # Store parsed cookies for start
                with state.active_checks_lock:
                    state.active_checks[f"ck_pending_{uid}"] = {
                        "service": service,
                        "cookie_list": cookie_list,
                        "message": fd["message"],
                    }

                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton(f"{E_PLAY} Start Checking", callback_data=f"ck_start_{uid}"),
                    types.InlineKeyboardButton(f"{E_STOP} Cancel",         callback_data=f"ck_cancel_{uid}"),
                )
                try:
                    bot.edit_message_text(
                        f"🍪 {bold(f'Cookie Checker — {svc_label}')}\n"
                        f"{E_GEAR} {italic('Dev: @RBX404')}\n\n"
                        f"{E_FILE} {bold('File:')} {mono(filename)}\n"
                        f"{E_CHECK} {bold('Valid cookies found:')} {mono(str(count))}\n"
                        f"{E_BOLT} {bold('Threads:')} {mono('30')}\n"
                        f"\n{E_GEAR} {italic('Ready to check')}",
                        chat_id=call.message.chat.id, message_id=call.message.message_id,
                        parse_mode="HTML", reply_markup=markup
                    )
                except Exception:
                    pass
            finally:
                with state.active_checks_lock:
                    state.active_checks.pop(f"ck_parsing_{uid}_{service}", None)

        threading.Thread(target=do_count, daemon=True).start()

    # ── Start cookie check ────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ck_start_"))
    def cb_ck_start(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return

        with state.active_checks_lock:
            if f"ck_{uid}" in state.active_checks:
                _answer(bot, call.id, "Already checking!", alert=True)
                return
            pending = state.active_checks.pop(f"ck_pending_{uid}", None)

        if not pending:
            _answer(bot, call.id, "No pending check! Send file again.", alert=True)
            return

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        cs = CookieCheckerSession(uid, pending["service"], pending["cookie_list"])
        with state.active_checks_lock:
            state.active_checks[f"ck_{uid}"] = cs

        threading.Thread(
            target=run_cookie_checker,
            args=(cs, pending["message"], call.from_user),
            daemon=True
        ).start()
        _answer(bot, call.id, f"Cookie check started! ({len(pending['cookie_list'])} cookies)")

    # ── Cancel ────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ck_cancel_"))
    def cb_ck_cancel(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            state.active_checks.pop(f"ck_pending_{uid}", None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id,
                         f"{E_STOP} {bold('Cookie check cancelled!')}\n{E_GEAR} {italic('Dev: @RBX404')}",
                         parse_mode="HTML")
        _answer(bot, call.id)

    # ── Get Hits (during check) ───────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ck_get_hits_"))
    def cb_ck_get_hits(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            cs = state.active_checks.get(f"ck_{uid}")
        if not cs:
            _answer(bot, call.id, "No active check found!", alert=True)
            return

        st = cs.stats
        svc_label = SERVICE_LABELS.get(cs.service, cs.service.upper())
        hit_label = "Hits" if cs.service == "tiktok" else "Premium"

        if not st.hits_list and not st.free_list:
            _answer(bot, call.id, f"No {hit_label.lower()} found yet!", alert=True)
            return

        lines = []
        for (src, result, cookies_dict, content, filename) in st.hits_list:
            if cs.service == "netflix":
                lines.append(f"[Netflix] {result.get('token','')[:30]}... | {src}")
            elif cs.service == "chatgpt":
                lines.append(f"[{result.get('plan','?')}] {result.get('email','?')} | {src}")
            elif cs.service == "tiktok":
                lines.append(f"[@{result.get('username','?')}] {_format_number(result.get('followers',0))} followers | {src}")
        for (src, result, cookies_dict, content, filename) in st.free_list:
            lines.append(f"[FREE] {result.get('email','?')} | {src}")

        hits_text = "\n".join(lines) if lines else "No hits yet."
        if len(hits_text) > 3800:
            try:
                f = io.BytesIO(hits_text.encode("utf-8"))
                f.name = "current_hits.txt"
                bot.send_document(call.message.chat.id, f,
                                  caption=f"{E_FIRE} {bold(f'Current {hit_label} [{svc_label}]')} ({len(st.hits_list)} found)\n{E_GEAR} {italic('Dev: @RBX404')}",
                                  parse_mode="HTML")
            except:
                pass
        else:
            bot.send_message(call.message.chat.id,
                             f"{E_FIRE} {bold(f'Current {hit_label} [{svc_label}]:')}\n\n{pre(hits_text)}\n\n{E_GEAR} {italic('Dev: @RBX404')}",
                             parse_mode="HTML")
        _answer(bot, call.id)

    # ── Stop ──────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ck_stop_"))
    def cb_ck_stop(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            cs = state.active_checks.get(f"ck_{uid}")
        if not cs:
            _answer(bot, call.id, "No active check found!", alert=True)
            return
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
        _answer(bot, call.id, "⛔ Stopped instantly!")


def _format_number(n) -> str:
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        elif n >= 1000:
            return f"{n/1000:.1f}K"
        return str(n)
    except:
        return str(n)
