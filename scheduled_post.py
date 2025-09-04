# file: scheduled_post.py
import os, base64, pathlib, requests, textwrap, argparse, datetime, sys, json, traceback
from dotenv import load_dotenv

load_dotenv()

# ---- Secrets / Env
XAI_API_KEY    = os.environ["XAI_API_KEY"]
X_MODEL        = os.environ.get("X_MODEL", "grok-code-fast-1")
CLIENT_ID      = os.environ["X_CLIENT_ID"]
CLIENT_SECRET  = os.environ["X_CLIENT_SECRET"]

TOKEN_URL      = "https://api.x.com/2/oauth2/token"
TWEET_URL      = "https://api.x.com/2/tweets"
REFRESH_PATH   = pathlib.Path(".x_refresh_token")

# Secrets'tan gelen refresh token'ı dosyaya yazarak dayanıklılık
if not REFRESH_PATH.exists():
    rt = os.environ.get("X_REFRESH_TOKEN")
    if rt:
        REFRESH_PATH.write_text(rt.strip(), encoding="utf-8")

def refresh_access_token():
    refresh_token = REFRESH_PATH.read_text().strip()
    auth_basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Content-Type":"application/x-www-form-urlencoded",
               "Authorization": f"Basic {auth_basic}"}
    data = {"grant_type":"refresh_token", "refresh_token":refresh_token, "client_id":CLIENT_ID}
    r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    print("X_TOKEN_HTTP:", r.status_code)
    print("X_TOKEN_RAW:", r.text[:400])
    r.raise_for_status()
    tok = r.json()
    if tok.get("refresh_token"):
        REFRESH_PATH.write_text(tok["refresh_token"], encoding="utf-8")
    return tok["access_token"]

def generate_tweet_text(topic: str, max_len: int = 280) -> str:
    """
    Grok'tan tek cümlelik, duygu yüklü Türkçe bir söz üretir.
    Boş dönerse güvenli fallback kullanır ve 280 karakter sınırına uyar.
    """
    # {TARIH}/{SAAT} yer tutucularını doldur (TRT = UTC+3)
    now_tr = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    topic = (
        topic.replace("{TARIH}", now_tr.strftime("%d.%m.%Y"))
             .replace("{SAAT}",  now_tr.strftime("%H:%M"))
    )

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": X_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Deneyimli bir sosyal medya editörüsün. Türkçe ve yalın yazıyorsun. "
                    "TEK CÜMLELİK, duygu yüklü ve vurucu bir söz üret. "
                    "280 karakteri geçme. Emoji ve hashtag KULLANMA. "
                    "Alıntı tırnakları ekleme; doğrudan cümleyi ver."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Tarih: {now_tr.strftime('%d.%m.%Y')}, Saat: {now_tr.strftime('%H:%M')}. "
                    f"Konu/ipucu: {topic}. "
                    "Tek cümlelik, özgün bir söz ver."
                ),
            },
        ],
        "temperature": 0.8,
        "max_tokens": 200,
    }

    text = ""
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print("GROK_HTTP:", r.status_code)
        print("GROK_RAW:", r.text[:400])
        r.raise_for_status()
        data = r.json()
        text = (data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "") or "").strip()
        print("GROK_OK:", text, f"(len={len(text)})")
    except Exception as e:
        print("GROK_EXCEPTION:", repr(e))
        traceback.print_exc()

    # Fallback: boş veya çok kısa ise güvenli bir cümle
    if not text or len(text) < 5:
        text = "Kalbin usulca fısıldar: Bugün, kendine iyi davran."
        print("FALLBACK_USED:", text)

    # 280 karakter sınırı
    if len(text) > max_len:
        text = textwrap.shorten(text, width=max_len - 1, placeholder="…")

    return text

def post_tweet(text: str):
    access_token = refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/json"}
    r = requests.post(TWEET_URL, headers=headers, json={"text": text}, timeout=30)
    print("X_POST_HTTP:", r.status_code)
    print("X_POST_RAW:", r.text[:400])
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default=None)
    parser.add_argument("--topic-file", default=None)
    args = parser.parse_args()

    if not args.topic and not args.topic_file:
        print("Konu gerekli: --topic veya --topic-file", file=sys.stderr); sys.exit(1)

    topic = args.topic if args.topic else pathlib.Path(args.topic_file).read_text(encoding="utf-8").strip()
    tweet = generate_tweet_text(topic)
    print("Üretilen:", tweet)
    resp = post_tweet(tweet)
    print("Tweet paylaşıldı:", resp)
