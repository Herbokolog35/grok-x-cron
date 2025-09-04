# file: scheduled_post.py
import os, base64, pathlib, requests, textwrap, argparse, datetime, json
from dotenv import load_dotenv

load_dotenv()

# ---- Config / Secrets
XAI_API_KEY    = os.environ["XAI_API_KEY"]
X_MODEL        = os.environ.get("X_MODEL", "grok-code-fast-1")
CLIENT_ID      = os.environ["X_CLIENT_ID"]
CLIENT_SECRET  = os.environ["X_CLIENT_SECRET"]

TOKEN_URL      = "https://api.x.com/2/oauth2/token"
TWEET_URL      = "https://api.x.com/2/tweets"
REFRESH_PATH   = pathlib.Path(".x_refresh_token")

def refresh_access_token():
    refresh_token = REFRESH_PATH.read_text().strip()
    auth_basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Content-Type":"application/x-www-form-urlencoded","Authorization":f"Basic {auth_basic}"}
    data = {"grant_type":"refresh_token","refresh_token":refresh_token,"client_id":CLIENT_ID}
    r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    r.raise_for_status()
    tok = r.json()
    if "refresh_token" in tok:
        REFRESH_PATH.write_text(tok["refresh_token"], encoding="utf-8")
    return tok["access_token"]

def generate_tweet_text(topic: str, max_len: int = 280) -> str:
    # Dinamik tarih/saat etiketi istersek:
    today_tr = datetime.datetime.utcnow() + datetime.timedelta(hours=3)  # Europe/Istanbul ~ UTC+3
    topic = topic.replace("{TARIH}", today_tr.strftime("%d.%m.%Y")).replace("{SAAT}", today_tr.strftime("%H:%M"))

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": X_MODEL,
            "messages": [
                {"role":"system","content":
                 "Kıdemli bir sosyal medya editörüsün. Tek bir tweet üret. Türkçe yaz. "
                 "280 karakteri geçme. Gereksiz hashtag ve emoji ekleme."
                },
                {"role":"user","content": f"Konu: {topic} — tek, vurucu, özgün bir tweet yaz."}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        },
        timeout=30
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    return text if len(text) <= max_len else textwrap.shorten(text, width=max_len-1, placeholder="…")

def post_tweet(text: str):
    access_token = refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type":"application/json"}
    r = requests.post(TWEET_URL, headers=headers, json={"text": text}, timeout=30)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", help="Tek seferlik konu (örn: '08:00 sabah motivasyonu')", default=None)
    parser.add_argument("--topic-file", help="Konu metnini dosyadan oku", default=None)
    args = parser.parse_args()

    if not args.topic and not args.topic_file:
        raise SystemExit("Konu gerekli: --topic veya --topic-file kullanın.")

    topic = args.topic if args.topic else pathlib.Path(args.topic_file).read_text(encoding="utf-8").strip()
    tweet = generate_tweet_text(topic)
    print("Üretilen tweet:\n", tweet)
    resp = post_tweet(tweet)
    print("Tweet paylaşıldı:", resp)
