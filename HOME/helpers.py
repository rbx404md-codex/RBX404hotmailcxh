from HOME import state

E_CHECK = "\u2705"
E_CROSS = "\u274C"
E_FIRE = "\U0001F525"
E_STAR = "\u2B50"
E_LOCK = "\U0001F512"
E_UNLOCK = "\U0001F513"
E_CHART = "\U0001F4CA"
E_FOLDER = "\U0001F4C1"
E_FILE = "\U0001F4C4"
E_USER = "\U0001F464"
E_CROWN = "\U0001F451"
E_GEAR = "\u2699\uFE0F"
E_ROCKET = "\U0001F680"
E_GLOBE = "\U0001F30D"
E_SHIELD = "\U0001F6E1"
E_BELL = "\U0001F514"
E_STOP = "\U0001F6D1"
E_PLAY = "\u25B6\uFE0F"
E_HOURGLASS = "\u23F3"
E_SPARKLE = "\u2728"
E_DIAMOND = "\U0001F48E"
E_HEART = "\u2764\uFE0F"
E_WAVE = "\U0001F44B"
E_PARTY = "\U0001F389"
E_ROBOT = "\U0001F916"
E_MONEY = "\U0001F4B0"
E_GAME = "\U0001F3AE"
E_MUSIC = "\U0001F3B5"
E_WARN = "\u26A0\uFE0F"
E_BAN = "\U0001F6AB"
E_PIN = "\U0001F4CC"
E_LINK = "\U0001F517"
E_BOLT = "\u26A1"
E_GIFT = "\U0001F381"
E_KEY = "\U0001F511"
E_MEMO = "\U0001F4DD"
E_BOOM = "\U0001F4A5"
E_CAMERA = "\U0001F4F7"
E_COOL = "\U0001F60E"
E_THUMB = "\U0001F44D"
E_EYES = "\U0001F440"
E_CLOCK = "\U0001F552"
E_GREEN = "\U0001F7E2"
E_RED = "\U0001F534"
E_YELLOW = "\U0001F7E1"
E_BLUE = "\U0001F535"
E_PURPLE = "\U0001F7E3"
E_ORANGE = "\U0001F7E0"


def mono(text): return f"<code>{text}</code>"
def bold(text): return f"<b>{text}</b>"
def italic(text): return f"<i>{text}</i>"
def uline(text): return f"<u>{text}</u>"
def link(text, url): return f'<a href="{url}">{text}</a>'
def pre(text): return f"<pre>{text}</pre>"
def strike(text): return f"<s>{text}</s>"


def make_progress_bar(current, total, length=20):
    pct = current / total if total else 0
    filled = int(length * pct)
    bar = "\u2588" * filled + "\u2591" * (length - filled)
    return f"{bar} {pct*100:.1f}%"


def get_profile_photo(user_id):
    try:
        photos = state.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            return photos.photos[0][-1].file_id
    except:
        pass
    return None


def user_link(user):
    name = user.first_name or "User"
    if user.username:
        return f'<a href="https://t.me/{user.username}">{name}</a>'
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def user_full_link(user):
    fn = user.first_name or ""
    ln = user.last_name or ""
    full = f"{fn} {ln}".strip() or "User"
    if user.username:
        return f'<a href="https://t.me/{user.username}">{full}</a>'
    return f'<a href="tg://user?id={user.id}">{full}</a>'
