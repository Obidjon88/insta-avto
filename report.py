"""Oxirgi postlar statistikasi: CSV + HTML hisobot (hisobotlar/ papkasida)."""
import csv
import html
from collections import defaultdict
from datetime import datetime, timedelta

from ig_client import IGClient, BASE_DIR

OUT_DIR = BASE_DIR / "hisobotlar"
METRICS = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"]
WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
LOCAL_OFFSET = timedelta(hours=5)  # Toshkent/Samarqand vaqti (UTC+5)


def run(client=None, limit=30, log=print):
    client = client or IGClient()
    OUT_DIR.mkdir(exist_ok=True)
    acc = client.me()
    rows = []
    for m in client.recent_media(limit=limit):
        ins = client.media_insights(m["id"], METRICS)
        ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        local = ts.replace(tzinfo=None) + LOCAL_OFFSET
        reach = ins.get("reach") or 0
        inter = ins.get("total_interactions")
        if inter is None:
            inter = sum((ins.get(k) or 0) for k in ("shares", "saved")) + (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        rows.append({
            "sana": local.strftime("%Y-%m-%d %H:%M"),
            "kun": WEEKDAYS[local.weekday()],
            "soat": local.hour,
            "tur": m.get("media_product_type") or m.get("media_type"),
            "reach": reach,
            "views": ins.get("views"),
            "likes": ins.get("likes") if ins.get("likes") is not None else m.get("like_count"),
            "comments": ins.get("comments") if ins.get("comments") is not None else m.get("comments_count"),
            "shares": ins.get("shares"),
            "saved": ins.get("saved"),
            "interaksiya": inter,
            "ER_%": round(100 * inter / reach, 2) if reach else None,
            "matn": (m.get("caption") or "").replace("\n", " ")[:80],
            "link": m.get("permalink"),
        })

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = OUT_DIR / f"statistika_{stamp}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    def avg_by(key):
        agg = defaultdict(list)
        for r in rows:
            agg[r[key]].append(r["reach"] or 0)
        return sorted(((k, sum(v) / len(v), len(v)) for k, v in agg.items()), key=lambda x: -x[1])

    by_hour, by_day, by_type = avg_by("soat"), avg_by("kun"), avg_by("tur")
    top = sorted(rows, key=lambda r: (-(r["reach"] or 0), -(r["interaksiya"] or 0)))[:5]

    def table(items, title, label):
        trs = "".join(f"<tr><td>{html.escape(str(k))}{label}</td><td>{v:,.0f}</td><td>{n}</td></tr>"
                      for k, v, n in items)
        return f"<h2>{title}</h2><table><tr><th></th><th>O'rtacha reach</th><th>Postlar</th></tr>{trs}</table>"

    top_html = "".join(
        f"<tr><td>{r['sana']}</td><td>{r['tur']}</td><td>{r['reach']:,}</td><td>{r['ER_%']}</td>"
        f"<td><a href='{html.escape(r['link'] or '')}'>{html.escape(r['matn'][:50]) or 'post'}</a></td></tr>"
        for r in top)
    page = f"""<!doctype html><html lang="uz"><meta charset="utf-8">
<title>Instagram hisobot {stamp}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:860px;margin:30px auto;padding:0 16px;color:#222}}
table{{border-collapse:collapse;width:100%;margin-bottom:24px}}td,th{{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left}}
th{{background:#f4f4f4}}.kpi{{display:flex;gap:16px}}.kpi div{{background:#f4f4f4;padding:12px 16px;border-radius:8px}}</style>
<h1>@{html.escape(acc.get('username',''))} — hisobot</h1>
<div class="kpi"><div>Obunachilar<br><b>{acc.get('followers_count','?'):,}</b></div>
<div>Tahlil qilingan postlar<br><b>{len(rows)}</b></div>
<div>O'rtacha reach<br><b>{(sum(r['reach'] or 0 for r in rows)/len(rows) if rows else 0):,.0f}</b></div></div>
<h2>Eng yaxshi 5 post</h2><table><tr><th>Sana</th><th>Tur</th><th>Reach</th><th>ER %</th><th>Post</th></tr>{top_html}</table>
{table(by_type, "Format bo'yicha", "")}
{table(by_day, "Hafta kuni bo'yicha", "")}
{table(by_hour, "Joylangan soat bo'yicha", ":00")}
<p style="color:#888">Vaqtlar UTC+5 bo'yicha. Kam postli guruhlarga ehtiyot bo'lib qarang.</p></html>"""
    html_path = OUT_DIR / f"hisobot_{stamp}.html"
    html_path.write_text(page, encoding="utf-8")
    log(f"[hisobot] {html_path.name} va {csv_path.name} tayyor")
    return html_path


if __name__ == "__main__":
    p = run()
    print(f"Ochish: {p}")
