# file: dispatcher_duygu.py
import datetime, pathlib, subprocess, sys

ANCHORS_FILE = pathlib.Path("anchors_trt.txt")
TOPIC_FILE   = pathlib.Path("topic_duygu.txt")
STATE_FILE   = pathlib.Path(".last_posted_duygu")  # yinelenmeyi önlemek için günlük kayıt

def now_trt():
    # Türkiye saati ~ UTC+3
    return datetime.datetime.utcnow() + datetime.timedelta(hours=3)

def load_anchors():
    """anchors_trt.txt içindeki HH:MM satırlarını oku."""
    if not ANCHORS_FILE.exists():
        return []
    anchors = []
    for line in ANCHORS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            hh, mm = map(int, line.split(":"))
            anchors.append((hh, mm))
        except Exception:
            continue
    return anchors

def todays_targets(now):
    """Bugün için: her anchor'dan başlayarak 2'şer saat aralıklarla gece 24:00'e kadar hedefler üret."""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = start + datetime.timedelta(days=1)
    targets = []
    for hh, mm in load_anchors():
        t = start.replace(hour=hh, minute=mm)
        # Eğer anchor geçmişse yine de bugünkü akış için 2'şer saat devam etsin
        while t < end:
            targets.append(t)
            t += datetime.timedelta(hours=2)
    return sorted(targets)

def already_posted(key):
    if not STATE_FILE.exists():
        return False
    lines = [l.strip() for l in STATE_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return key in lines

def mark_posted(key):
    prev = []
    if STATE_FILE.exists():
        prev = [l.strip() for l in STATE_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
        # eski günlerin kayıtlarını temizle (yalın tut)
        today = key.split(" ")[0]
        prev = [x for x in prev if x.startswith(today)]
    prev.append(key)
    STATE_FILE.write_text("\n".join(prev), encoding="utf-8")

if __name__ == "__main__":
    now = now_trt()
    targets = todays_targets(now)

    if not TOPIC_FILE.exists():
        print("[dispatcher] topic_duygu.txt bulunamadı.", file=sys.stderr)
        sys.exit(1)

    # 5 dakikalık çalışma aralığını yakalamak için: hedeften itibaren 0–5 dk penceresi
    window_sec = 5 * 60
    ran_any = False

    for t in targets:
        delta = (now - t).total_seconds()
        key = f"{t.strftime('%Y-%m-%d %H:%M')}"
        if 0 <= delta < window_sec and not already_posted(key):
            print(f"[dispatcher] Eşleşme: {key} → topic_duygu.txt")
            # scheduled_post.py'yi çağır
            res = subprocess.run(
                [sys.executable, "scheduled_post.py", "--topic-file", str(TOPIC_FILE)],
                capture_output=True, text=True
            )
            print(res.stdout)
            if res.stderr:
                print(res.stderr, file=sys.stderr)
            mark_posted(key)
            ran_any = True

    if not ran_any:
        print(f"[dispatcher] Bu dakikada gönderi yok. Şimdi (TRT): {now.strftime('%Y-%m-%d %H:%M')}")
