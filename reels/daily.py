"""Har kungi avtomatik reels:
 1) o'z reels'laringiz statistikasini tahlil qiladi (qaysi uslub/mavzu/til ko'proq like yig'gan)
 2) yangiliklarni (RSS) o'qiydi - faqat mavzu ilhomi uchun
 3) AI (GitHub Models) bilan ma'noli iqtibos matni yozadi, xavfsizlik tekshiruvidan o'tkazadi
 4) videoni chizadi va Instagram'ga joylaydi
Ishga tushirish:  python reels/daily.py            (yasaydi va joylaydi)
                  python reels/daily.py --dry-run  (faqat yasaydi, joylamaydi)
"""
import json, os, random, re, sys, time, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from ig_client import IGClient, IGError  # noqa: E402
import render_quote  # noqa: E402

CONFIG = os.path.join(ROOT, "reels_config.json")
HISTORY = os.path.join(ROOT, "tahlil", "reels_tarix.json")
OUT = os.path.join(ROOT, "output")
TZ = timezone(timedelta(hours=5))
MODELS_URL = "https://models.github.ai/inference/chat/completions"


def log(msg):
    print(f"{datetime.now(TZ):%Y-%m-%d %H:%M} {msg}", flush=True)


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# ---------- 1. tahlil ----------
def update_stats(client, hist):
    """Oldin joylangan reels'larimizning like/komment sonini yangilaydi."""
    for h in hist[-40:]:
        if not h.get("media_id"):
            continue
        try:
            m = client.get(h["media_id"], fields="like_count,comments_count")
            h["like"] = m.get("like_count", 0); h["komment"] = m.get("comments_count", 0)
            h["ball"] = h["like"] + 3 * h["komment"]
        except IGError:
            pass
    return hist


def account_summary(client):
    try:
        ms = client.recent_media(limit=50)
    except IGError as e:
        log(f"tahlil xatosi: {e}"); return {}
    reels = [m for m in ms if (m.get("media_product_type") == "REELS")]
    best = sorted(reels, key=lambda m: -((m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)))[:5]
    hours = {}
    for m in reels:
        hr = (datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ)).hour
        hours.setdefault(hr, []).append(m.get("like_count") or 0)
    best_hour = max(hours, key=lambda k: sum(hours[k]) / len(hours[k])) if hours else None
    return {"reels_soni": len(reels), "eng_yaxshi_like": [m.get("like_count") for m in best],
            "eng_yaxshi_soat": best_hour}


def choose(options, hist, key, eps=0.3):
    """Ko'p like olgan variantni ko'proq tanlaydi, lekin yangisini ham sinab turadi."""
    scored = {}
    for h in hist:
        if h.get(key) in options and "ball" in h:
            scored.setdefault(h[key], []).append(h["ball"])
    untried = [o for o in options if o not in scored]
    if untried and random.random() < 0.6:
        return random.choice(untried)
    if not scored or random.random() < eps:
        return random.choice(options)
    return max(scored, key=lambda k: sum(scored[k]) / len(scored[k]))


# ---------- 2. yangiliklar ----------
def news(feeds, limit=12):
    titles = []
    for url in feeds:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for it in root.iter("item"):
                t = (it.findtext("title") or "").strip()
                if t:
                    titles.append(t)
                if len(titles) >= limit * len(feeds):
                    break
        except Exception as e:  # manba ishlamasa, boshqasi bilan davom etamiz
            log(f"yangilik manbasi o'qilmadi: {url} ({e.__class__.__name__})")
    random.shuffle(titles)
    return titles[:limit]


# ---------- 3. AI ----------
def llm(messages, models, temperature=0.9):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_MODELS_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN yo'q (GitHub Actions'da avtomatik beriladi)")
    last = None
    endpoints = [(MODELS_URL, lambda m: m),
                 ("https://models.inference.ai.azure.com/chat/completions", lambda m: m.split("/")[-1])]
    for url, name in endpoints:
        for model in models:
            for attempt in range(2):
                try:
                    r = requests.post(url, timeout=120, headers={
                        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
                        "Accept": "application/json"},
                        json={"model": name(model), "messages": messages, "temperature": temperature})
                    if r.status_code == 429:
                        log(f"AI limit (429), kutilyapti: {model}"); time.sleep(20 * (attempt + 1)); continue
                    try:
                        data = r.json()
                    except ValueError:
                        data = None
                    if r.status_code >= 400 or not data or "choices" not in data:
                        last = f"{url.split('/')[2]} {model}: HTTP {r.status_code} {r.text[:200]!r}"
                        log(f"AI xato: {last}"); break
                    return data["choices"][0]["message"]["content"]
                except requests.RequestException as e:
                    last = f"{model}: {e}"; log(f"AI tarmoq xatosi: {last}"); time.sleep(5)
    raise RuntimeError(f"AI javob bermadi: {last}")


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON topilmadi")
    return json.loads(m.group(0))


LANG_NAMES = {"ru": "rus tilida", "uz-cyrl": "o'zbek tilida, KIRILL yozuvida", "uz-latn": "o'zbek tilida, LOTIN yozuvida"}


