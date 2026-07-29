import os
import zipfile
import tempfile
from datetime import datetime
from API.checker_engine import fmt_svc
from HOME import state


def get_bot_username():
    try:
        info = state.bot.get_me()
        if info and info.username:
            return f"@{info.username}"
    except:
        pass
    return "@BlackoutZoneCheckerBot"


def build_hits_text(cs):
    lines = [f"{em}:{pw} | {cat} | {det}" for em, pw, cat, det in cs.stats.all_hits]
    return "\n".join(lines) if lines else "No hits found yet."


def build_result_zip(cs, user=None):
    import time
    st = cs.stats
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    tmpdir = tempfile.mkdtemp(prefix="checker_")
    odir = os.path.join(tmpdir, f"results_{ts}")
    os.makedirs(odir, exist_ok=True)
    bot_username = get_bot_username()

    def w(fn, lines):
        with open(os.path.join(odir, fn), "w", encoding="utf-8") as f:
            for l in lines:
                f.write(l + "\n")

    w("all_hits.txt", [f"{em}:{pw} | {cat} | {det}" for em, pw, cat, det in st.all_hits])

    svc_lines = []
    for em, pw, svcs in st.svc_results:
        svc_lines.append(f"{em}:{pw}")
        for i, s in enumerate(svcs):
            pfx = "  +-- " if i == len(svcs) - 1 else "  |-- "
            svc_lines.append(pfx + fmt_svc(s))
        svc_lines.append("-" * 50)
    w("services_hits.txt", svc_lines)

    all_svc_lines = []
    for em, pw, svcs in st.all_services:
        all_svc_lines.append(f"{em}:{pw}")
        for i, s in enumerate(svcs):
            pfx = "  +-- " if i == len(svcs) - 1 else "  |-- "
            all_svc_lines.append(pfx + fmt_svc(s))
        all_svc_lines.append("-" * 50)
    w("all_services.txt", all_svc_lines)

    w("balance_hits.txt", [f"{em}:{pw} | ${bal} {cur} | {holder}" for em, pw, bal, cur, holder in st.balance_list])
    w("rp_hits.txt", [f"[{pts}] {em}:{pw}" for em, pw, pts in sorted(st.rp_list, key=lambda x: x[2], reverse=True)])
    w("discord_promos.txt", [f"{em}:{pw} | {lnk} | {s2}" for em, pw, lnk, s2 in st.discord_list])
    w("xbox_codes.txt", [f"{em}:{pw} | {code} | {desc}" for em, pw, code, desc in st.xbox_code_list])

    # Nitro_Pulled folder
    nitro_pulled_dir = os.path.join(odir, "Nitro_Pulled")
    os.makedirs(nitro_pulled_dir, exist_ok=True)

    def w_nitro(fn, items):
        with open(os.path.join(nitro_pulled_dir, fn), "w", encoding="utf-8") as f:
            for em, pw, lnk, status in items:
                f.write(f"{em}:{pw}:{status}:{lnk}\n")

    # Categorize Discord promos by status
    nitro_valid = [item for item in st.discord_list if item[3] == "UNCLAIMED"]
    nitro_invalid = [item for item in st.discord_list if item[3] == "CLAIMED"]
    nitro_unknown = [item for item in st.discord_list if item[3] in ["EXPIRED", "INVALID", "UNKNOWN"]]

    w_nitro("Nitro_Valid.txt", nitro_valid)
    w_nitro("Nitro_Invalid.txt", nitro_invalid)
    w_nitro("Nitro_Unknown.txt", nitro_unknown)

    xbox_pulled_dir = os.path.join(odir, "xbox_pulled")
    os.makedirs(xbox_pulled_dir, exist_ok=True)

    def w_xbox(fn, items):
        with open(os.path.join(xbox_pulled_dir, fn), "w", encoding="utf-8") as f:
            for em, pw, name, code in items:
                f.write(f"{em}:{pw} \u2013 {name} \u2013 {code}\n")

    w_xbox("valid_xbox_codes.txt", st.xbox_pulled_by_status.get("VALID", []) + st.xbox_pulled_by_status.get("BALANCE_CODE", []))
    w_xbox("valid_cardrequired_codes.txt", st.xbox_pulled_by_status.get("VALID_REQUIRES_CARD", []))
    w_xbox("already_claimed.txt", st.xbox_pulled_by_status.get("REDEEMED", []))
    w_xbox("expired.txt", st.xbox_pulled_by_status.get("EXPIRED", []))
    w_xbox("invalid.txt", st.xbox_pulled_by_status.get("INVALID", []) + st.xbox_pulled_by_status.get("DEACTIVATED", []))
    w_xbox("unknown_codes.txt", st.xbox_pulled_by_status.get("UNKNOWN", []))
    w_xbox("region_locked_codes.txt", st.xbox_pulled_by_status.get("REGION_LOCKED", []))
    w_xbox("rate_limited.txt", st.xbox_pulled_by_status.get("RATE_LIMITED", []))
    w_xbox("errors.txt", st.xbox_pulled_by_status.get("ERROR", []))

    w("psn_hits.txt", [f"{em}:{pw} | Orders: {n}" for em, pw, n in st.psn_list])
    w("steam_hits.txt", [f"{em}:{pw} | Items: {n}" for em, pw, n in st.steam_list])
    w("supercell_hits.txt", [f"{em}:{pw} | {','.join(g) if isinstance(g, list) else g}" for em, pw, g in st.supercell_list])

    tt_lines = []
    for em, pw, tt in st.tiktok_list:
        if isinstance(tt, dict):
            flw = tt.get('followers', 0)
            verified = " ✓" if tt.get('verified') else ""
            tt_lines.append(f"{em}:{pw} | @{tt.get('username', 'N/A')} | Followers: {flw:,}{verified} | Likes: {tt.get('likes', 0):,} | Videos: {tt.get('videos', 0)}")
        else:
            tt_lines.append(f"{em}:{pw} | {tt}")
    w("tiktok_hits.txt", tt_lines)

    ig_lines = []
    for em, pw, ig in st.instagram_list:
        if isinstance(ig, dict):
            flw = ig.get('followers', 0)
            verified = " ✓" if ig.get('verified') else ""
            ig_lines.append(f"{em}:{pw} | @{ig.get('username', 'N/A')} | Followers: {flw:,}{verified} | Posts: {ig.get('posts', 0):,} | Following: {ig.get('following', 0):,}")
        else:
            ig_lines.append(f"{em}:{pw} | {ig}")
    w("instagram_hits.txt", ig_lines)

    w("minecraft_hits.txt", [f"{em}:{pw} | {n}" for em, pw, n in st.minecraft_list])
    w("bad.txt", st.bad_list)
    w("2fa.txt", st.twofa_list)
    w("errors.txt", st.error_list)

    elapsed = time.time() - cs.started
    cpm = int((st.checked / elapsed) * 60) if elapsed > 1 else 0
    checked_by = "N/A"
    checked_by_link = ""
    if user:
        fn = user.first_name or ""
        ln = user.last_name or ""
        checked_by = f"{fn} {ln}".strip() or "User"
        checked_by_link = f"@{user.username}" if user.username else f"tg://user?id={user.id}"

    tiktok_top = sorted(st.tiktok_followers_ranges.items(), key=lambda x: x[1], reverse=True)[:3]
    instagram_top = sorted(st.instagram_followers_ranges.items(), key=lambda x: x[1], reverse=True)[:3]
    tt_ranges_str = ", ".join([f"{r}:{c}" for r, c in tiktok_top if c > 0]) or "None"
    ig_ranges_str = ", ".join([f"{r}:{c}" for r, c in instagram_top if c > 0]) or "None"

    w("summary.txt", [
        "Blackout Zone Checker - Summary", "",
        "Dev: @RBX404", f"Bot: {bot_username}", "",
        f"Checked by: {checked_by} ({checked_by_link})",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "",
        f"Total Lines: {st.total} | Valid: {st.valid} | Skipped: {st.bad_lines}",
        f"Checked: {st.checked} | CPM: {cpm}", "",
        "--- RESULTS ---",
        f"PSN: {st.psn} | STEAM: {st.steam} | SUPERCELL: {st.supercell}",
        f"TIKTOK: {st.tiktok} (Top Ranges: {tt_ranges_str})",
        f"INSTAGRAM: {st.instagram} (Top Ranges: {ig_ranges_str})",
        f"MINECRAFT: {st.minecraft} | XBOX CODES: {st.xbox_codes} | XBOX PULLED: {st.xbox_pulled} (Valid: {st.xbox_pulled_valid})",
        f"DISCORD: {st.discord_total} (Valid: {st.discord_valid}, Claimed: {st.discord_claimed}, Unk: {st.discord_unk})",
        f"BALANCE >$0: {st.balance} | RP HITS: {st.rp_hits} ({st.rp_total_pts} pts)",
        f"XGPU: {st.xgpu} | XGPP: {st.xgpp} | XGPE: {st.xgpe} | M365: {st.m365} | OTHER: {st.other_svc}", "",
        "--- NEGATIVES ---",
        f"BAD: {st.bad} | 2FA: {st.twofa} | ERRORS: {st.errors}",
        f"RETRIES: {st.retries} | PROXY ERR: {st.proxy_err}",
    ])

    zip_path = os.path.join(tmpdir, f"results_master_{ts}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(odir):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, tmpdir))

    return zip_path, tmpdir
