"""media/ papkadagi rasm va videolarni GitHub'dagi PUBLIC repoga yuklaydi.

Instagram faylni internetdagi ochiq manzildan oladi, shuning uchun media shu yerda turadi.
Ishlatish: media/ ga fayl tashlang -> media_yukla.bat ni bosing -> schedule.csv da faqat fayl nomini yozing.
DIQQAT: bu repo hammaga ochiq. U yerga faqat joylamoqchi bo'lgan kontentni qo'ying.
"""
import subprocess
import sys

from ig_client import BASE_DIR, save_env_value

MEDIA = BASE_DIR / "media"
REPO = "insta-media"


def sh(*args, check=True):
    r = subprocess.run(args, cwd=MEDIA, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(r.stdout, r.stderr)
        sys.exit(f"Buyruq bajarilmadi: {' '.join(args)}")
    return r.stdout.strip()


def main():
    MEDIA.mkdir(exist_ok=True)
    user = sh("gh", "api", "user", "--jq", ".login")
    if not (MEDIA / ".git").exists():
        sh("git", "init", "-b", "main")
        (MEDIA / "README.md").write_text("Instagram postlar uchun media.\n", encoding="utf-8")
    exists = subprocess.run(["gh", "repo", "view", f"{user}/{REPO}"], capture_output=True).returncode == 0
    if not exists:
        sh("gh", "repo", "create", REPO, "--public", "--description", "Instagram media (avto-joylash uchun)")
    if not sh("git", "remote", check=False):
        sh("git", "remote", "add", "origin", f"https://github.com/{user}/{REPO}.git")
    sh("git", "add", "-A")
    if sh("git", "status", "--porcelain"):
        sh("git", "commit", "-m", "media yangilandi")
    sh("git", "push", "-u", "origin", "main")
    base = f"https://raw.githubusercontent.com/{user}/{REPO}/main"
    save_env_value("MEDIA_BASE_URL", base)
    files = [p.name for p in MEDIA.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".mp4", ".mov")]
    print(f"Yuklandi. Manzil: {base}")
    print("Fayllar:", ", ".join(files) or "(hali yo'q)")


if __name__ == "__main__":
    main()
