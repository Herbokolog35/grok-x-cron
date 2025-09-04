# Üste ek importlar:
import json, traceback

def refresh_access_token():
    refresh_token = REFRESH_PATH.read_text().strip()
    auth_basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Content-Type":"application/x-www-form-urlencoded","Authorization":f"Basic {auth_basic}"}
    data = {"grant_type":"refresh_token","refresh_token":refresh_token,"client_id":CLIENT_ID}
    r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=30)
    print("X_TOKEN_HTTP:", r.status_code)               # <— TEŞHİS
    print("X_TOKEN_RAW:", r.text[:400])                 # <— TEŞHİS (ilk 400 karakter)
    r.raise_for_status()
    tok = r.json()
    if "refresh_token" in tok and tok["refresh_token"]:
        REFRESH_PATH.write_text(tok["refresh_token"], encoding="utf-8")
    return tok["access_token"]

def generate_tweet_text(topic: str, max_len: int = 280) -> str:
    now_tr = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    topic = topic.replace("{TARIH}", now_tr.strftime("%d.%m.%Y")).replace("{SAAT}", now_tr.strftime("%H:%M"))

    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": X_MODEL,
        "messages": [
            {"role":"system","content":"Kıdemli bir sosyal medya editörüsün. Tek cümlelik, duygu yüklü bir söz üret. Türkçe yaz. 280 karakteri geçme. Hashtag/emoji yok."},
            {"role":"user","content": f"Konu: {topic} — tek, vurucu, özgün bir söz yaz."}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print("GROK_HTTP:", r.status_code)              # <— TEŞHİS
        print("GROK_RAW:", r.text[:400])                # <— TEŞHİS
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"].strip()
        print("GROK_OK:", text, f"(len={len(text)})")
    except Exception as e:
        print("GROK_EXCEPTION:", repr(e))
        traceback.print_exc()
        text = ""

    if not text or len(text.strip()) < 5:
        text = "Kalbin usulca fısıldar: Bugün, kendine iyi davran."
        print("FALLBACK_USED:", text)

    if len(text) > max_len:
        text = textwrap.shorten(text, width=max_len-1, placeholder="…")
    return text

def post_tweet(text: str):
    access_token = refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type":"application/json"}
    r = requests.post(TWEET_URL, headers=headers, json={"text": text}, timeout=30)
    print("X_POST_HTTP:", r.status_code)                # <— TEŞHİS
    print("X_POST_RAW:", r.text[:400])                  # <— TEŞHİS
    r.raise_for_status()
    return r.json()