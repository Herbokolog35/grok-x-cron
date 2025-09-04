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
                    "Sen deneyimli bir sosyal medya yazarı ve şairsin. "
                    "Türkçe yaz. Tek cümlelik, duygu yüklü, özgün bir söz yaz. "
                    "İçinde duygu, derinlik ve vuruculuk olsun. "
                    "En fazla 280 karakter kullan. "
                    "Emoji, hashtag veya alıntı işareti KULLANMA."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Tarih: {now_tr.strftime('%d.%m.%Y')}, Saat: {now_tr.strftime('%H:%M')}.\n"
                    f"Konu/ipucu: {topic}\n"
                    "Bana tek cümlelik, duygu yüklü bir söz üret."
                ),
            },
        ],
        "temperature": 0.9,
        "max_tokens": 400,  # Boş dönmesin diye artırıldı
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
