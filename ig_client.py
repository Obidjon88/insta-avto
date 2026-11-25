"""Instagram API (Business Login for Instagram) uchun kichik klient.

Barcha so'rovlar graph.instagram.com orqali ketadi. Facebook sahifa shart emas.
"""
import json
import os
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_env(override=False):
    """.env faylni o'qiydi (python-dotenv kerak emas)."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip('"').strip("'")
            if override:
                os.environ[key.strip()] = val
            else:
                os.environ.setdefault(key.strip(), val)


def save_env_value(key, value):
    """.env ichidagi bitta qiymatni yangilaydi (token yangilanganda)."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[i] = f"{key}={value}"
            found = True
    if not found:
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


class IGError(Exception):
    pass


class IGClient:
    def __init__(self, token=None, user_id=None, version=None):
        load_env()
        self.token = token or os.environ.get("IG_ACCESS_TOKEN", "")
        self.user_id = user_id or os.environ.get("IG_USER_ID", "me") or "me"
        self.version = version or os.environ.get("IG_API_VERSION", "v23.0")
        if not self.token or self.token == "bu_yerga_token":
            raise IGError("IG_ACCESS_TOKEN topilmadi. .env faylni to'ldiring (README ga qarang).")
        # "EAA..." = Facebook/yagona kirish (Unified login) tokeni -> graph.facebook.com
        self.fb = self.token.startswith("EAA")
        host = "graph.facebook.com" if self.fb else "graph.instagram.com"
        self.base = f"https://{host}/{self.version}"
        if self.fb and self.user_id in ("", "me"):
            self.user_id = self._discover_ig_id()
            save_env_value("IG_USER_ID", self.user_id)

    def _discover_ig_id(self):
        """Yagona kirish tokeni uchun Instagram Business akkaunt ID sini topadi."""
        tries = [("me/accounts", {"fields": "instagram_business_account{id,username}"})]
        biz = os.environ.get("IG_BUSINESS_ID", "")
        if biz:
            tries += [(f"{biz}/owned_instagram_accounts", {"fields": "id,username"}),
                      (f"{biz}/instagram_accounts", {"fields": "id,username"})]
        tries += [("me", {"fields": "instagram_business_account{id,username}"})]
        for path, params in tries:
            try:
                d = self._req("GET", path, params=params)
            except IGError:
                continue
            items = d.get("data", [d]) if isinstance(d, dict) else []
            for it in items:
                acc = it.get("instagram_business_account") or (it if it.get("username") else None)
                if acc and acc.get("id"):
                    return acc["id"]
        raise IGError("Instagram akkaunt ID topilmadi. .env ga IG_USER_ID=... ni qo'lda yozing.")

    # --- past darajadagi so'rov ---
    def _req(self, method, path, params=None, json_body=None, base=None):
        url = f"{base or self.base}/{path.lstrip('/')}"
        params = dict(params or {})
        params["access_token"] = self.token
        for attempt in range(3):
            try:
                r = requests.request(method, url, params=params, json=json_body, timeout=60)
            except requests.RequestException as e:
                if attempt == 2:
                    raise IGError(f"Tarmoq xatosi: {e}")
                time.sleep(3 * (attempt + 1))
                continue
            try:
                data = r.json()
            except ValueError:
                data = {"raw": r.text}
            if r.status_code >= 500 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            if r.status_code >= 400 or (isinstance(data, dict) and "error" in data):
                err = data.get("error", data) if isinstance(data, dict) else data
                raise IGError(f"{method} {path} -> {r.status_code}: {json.dumps(err, ensure_ascii=False)}")
            return data
        raise IGError("So'rov bajarilmadi")

    def get(self, path, **params):
        return self._req("GET", path, params=params)

    def post(self, path, params=None, json_body=None):
        return self._req("POST", path, params=params, json_body=json_body)

    # --- akkaunt ---
    def me(self):
        if self.fb:
            d = self.get(self.user_id, fields="id,username,followers_count,media_count")
            d.setdefault("user_id", d.get("id")); d.setdefault("account_type", "BUSINESS")
            return d
        return self.get(self.user_id, fields="user_id,username,account_type,followers_count,media_count")

    def refresh_token(self):
        """Uzoq muddatli tokenni yana 60 kunga uzaytiradi."""
        if self.fb:
            return {"info": "Yagona kirish tokeni muddatsiz, yangilash shart emas"}
        data = self._req("GET", "refresh_access_token",
                         params={"grant_type": "ig_refresh_token"},
                         base="https://graph.instagram.com")
        new = data.get("access_token")
        if new:
            self.token = new
            save_env_value("IG_ACCESS_TOKEN", new)
        return data

    # --- joylash ---
    def _wait_container(self, container_id, timeout=600):
        start = time.time()
        while time.time() - start < timeout:
            st = self.get(container_id, fields="status_code,status")
            code = st.get("status_code")
            if code == "FINISHED":
                return
            if code in ("ERROR", "EXPIRED"):
                raise IGError(f"Media konteyner xatosi: {st}")
            time.sleep(10)
        raise IGError("Video ishlov berish vaqti tugadi (10 daqiqa)")

    def publish(self, kind, urls, caption="", share_to_feed=True):
        """kind: IMAGE | REELS | STORY | CAROUSEL. urls: ochiq (public) URL lar ro'yxati."""
        kind = kind.upper().strip()
        uid = self.user_id
        if kind == "CAROUSEL":
            if not 2 <= len(urls) <= 10:
                raise IGError("Karusel uchun 2-10 ta media kerak")
            children = []
            for u in urls:
                is_video = u.lower().split("?")[0].endswith((".mp4", ".mov"))
                p = {"is_carousel_item": "true"}
                if is_video:
                    p.update(media_type="VIDEO", video_url=u)
                else:
                    p["image_url"] = u
                c = self.post(f"{uid}/media", params=p)["id"]
                if is_video:
                    self._wait_container(c)
                children.append(c)
            cid = self.post(f"{uid}/media", params={
                "media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})["id"]
            self._wait_container(cid)
        elif kind == "REELS":
            cid = self.post(f"{uid}/media", params={
                "media_type": "REELS", "video_url": urls[0], "caption": caption,
                "share_to_feed": "true" if share_to_feed else "false"})["id"]
            self._wait_container(cid)
        elif kind == "STORY":
            u = urls[0]
            p = {"media_type": "STORIES"}
            if u.lower().split("?")[0].endswith((".mp4", ".mov")):
                p["video_url"] = u
            else:
                p["image_url"] = u
            cid = self.post(f"{uid}/media", params=p)["id"]
            self._wait_container(cid)
        else:  # IMAGE
            cid = self.post(f"{uid}/media", params={"image_url": urls[0], "caption": caption})["id"]
            self._wait_container(cid)
        return self.post(f"{uid}/media_publish", params={"creation_id": cid})["id"]

    def publish_reel_file(self, path, caption="", share_to_feed=True, publish=True):
        """Kompyuter/serverdagi MP4 faylni to'g'ridan-to'g'ri yuklaydi (ochiq URL shart emas).
        Faqat yagona kirish (EAA) tokeni bilan ishlaydi."""
        if not self.fb:
            raise IGError("Fayldan yuklash faqat yagona kirish (EAA...) tokeni bilan ishlaydi")
        size = os.path.getsize(path)
        c = self.post(f"{self.user_id}/media", params={
            "media_type": "REELS", "upload_type": "resumable", "caption": caption,
            "share_to_feed": "true" if share_to_feed else "false"})
        cid, uri = c["id"], c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{self.version}/{c['id']}"
        with open(path, "rb") as f:
            data = f.read()
        r = requests.post(uri, data=data, timeout=600, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(size)})
        if r.status_code >= 400:
            raise IGError(f"Video yuklashda xato {r.status_code}: {r.text[:300]}")
        self._wait_container(cid)
        if not publish:
            return cid
        return self.post(f"{self.user_id}/media_publish", params={"creation_id": cid})["id"]

    # --- media va kommentlar ---
    def recent_media(self, limit=10):
        fields = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count"
        return self.get(f"{self.user_id}/media", fields=fields, limit=limit).get("data", [])

    def comments(self, media_id, limit=50):
        return self.get(f"{media_id}/comments", fields="id,text,username,timestamp,from",
                        limit=limit).get("data", [])

    def reply_comment(self, comment_id, message):
        return self.post(f"{comment_id}/replies", params={"message": message})

    def private_reply(self, comment_id, text):
        """Komment yozgan odamga Direct orqali bitta xabar (7 kun ichida)."""
        return self.post(f"{self.user_id}/messages", json_body={
            "recipient": {"comment_id": comment_id},
            "message": {"text": text}})

    # --- statistika ---
    def media_insights(self, media_id, metrics):
        """Har bir metrikani alohida so'raydi: biri ishlamasa ham qolganlari keladi."""
        out = {}
        for m in metrics:
            try:
                d = self.get(f"{media_id}/insights", metric=m).get("data", [])
                if d:
                    vals = d[0].get("values") or [{}]
                    out[m] = vals[0].get("value", d[0].get("total_value", {}).get("value"))
            except IGError:
                out[m] = None
        return out
