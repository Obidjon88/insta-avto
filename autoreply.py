"""Kommentlarga avtomatik javob + Direct (private reply).

rules.json dagi qoidalar bo'yicha ishlaydi. Har bir kommentga faqat bir marta javob beriladi
(javob berilganlar state.json da saqlanadi).
"""
import json
from datetime import datetime, timedelta, timezone

from ig_client import IGClient, IGError, BASE_DIR

RULES_FILE = BASE_DIR / "rules.json"
STATE_FILE = BASE_DIR / "state.json"


def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return default


def save_state(state):
    # juda kattalashib ketmasin
    state["javob_berilgan"] = state.get("javob_berilgan", [])[-5000:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def match_rule(text, rules):
    t = (text or "").lower()
    for rule in rules.get("qoidalar", []):
        for kw in rule.get("kalit_sozlar", []):
            if kw.lower() in t:
                return rule
    return rules.get("umumiy_javob") if rules.get("umumiy_javob", {}).get("yoqilgan") else None


def fill(template, username):
    return (template or "").replace("{username}", username or "")


def run(client=None, log=print):
    rules = load_json(RULES_FILE, {})
    if not rules.get("yoqilgan", True):
        return 0
    state = load_json(STATE_FILE, {})
    seen = set(state.get("javob_berilgan", []))
    client = client or IGClient()

    own = state.get("username")
    if not own:
        own = client.me().get("username", "")
        state["username"] = own

    # Birinchi ishga tushirishda eski kommentlarga javob yozib yubormaslik uchun
    first_run = "boshlangan" not in state
    skip_old = first_run and not rules.get("eski_kommentlarga_javob", False)
    state.setdefault("boshlangan", datetime.now().isoformat(timespec="minutes"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)  # Direct faqat 7 kun ichida mumkin
    count = 0
    for media in client.recent_media(limit=int(rules.get("tekshiriladigan_postlar", 10))):
        if not media.get("comments_count"):
            continue
        for c in client.comments(media["id"]):
            cid = c["id"]
            if cid in seen:
                continue
            if skip_old:
                seen.add(cid)
                continue
            user = c.get("username") or (c.get("from") or {}).get("username", "")
            if user and own and user.lower() == own.lower():
                seen.add(cid)
                continue
            rule = match_rule(c.get("text"), rules)
            if not rule:
                seen.add(cid)
                continue
            try:
                if rule.get("javob"):
                    client.reply_comment(cid, fill(rule["javob"], user))
                ts = c.get("timestamp")
                fresh = True
                if ts:
                    fresh = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z") > cutoff
                if rule.get("direct") and fresh:
                    try:
                        client.private_reply(cid, fill(rule["direct"], user))
                    except IGError as e:
                        log(f"[javob] Direct yuborilmadi (@{user}): {e}")
                log(f"[javob] @{user}: '{(c.get('text') or '')[:40]}'")
                count += 1
            except IGError as e:
                log(f"[javob] XATO @{user}: {e}")
            seen.add(cid)
            state["javob_berilgan"] = list(seen)
            save_state(state)
    state["javob_berilgan"] = list(seen)
    save_state(state)
    return count


if __name__ == "__main__":
    print(f"Javob berilgan kommentlar: {run()}")
