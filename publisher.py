"""schedule.csv dagi vaqti kelgan postlarni joylaydi.

schedule.csv ustunlari:
  vaqt      - 2026-11-26 19:00  (mahalliy vaqt, Toshkent/Samarqand)
  tur       - IMAGE | REELS | CAROUSEL | STORY
  media     - URL yoki fayl nomi; bir nechta bo'lsa | bilan ajrating
  matn      - caption (heshteglar bilan)
  holat     - bo'sh = kutilmoqda; skript o'zi "joylandi: <id>" yoki "xato: ..." yozadi
"""
import csv
import os
from datetime import datetime
from pathlib import Path

from ig_client import IGClient, IGError, load_env, BASE_DIR

SCHEDULE = BASE_DIR / "schedule.csv"
FIELDS = ["vaqt", "tur", "media", "matn", "holat"]


def resolve_url(item):
    item = item.strip()
    if item.lower().startswith(("http://", "https://")):
        return item
    base = os.environ.get("MEDIA_BASE_URL", "").rstrip("/")
    if not base:
        raise IGError(f"'{item}' URL emas. .env da MEDIA_BASE_URL ni belgilang yoki to'liq URL yozing.")
    return f"{base}/{item}"


def read_rows():
    if not SCHEDULE.exists():
        return []
    with SCHEDULE.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(rows):
    with SCHEDULE.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run(client=None, now=None, log=print):
    load_env()
    rows = read_rows()
    if not rows:
        return 0
    now = now or datetime.now()
    client = client or IGClient()
    done = 0
    for row in rows:
        if (row.get("holat") or "").strip():
            continue
        try:
            when = datetime.strptime(row["vaqt"].strip(), "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            row["holat"] = "xato: vaqt formati YYYY-MM-DD HH:MM bo'lishi kerak"
            continue
        if when > now:
            continue
        try:
            urls = [resolve_url(u) for u in row["media"].split("|") if u.strip()]
            if not urls:
                raise IGError("media bo'sh")
            media_id = client.publish(row.get("tur") or "IMAGE", urls, row.get("matn", ""))
            row["holat"] = f"joylandi: {media_id} ({datetime.now():%Y-%m-%d %H:%M})"
            log(f"[joylash] OK {row['vaqt']} -> {media_id}")
            done += 1
        except IGError as e:
            row["holat"] = f"xato: {e}"[:500]
            log(f"[joylash] XATO {row['vaqt']}: {e}")
        write_rows(rows)  # har bir postdan keyin saqlaymiz, qayta joylanmasligi uchun
    write_rows(rows)
    return done


if __name__ == "__main__":
    n = run()
    print(f"Joylangan postlar: {n}")
