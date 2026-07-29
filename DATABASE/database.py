import json
import threading
from datetime import datetime, timedelta
from CONFIG.config import DB_FILE

db_lock = threading.Lock()


def load_db():
    import os
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "users": {},
        "banned": {},
        "approved": {},
        "global_stats": {
            "total_checked": 0,
            "total_hits": 0,
            "total_lines_checked": 0
        }
    }


def save_db(db):
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)


def get_user(db, uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "username": "",
            "full_name": "",
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "total_checked": 0,
            "total_hits": 0,
            "total_lines": 0,
            "checks_count": 0
        }
    db["users"][uid]["last_seen"] = datetime.now().isoformat()
    return db["users"][uid]


def update_user_info(db, user):
    uid = str(user.id)
    u = get_user(db, uid)
    u["username"] = user.username or ""
    fn = user.first_name or ""
    ln = user.last_name or ""
    u["full_name"] = f"{fn} {ln}".strip()
    save_db(db)


def is_banned(db, uid):
    uid = str(uid)
    if uid not in db.get("banned", {}):
        return False, None
    ban = db["banned"][uid]
    if ban.get("days"):
        ban_date = datetime.fromisoformat(ban["date"])
        if datetime.now() > ban_date + timedelta(days=ban["days"]):
            del db["banned"][uid]
            save_db(db)
            return False, None
    return True, ban.get("reason", "No reason")


def is_approved(db, uid):
    uid = str(uid)
    if uid not in db.get("approved", {}):
        return False
    appr = db["approved"][uid]
    if appr.get("days"):
        appr_date = datetime.fromisoformat(appr["date"])
        if datetime.now() > appr_date + timedelta(days=appr["days"]):
            del db["approved"][uid]
            save_db(db)
            return False
    return True
