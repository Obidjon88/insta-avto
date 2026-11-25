"""Asosiy boshqaruv.

  python main.py tekshir     - token va akkauntni tekshiradi
  python main.py joyla       - vaqti kelgan postlarni bir marta joylaydi
  python main.py javob       - kommentlarga bir marta javob beradi
  python main.py hisobot     - statistika hisobotini yaratadi
  python main.py token       - tokenni 60 kunga uzaytiradi
  python main.py ishla       - hammasini doimiy ishlatadi (kompyuter yoniq tursa)
  python main.py bir_marta   - bir marta tekshiradi (GitHub Actions shu bilan ishlaydi)
"""
import os
import sys
import time
from datetime import datetime

import autoreply
import publisher
import report
from ig_client import IGClient, IGError, BASE_DIR, load_env

LOG = BASE_DIR / "log.txt"


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def connect(every):
    """Token qo'yilmaguncha yoki internet yo'q bo'lsa kutib, qayta urinadi."""
    while True:
        try:
            load_env(override=True)
            client = IGClient()
            log(f"Ishga tushdi: @{client.me().get('username')}")
            return client
        except IGError as e:
            log(f"Ulanib bo'lmadi, {every // 60} daqiqadan keyin qayta urinadi: {e}")
        except Exception as e:
            log(f"Ulanishda kutilmagan xato: {e!r}")
        time.sleep(every)


def single_instance():
    """Faqat bitta nusxa ishlashi uchun (aks holda kommentlarga ikki marta javob ketadi)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        s.bind(("127.0.0.1", 47613))
        s.listen(1)
    except OSError:
        log("Avtomatika allaqachon fonda ishlayapti, bu nusxa yopiladi.")
        sys.exit(0)
    return s


def loop():
    _lock = single_instance()  # noqa: F841
    every = 5 * 60  # har 5 daqiqada
    client = connect(every)
    last_report = last_refresh = None
    while True:
        try:
            load_env(override=True)
            if os.environ.get("IG_ACCESS_TOKEN") and os.environ["IG_ACCESS_TOKEN"] != client.token:
                client = IGClient(token=os.environ["IG_ACCESS_TOKEN"])  # .env da token almashtirilgan
            publisher.run(client, log=log)
            autoreply.run(client, log=log)
            today = datetime.now().date()
            if datetime.now().weekday() == 0 and last_report != today:  # har dushanba
                report.run(client, log=log)
                last_report = today
            if last_refresh is None or (datetime.now() - last_refresh).days >= 7:
                client.refresh_token()
                last_refresh = datetime.now()
                log("Token yangilandi")
        except IGError as e:
            log(f"XATO: {e}")
        except Exception as e:  # skript to'xtab qolmasin
            log(f"Kutilmagan xato: {e!r}")
        time.sleep(every)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ishla"
    try:
        if cmd == "tekshir":
            me = IGClient().me()
            print(f"Ulandi: @{me.get('username')} | turi: {me.get('account_type')} | "
                  f"obunachi: {me.get('followers_count')} | ID: {me.get('user_id')}")
        elif cmd == "joyla":
            print(f"Joylandi: {publisher.run(log=log)}")
        elif cmd == "javob":
            print(f"Javob berildi: {autoreply.run(log=log)}")
        elif cmd == "hisobot":
            print(f"Hisobot: {report.run(log=log)}")
        elif cmd == "token":
            IGClient().refresh_token()
            print("Token 60 kunga uzaytirildi va .env ga yozildi")
        elif cmd == "bir_marta":  # GitHub Actions uchun: bir marta tekshirib chiqadi
            client = IGClient()
            publisher.run(client, log=log)
            autoreply.run(client, log=log)
            if datetime.now().weekday() == 0 and datetime.now().hour < 6:
                report.run(client, log=log)
        elif cmd == "ishla":
            loop()
        else:
            print(__doc__)
    except IGError as e:
        print(f"XATO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
