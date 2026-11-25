# Instagram avtomatika (Business akkaunt uchun)

Bu to'plam Instagram'ning **rasmiy API**si orqali ishlaydi, shuning uchun akkaunt bloklanish xavfi yo'q.
Uning vazifalari:

1. **Avto-joylash.** `schedule.csv` ga yozilgan post, reel, karusel va storylarni o'z vaqtida joylaydi.
2. **Kommentga avto-javob va Direct.** Komment kalit so'zga mos kelsa, kommentga javob yozadi va o'sha odamga Direct yuboradi.
3. **Statistika hisoboti.** Reach, ko'rishlar, like va saqlashlarni yig'adi, eng yaxshi postlar, kunlar va soatlarni ko'rsatadi.

---

## 1-qadam. Python o'rnatish (Windows)

1. https://www.python.org/downloads/ saytidan Python 3.10 yoki undan yangisini o'rnating. O'rnatishda **"Add python.exe to PATH"** belgisini qo'ying.
2. Shu papkada `cmd` oching va quyidagini yozing:
   ```
   pip install -r requirements.txt
   ```

## 2-qadam. Meta ilovasini yaratish va token olish (taxminan 10 daqiqa)

1. https://developers.facebook.com ga kiring (Facebook akkaunt bilan) → **My Apps → Create App**.
2. Use case sifatida **"Manage messaging & content on Instagram"** ni tanlang va ilovaga nom bering.
3. Ilova ichida **Instagram → API setup with Instagram login** bo'limiga o'ting.
4. **"Generate access tokens"** qismida **Add account** tugmasini bosing va Instagram Business akkauntingiz bilan kiring.
   - Agar "tester" talab qilinsa: **App roles → Roles → Instagram Testers** bo'limiga akkauntingizni qo'shing.
     Keyin Instagram'da **Sozlamalar → Ilovalar va veb-saytlar → Tester takliflari** orqali taklifni qabul qiling.
5. Ruxsatlarni yoqing: `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_comments`, `instagram_business_manage_messages`.
6. **Generate token** tugmasini bosing va tokenni nusxalang.
7. `.env.example` faylidan nusxa olib, uni `.env` deb nomlang. `IG_ACCESS_TOKEN=` dan keyin tokenni qo'ying.

> ⚠️ Tokenni hech kimga bermang, GitHub'ga ham yuklamang (`.gitignore` buni allaqachon to'sib turadi).
> Token 60 kun amal qiladi. `main.py ishla` rejimi uni har hafta o'zi yangilab turadi.
> Qo'lda yangilash uchun: `python main.py token`.

Ulanishni tekshirish:
```
python main.py tekshir
```
Natijada `Ulandi: @akkauntingiz | turi: BUSINESS ...` chiqishi kerak.

## 3-qadam. Postlarni jadvalga qo'yish (`schedule.csv`)

Faylni Excel yoki Bloknot bilan oching:

| vaqt | tur | media | matn | holat |
|---|---|---|---|---|
| 2026-11-26 19:00 | IMAGE | https://.../rasm.jpg | Caption #heshteg | *(bo'sh qoldiring)* |
| 2026-11-27 20:00 | REELS | reel1.mp4 | ... | |
| 2026-11-28 19:00 | CAROUSEL | 1.jpg\|2.jpg\|3.jpg | ... | |

- **tur:** `IMAGE`, `REELS`, `CAROUSEL` (2–10 ta media, `|` bilan ajratiladi) yoki `STORY`.
- **vaqt:** O'zbekiston vaqti bilan, `YYYY-MM-DD HH:MM` formatida.
- **holat:** skript buni o'zi to'ldiradi (`joylandi: ...` yoki `xato: ...`). Qayta joylash kerak bo'lsa, katakni tozalang.

**Muhim: media internetda ochiq (public) URL bo'lishi kerak.** Instagram faylni o'sha manzildan o'zi yuklab oladi.
Kompyuterdagi faylni to'g'ridan-to'g'ri yuborib bo'lmaydi. Eng oson yo'l:

1. GitHub'da **public** repo oching (masalan `insta-media`) va rasm hamda videolarni o'sha yerga yuklang.
2. `.env` ga `MEDIA_BASE_URL=https://raw.githubusercontent.com/LOGIN/insta-media/main` deb yozing.
3. Endi `schedule.csv` da faqat fayl nomini yozish kifoya: `reel1.mp4`.

Talablar: rasmlar **JPEG**, reels **MP4** (H.264) bo'lishi kerak, vertikal 9:16 format tavsiya etiladi.

## 4-qadam. Avto-javob qoidalari (`rules.json`)

```json
{
  "kalit_sozlar": ["qo'llanma", "pdf"],
  "javob": "@{username} Direct'ingizga yubordim 📩",
  "direct": "Salom! Mana qo'llanma: https://..."
}
```
- Kommentda kalit so'z bo'lsa, skript **kommentga javob** yozadi va **Direct** yuboradi.
  Reeldagi "izohga Claude deb yozing" usuli aynan shunday ishlaydi.
- `{username}` o'rniga komment yozgan odamning nomi qo'yiladi.
- Direct yubormaslik uchun `"direct": ""` deb qoldiring.
- Har bir kommentga faqat **bir marta** javob beriladi.
- Birinchi ishga tushirishda eski kommentlarga javob yozilmaydi (`eski_kommentlarga_javob: false`).
- Instagram qoidasiga ko'ra Direct faqat komment yozilganidan keyingi **7 kun ichida** yuborilishi mumkin.

> ℹ️ Ilova **Development** rejimida turganda Direct (private reply) faqat ilovada roli bor odamlarga ketishi mumkin.
> Hammaga yuborish uchun Meta'da `instagram_business_manage_messages` ruxsatiga **App Review** orqali Advanced Access olish kerak.
> Kommentlarga oddiy javob berish esa darhol ishlaydi.

## 5-qadam. Ishga tushirish

- **Doimiy rejim:** `ishga_tushir.bat` faylini ikki marta bosing. Skript har 5 daqiqada jadvalni va kommentlarni tekshiradi,
  har dushanba hisobot tuzadi va har hafta tokenni yangilaydi. Kompyuter yoniq va internet ulangan bo'lishi kerak.
- **Alohida buyruqlar:**
  ```
  python main.py joyla     # vaqti kelgan postlarni joylash
  python main.py javob     # kommentlarni bir marta tekshirish
  python main.py hisobot   # hisobot -> hisobotlar/hisobot_....html
  ```
- Kompyuter yoqilganda o'zi ishga tushsin desangiz: `Win+R` → `shell:startup` ni oching va
  `ishga_tushir.bat` ning yorlig'ini (shortcut) o'sha papkaga qo'ying.

Barcha harakatlar `log.txt` ga yoziladi.

## Cheklovlar

- Instagram API orqali sutkasiga taxminan 100 tagacha post joylash mumkin. Bu blog uchun yetarli.
- Avtomatik like, follow yoki unfollow qilish yo'q. Bu Instagram qoidalariga zid va akkauntni bloklatadi.
- Musiqa, stiker va hamkor (collab) teglarini API orqali qo'shishning imkoni cheklangan. Ular kerak bo'lsa, postni ilovadan joylang.