def write_text(cfg, lang, theme, headlines, recent_texts):
    sys_prompt = (
        "Sen Instagram uchun qisqa, ma'noli, hissiy iqtibos-reels matnlarini yozadigan muallifsan. "
        "Matn ekranda fon ustida satrma-satr chiqadi. Faqat O'ZING YOZGAN original fikrlar yoz. "
        "Hech qachon real shaxslarga (yozuvchi, shoir, siyosatchi) so'z nisbat berma, qo'shiq so'zlarini ishlatma. "
        "Siyosat, din bo'yicha bahsli gaplar, fojialar, kimnidir kamsitish, tibbiy yoki moliyaviy maslahat bo'lmasin. "
        "Yangiliklardagi faktlarni takrorlama - ulardan faqat umumiy hayotiy mavzu ilhomi ol.")
    examples = "\n".join(f"- {e}" for e in cfg["muvaffaqiyatli_namunalar"])
    user = f"""Akkauntdagi eng ko'p like olgan reels'lar uslubi (ilhom uchun, ko'chirma):
{examples}

Bugungi mavzu: {theme}
Til: {LANG_NAMES.get(lang, lang)}
Bugungi yangiliklar sarlavhalari (faqat ilhom, faktlarni yozma):
{chr(10).join('- ' + h for h in headlines[:10]) or '- (yo`q)'}

Oxirgi matnlar (takrorlama):
{chr(10).join('- ' + t for t in recent_texts[-10:]) or '- (yo`q)'}

Talablar: matn 3-5 qisqa satr (har satr 2-6 so'z), jami 30 so'zdan oshmasin, oxirgi satr kuchli xulosa bo'lsin.
Faqat quyidagi JSON'ni qaytar:
{{"matn": "satr1\\nsatr2\\nsatr3\\nsatr4", "yuqori_yozuv": "2-4 so'zli kichik sarlavha (masalan 'Как-то так...')",
 "caption": "1-2 gapli izoh + savol (izoh yozishga undaydigan)", "heshteglar": ["#...", "... 8-12 ta"]}}"""
    raw = llm([{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}], cfg["ai_modellar"])
    return parse_json(raw)


def safe(cfg, data):
    text = data.get("matn", "") + " " + data.get("caption", "")
    if not (10 <= len(data.get("matn", "")) <= 260):
        return False, "uzunlik"
    for w in cfg.get("taqiqlangan_sozlar", []):
        if w.lower() in text.lower():
            return False, f"taqiqlangan so'z: {w}"
    verdict = llm([{"role": "system", "content": "Sen kontent moderatorisan. Faqat SAFE yoki UNSAFE deb javob ber."},
                   {"role": "user", "content": "Bu Instagram matni ommaviy blogga joylash uchun xavfsizmi? "
                    "UNSAFE: siyosat, nafrat, haqorat, zo'ravonlik, o'z joniga qasd, 18+, yolg'on fakt, real shaxsga uydirma iqtibos, "
                    "diniy bahs, tibbiy/moliyaviy maslahat.\n\n" + text}], cfg["ai_modellar"], temperature=0)
    return verdict.strip().upper().startswith("SAFE"), verdict.strip()[:40]


# ---------- asosiy ----------
def main(dry=False):
    cfg = load(CONFIG, {})
    hist = load(HISTORY, [])
    os.makedirs(OUT, exist_ok=True)
    client = None
    try:
        client = IGClient()
        hist = update_stats(client, hist)
        summary = account_summary(client)
        log(f"tahlil: {summary}")
    except IGError as e:
        log(f"Instagram'ga ulanib bo'lmadi: {e}")
        if not dry:
            raise

    lang = choose(cfg["tillar"], hist, "til")
    theme = choose(cfg["mavzular"], hist, "mavzu")
    style = choose(cfg["fonlar"], hist, "fon")
    headlines = news(cfg.get("yangilik_manbalari", []))
    log(f"tanlandi: til={lang} mavzu={theme} fon={style} yangiliklar={len(headlines)}")

    data = None
    for attempt in range(4):
        cand = write_text(cfg, lang, theme, headlines, [h.get("matn", "") for h in hist])
        ok, why = safe(cfg, cand)
        log(f"matn varianti {attempt + 1}: {'OK' if ok else 'rad etildi (' + why + ')'}")
        if ok:
            data = cand; break
    if not data:
        raise RuntimeError("Xavfsiz matn yozilmadi, bugun joylanmaydi")

    stamp = datetime.now(TZ).strftime("%Y%m%d_%H%M")
    path = os.path.join(OUT, f"reel_{stamp}.mp4")
    render_quote.render(data["matn"], path, style, seed=random.randint(1, 10 ** 6),
                        top_label=data.get("yuqori_yozuv") or None)
    tags = " ".join(data.get("heshteglar", [])[:12])
    caption = f"{data.get('caption', '').strip()}\n\n{tags}".strip()
    rec = {"sana": stamp, "til": lang, "mavzu": theme, "fon": style, "matn": data["matn"],
           "caption": caption, "fayl": os.path.basename(path)}
    if dry or not cfg.get("avto_joylash", True):
        log(f"joylanmadi (sinov/tasdiq rejimi): {path}")
    else:
        rec["media_id"] = client.publish_reel_file(path, caption)
        log(f"JOYLANDI: {rec['media_id']}")
    hist.append(rec)
    save(HISTORY, hist[-300:])
    with open(os.path.join(OUT, "oxirgi.txt"), "w", encoding="utf-8") as f:
        f.write(data["matn"] + "\n\n" + caption)
    return rec


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
