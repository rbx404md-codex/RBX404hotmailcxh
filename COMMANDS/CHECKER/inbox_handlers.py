import io
import threading
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, pre,
    E_FILE, E_CHART, E_CHECK, E_CROSS, E_BOLT, E_GEAR, E_MEMO,
    E_WARN, E_HOURGLASS, E_STOP, E_PLAY, E_FIRE, E_ROCKET
)
from HOME.inbox_session import InboxCheckerSession
from HOME.inbox_runner import run_inbox_checker, _build_status_msg
from API.inbox_engine import parse_inbox_combos
from CONFIG.config import ADMIN_ID, INBOXER_THREADS, MAX_LINES
from DATABASE.database import load_db, is_approved


def _answer(bot, call_id, text=None, alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=alert)
    except:
        pass


def register():
    bot = state.bot

    # ── Inboxer mode selected ─────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("mode_inboxer_"))
    def cb_mode_inboxer(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return

        # Answer IMMEDIATELY — stops Telegram from resending the callback
        _answer(bot, call.id)

        with state.active_checks_lock:
            fd = state.active_checks.get(f"file_{uid}")
            if f"ib_parsing_{uid}" in state.active_checks:
                return
            if not fd:
                return
            if fd.get("is_zip"):
                return
            state.active_checks[f"ib_parsing_{uid}"] = True

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
                combos, total_lines, bad_lines = parse_inbox_combos(lines)
                valid = len(combos)
                approved = is_approved(db_inst, uid) or is_admin
                over_limit = not approved and total_lines > MAX_LINES

                sep = "━" * 20
                summary_text = (
                    f"📬 {bold('Inboxer — File Summary')}\n"
                    f"{sep}\n"
                    f"{E_MEMO} File: {mono(fd['filename'])}\n"
                    f"{E_CHART} Total Lines: {mono(str(total_lines))}\n"
                    f"{E_CHECK} Valid Combos: {mono(str(valid))}\n"
                    f"{E_CROSS} Invalid/Skipped: {mono(str(bad_lines))}\n"
                    f"{E_BOLT} Threads: {mono(str(INBOXER_THREADS))}\n"
                    f"{sep}"
                )

                if over_limit:
                    summary_text += (f"\n{E_WARN} {bold(f'More than {MAX_LINES} lines!')}\n"
                                     f"{E_MEMO} Only first {MAX_LINES} will be processed.")
                    combos = combos[:MAX_LINES]
                    valid = len(combos)

                if valid == 0:
                    try:
                        bot.edit_message_text(
                            f"{E_CROSS} {bold('No valid combos found!')}\n"
                            f"{E_MEMO} File must contain email:pass lines.",
                            call.message.chat.id, call.message.message_id, parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    return

                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton(f"{E_PLAY} Start Inboxer", callback_data=f"ib_start_{uid}"),
                    types.InlineKeyboardButton(f"{E_STOP} Cancel",        callback_data=f"ib_cancel_{uid}"),
                )

                summary_text += f"\n{E_GEAR} {italic('Dev: @RBX404')}"
                try:
                    bot.edit_message_text(
                        summary_text,
                        call.message.chat.id, call.message.message_id,
                        parse_mode="HTML", reply_markup=markup
                    )
                except Exception:
                    pass

                with state.active_checks_lock:
                    state.active_checks[f"ib_pending_{uid}"] = {
                        "combos": combos,
                        "total_lines": total_lines,
                        "bad_lines": bad_lines,
                        "message": fd["message"],
                        "loading_msg_id": call.message.message_id,
                    }
            finally:
                with state.active_checks_lock:
                    state.active_checks.pop(f"ib_parsing_{uid}", None)

        threading.Thread(target=do_parse, daemon=True).start()

    # ── Start inbox check ─────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ib_start_"))
    def cb_ib_start(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return

        with state.active_checks_lock:
            if f"ib_{uid}" in state.active_checks:
                _answer(bot, call.id, "Already checking!", alert=True)
                return
            pending = state.active_checks.pop(f"ib_pending_{uid}", None)

        if not pending:
            _answer(bot, call.id, "No pending check! Send file again.", alert=True)
            return

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        cs = InboxCheckerSession(uid, pending["combos"])
        with state.active_checks_lock:
            state.active_checks[f"ib_{uid}"] = cs

        threading.Thread(
            target=run_inbox_checker,
            args=(cs, pending["message"], call.from_user),
            daemon=True
        ).start()
        _answer(bot, call.id, f"Inboxer started! ({len(pending['combos'])} combos)")

    # ── Cancel ────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ib_cancel_"))
    def cb_ib_cancel(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            state.active_checks.pop(f"ib_pending_{uid}", None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id,
                         f"{E_STOP} {bold('Inboxer cancelled!')}\n{E_GEAR} {italic('Dev: @RBX404')}",
                         parse_mode="HTML")
        _answer(bot, call.id)

    # ── Get Hits (during check) ───────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ib_get_hits_"))
    def cb_ib_get_hits(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            cs = state.active_checks.get(f"ib_{uid}")
        if not cs:
            _answer(bot, call.id, "No active check found!", alert=True)
            return

        st = cs.stats
        if not st.hits_list:
            _answer(bot, call.id, "No hits found yet!", alert=True)
            return

        lines = []
        for result in st.hits_list:
            email = result.get('email', '?')
            password = result.get('password', '?')
            profile = result.get('profile', {})
            services = result.get('services', [])
            name = profile.get('name', 'Unknown')
            country = profile.get('country', 'Unknown')
            svc_str = ', '.join(services[:5]) + ('...' if len(services) > 5 else '')
            lines.append(f"{email}:{password} | {name} | {country}\n  Services: {svc_str}")

        hits_text = "\n\n".join(lines)
        if len(hits_text) > 3800:
            try:
                f = io.BytesIO(hits_text.encode("utf-8"))
                f.name = "inbox_hits.txt"
                bot.send_document(call.message.chat.id, f,
                                  caption=f"{E_FIRE} {bold('Current Inbox Hits')} ({len(st.hits_list)} found)\n{E_GEAR} {italic('Dev: @RBX404')}",
                                  parse_mode="HTML")
            except:
                pass
        else:
            bot.send_message(call.message.chat.id,
                             f"{E_FIRE} {bold('Current Inbox Hits:')}\n\n{pre(hits_text)}\n\n{E_GEAR} {italic('Dev: @RBX404')}",
                             parse_mode="HTML")
        _answer(bot, call.id)

    # ── Stop ──────────────────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ib_stop_"))
    def cb_ib_stop(call):
        uid = int(call.data.split("_")[-1])
        if call.from_user.id != uid:
            _answer(bot, call.id, "Not your session!", alert=True)
            return
        with state.active_checks_lock:
            cs = state.active_checks.get(f"ib_{uid}")
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
