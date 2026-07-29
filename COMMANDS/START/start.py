import time
from telebot import types
from HOME import state
from HOME.helpers import (
    bold, italic, mono, make_progress_bar,
    get_profile_photo, user_full_link,
    E_WAVE, E_SPARKLE, E_ROBOT, E_SHIELD, E_GREEN, E_CLOCK, E_USER, E_GLOBE,
    E_CHART, E_FIRE, E_DIAMOND, E_CHECK, E_CROWN, E_HEART, E_ROCKET, E_CROSS,
    E_GEAR, E_BAN, E_MEMO, E_PIN, E_KEY, E_STOP, E_STAR, E_BOLT
)
from DATABASE.database import load_db, update_user_info, is_banned, is_approved, get_user
from PROXY.proxy import init_proxies
from CONFIG.config import ADMIN_ID, MAX_LINES, MASTER_THREADS, INBOXER_THREADS, COOKIES_THREADS, DEFAULT_THREADS


def _answer(bot, call_id, text=None, alert=False):
    """Silently answer callback queries — Telegram expires them after 30s."""
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=alert)
    except:
        pass


def register():
    bot = state.bot

    @bot.message_handler(commands=['start'])
    def cmd_start(message):
        user = message.from_user
        db_inst = load_db()
        update_user_info(db_inst, user)

        banned, reason = is_banned(db_inst, user.id)
        if banned:
            bot.reply_to(message, f"{E_BAN} {bold('You are banned!')}\n{E_MEMO} Reason: {mono(reason or 'No reason')}", parse_mode="HTML")
            return

        uptime = time.time() - state.BOT_START_TIME
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        total_users = len(db_inst.get("users", {}))
        total_proxies = len(init_proxies())
        g = db_inst.get("global_stats", {})

        welcome_text = f"""{E_WAVE} {bold('Welcome to Blackout Zone Checker!')}

{E_SPARKLE} Hello, {user_full_link(user)}!
{E_ROBOT} {italic('Your all-in-one account checker')}

{E_SHIELD} {bold('Bot Health:')}
{E_GREEN} Status: {mono('Online')}
{E_CLOCK} Uptime: {mono(uptime_str)}
{E_USER} Total Users: {mono(str(total_users))}
{E_GLOBE} Proxies Loaded: {mono(str(total_proxies))}
{E_CHART} Total Checked: {mono(str(g.get('total_checked', 0)))}
{E_FIRE} Total Hits: {mono(str(g.get('total_hits', 0)))}

{E_DIAMOND} {bold('Features:')}
{E_CHECK} PSN / Steam / Supercell / TikTok
{E_CHECK} Minecraft / Xbox Codes / Xbox Pulled / Discord
{E_CHECK} Balance / Rewards Points
{E_CHECK} Game Pass / M365 Services
{E_CHECK} Fast Multi-threaded Checking
{E_STAR} 🍪 Cookie Checker — Netflix / ChatGPT / TikTok
{E_STAR} 📬 Inboxer — 200+ Services Detection

{E_CROWN} {italic('Dev: @RBX404')}
{E_HEART} {italic('Enjoy using the bot!')}"""

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{E_ROCKET} Checker", callback_data="open_checker"),
            types.InlineKeyboardButton(f"{E_USER} My Profile", callback_data="my_profile"),
        )
        markup.add(
            types.InlineKeyboardButton(f"{E_GLOBE} Bot Status", callback_data="bot_status"),
            types.InlineKeyboardButton(f"{E_CROSS} Exit", callback_data="exit_bot"),
        )

        photo = get_profile_photo(user.id)
        if photo:
            try:
                bot.send_photo(message.chat.id, photo, caption=welcome_text,
                               parse_mode="HTML", reply_to_message_id=message.message_id, reply_markup=markup)
                return
            except:
                pass
        bot.reply_to(message, welcome_text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

    @bot.callback_query_handler(func=lambda call: call.data == "open_checker")
    def cb_open_checker(call):
        user = call.from_user
        db_inst = load_db()
        banned, reason = is_banned(db_inst, user.id)
        if banned:
            _answer(bot, call.id, "You are banned!", alert=True)
            return

        is_admin = user.id == ADMIN_ID
        with state.active_checks_lock:
            if user.id in state.active_checks and not is_admin:
                _answer(bot, call.id, "You already have an active check running!", alert=True)
                return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"{E_CROSS} Back to Menu", callback_data="back_to_menu"))

        approved = is_approved(db_inst, user.id) or is_admin
        limit_text = "Unlimited (Admin)" if is_admin else ("Unlimited (Approved)" if approved else f"Max {MAX_LINES} lines")

        text = f"""{E_ROCKET} {bold('Checker — Send Your File')}

{E_MEMO} {bold('M-HOTMAIL Checker:')}
{E_PIN} Format: {mono('email:password')}
{E_PIN} Lines limit: {mono(limit_text)}
{E_PIN} File: {mono('.txt only')}

{E_STAR} {bold('🍪 Cookie Checker:')}
{E_PIN} Services: {mono('Netflix / ChatGPT / TikTok')}
{E_PIN} Format: {mono('Netscape / JSON / key=value')}
{E_PIN} File: {mono('.txt or .zip')}

{E_STAR} {bold('📬 Inboxer:')}
{E_PIN} Detect {mono('200+ services')} in inbox
{E_PIN} PSN / Games / Social / Payment / Proxy
{E_PIN} File: {mono('.txt only (email:pass)')}

{E_CHECK} {bold('Note')} — Proxies already loaded! {E_GEAR}
{E_BOLT} Threads: Hotmail {mono(str(MASTER_THREADS))} / Inbox {mono(str(INBOXER_THREADS))} / Cookies {mono(str(COOKIES_THREADS))}
{E_GLOBE} Proxies: {mono(str(len(init_proxies())))}

{E_MEMO} {italic('Send your .txt or .zip file to begin!')}
{E_GEAR} {italic('Dev: @RBX404')}"""

        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                  parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        except:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "my_profile")
    def cb_my_profile(call):
        user = call.from_user
        db_inst = load_db()
        u = get_user(db_inst, user.id)

        is_prem = getattr(user, 'is_premium', False) or False
        prem_text = f"{E_DIAMOND} Yes" if is_prem else f"{E_CROSS} No"
        approved = is_approved(db_inst, user.id)
        rank = f"{E_CROWN} Admin" if user.id == ADMIN_ID else (f"{E_CROWN} Approved" if approved else f"{E_USER} Normal")

        text = f"""{E_USER} {bold('My Profile')}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_SPARKLE} {bold('Name:')} {user_full_link(user)}
{E_PIN} {bold('Username:')} {mono('@' + user.username if user.username else 'N/A')}
{E_KEY} {bold('User ID:')} {mono(str(user.id))}
{E_MEMO} {bold('Chat ID:')} {mono(str(call.message.chat.id))}
{E_DIAMOND} {bold('Premium:')} {prem_text}
{E_SHIELD} {bold('Rank:')} {rank}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_CHART} {bold('Statistics:')}
{E_CHECK} Total Checked: {mono(str(u.get('total_checked', 0)))}
{E_FIRE} Total Hits: {mono(str(u.get('total_hits', 0)))}
{E_GLOBE} Total Lines: {mono(str(u.get('total_lines', 0)))}
{E_BOLT} Total Checks: {mono(str(u.get('checks_count', 0)))}
{E_CLOCK} First Seen: {mono(u.get('first_seen', 'N/A')[:10])}
{E_CLOCK} Last Seen: {mono(u.get('last_seen', 'N/A')[:10])}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GEAR} {italic('Dev: @RBX404')}"""

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"{E_CROSS} Back to Menu", callback_data="back_to_menu"))

        photo = get_profile_photo(user.id)
        if photo:
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            try:
                bot.send_photo(call.message.chat.id, photo, caption=text, parse_mode="HTML", reply_markup=markup)
                _answer(bot, call.id)
                return
            except:
                pass

        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                  parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        except:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "bot_status")
    def cb_bot_status(call):
        db_inst = load_db()
        uptime = time.time() - state.BOT_START_TIME
        uptime_str = time.strftime("%Hh %Mm %Ss", time.gmtime(uptime))
        total_users = len(db_inst.get("users", {}))
        total_proxies = len(init_proxies())
        g = db_inst.get("global_stats", {})

        with state.active_checks_lock:
            current_checks = len(state.active_checks)

        text = f"""{E_ROBOT} {bold('Bot Status')}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GREEN} Status: {mono('Online')}
{E_CLOCK} Uptime: {mono(uptime_str)}
{E_USER} Total Users: {mono(str(total_users))}
{E_GLOBE} Proxies: {mono(str(total_proxies))}
{E_BOLT} Active Checks: {mono(str(current_checks))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_CHART} {bold('Global Stats:')}
{E_CHECK} Total Checked: {mono(str(g.get('total_checked', 0)))}
{E_FIRE} Total Hits: {mono(str(g.get('total_hits', 0)))}
{E_GLOBE} Total Lines: {mono(str(g.get('total_lines_checked', 0)))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GEAR} {italic('Dev: @RBX404')}"""

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"{E_CROSS} Back to Menu", callback_data="back_to_menu"))
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                                  parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        except:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "exit_bot")
    def cb_exit(call):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        try:
            bot.send_animation(call.message.chat.id, "https://t.me/conflicthistor/1401255",
                               caption=f"{E_WAVE} Bye :)\n{E_GEAR} {italic('Dev: @RBX404')}", parse_mode="HTML")
        except:
            bot.send_message(call.message.chat.id, f"{E_WAVE} Bye :)\n{E_GEAR} {italic('Dev: @RBX404')}", parse_mode="HTML")
        _answer(bot, call.id)

    @bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
    def cb_back_to_menu(call):
        user = call.from_user
        db_inst = load_db()
        uptime = time.time() - state.BOT_START_TIME
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        total_users = len(db_inst.get("users", {}))
        total_proxies = len(init_proxies())
        g = db_inst.get("global_stats", {})

        welcome_text = f"""{E_WAVE} {bold('Welcome to Blackout Zone Checker!')}

{E_SPARKLE} Hello, {user_full_link(user)}!
{E_ROBOT} {italic('Your all-in-one account checker')}

{E_SHIELD} {bold('Bot Health:')}
{E_GREEN} Status: {mono('Online')}
{E_CLOCK} Uptime: {mono(uptime_str)}
{E_USER} Total Users: {mono(str(total_users))}
{E_GLOBE} Proxies Loaded: {mono(str(total_proxies))}
{E_CHART} Total Checked: {mono(str(g.get('total_checked', 0)))}
{E_FIRE} Total Hits: {mono(str(g.get('total_hits', 0)))}

{E_DIAMOND} {bold('Features:')}
{E_CHECK} PSN / Steam / Supercell / TikTok
{E_CHECK} Minecraft / Xbox Codes / Xbox Pulled / Discord
{E_CHECK} Balance / Rewards Points
{E_CHECK} Game Pass / M365 Services
{E_CHECK} Fast Multi-threaded Checking
{E_STAR} 🍪 Cookie Checker — Netflix / ChatGPT / TikTok
{E_STAR} 📬 Inboxer — 200+ Services Detection

{E_CROWN} {italic('Dev: @RBX404')}
{E_HEART} {italic('Enjoy using the bot!')}"""

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{E_ROCKET} Checker", callback_data="open_checker"),
            types.InlineKeyboardButton(f"{E_USER} My Profile", callback_data="my_profile"),
        )
        markup.add(
            types.InlineKeyboardButton(f"{E_GLOBE} Bot Status", callback_data="bot_status"),
            types.InlineKeyboardButton(f"{E_CROSS} Exit", callback_data="exit_bot"),
        )

        try:
            if call.message.content_type == 'photo':
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, welcome_text, parse_mode="HTML",
                                 reply_markup=markup, disable_web_page_preview=True)
            else:
                bot.edit_message_text(welcome_text, call.message.chat.id, call.message.message_id,
                                      parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        except:
            bot.send_message(call.message.chat.id, welcome_text, parse_mode="HTML",
                             reply_markup=markup, disable_web_page_preview=True)
        _answer(bot, call.id)
