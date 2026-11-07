import urllib.request, re, json

req = urllib.request.Request("https://lawplayer.com/", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8")
    matches = re.findall(r'href="(/act/[0-9a-f]+)"[^>]*>([^<]+)<', html)
    print("Found acts on LawPlayer:")
    for link, title in set(matches):
        print(f"{title.strip()}: {link}")
except Exception as e:
    print("Error:", e)

