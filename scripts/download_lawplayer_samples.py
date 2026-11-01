import os
import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw', 'lawplayer', 'civil_procedure_code')
os.makedirs(save_dir, exist_ok=True)

targets = {
    'cpc_act.html': 'https://lawplayer.com/act/6437d054e800e5f0b93015aa',
    'cpc_art_1.html': 'https://lawplayer.com/article/6438cf48e800e5f0b932894f',
    'cpc_art_244.html': 'https://lawplayer.com/article/6438cf6fe800e5f0b9328b7a',
    'cpc_art_277.html': 'https://lawplayer.com/article/6438cf79e800e5f0b9328bfe',
    'criminal_act.html': 'https://lawplayer.com/act/6437d05ae800e5f0b9301656',
    'civil_art_2.html': 'https://lawplayer.com/article/6438cdc1e800e5f0b9327944'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

for filename, url in targets.items():
    print(f"Fetching {filename} from {url} ...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            resp_headers = resp.headers.as_string()
            body_bytes = resp.read()
            
            # Save raw file with headers prepended as curl -i does
            out_path = os.path.join(save_dir, filename)
            header_str = f"HTTP/1.1 {status} OK\r\n{resp_headers}\r\n"
            with open(out_path, 'wb') as out_f:
                out_f.write(header_str.encode('utf-8'))
                out_f.write(body_bytes)
            
            # Also save separate headers.txt and body.html for easy testing
            base_name = filename.rsplit('.', 1)[0]
            with open(os.path.join(save_dir, f"{base_name}.headers.txt"), 'w', encoding='utf-8') as hf:
                hf.write(f"URL: {url}\nHTTP/1.1 {status} OK\n{resp_headers}")
            with open(os.path.join(save_dir, f"{base_name}.body.html"), 'wb') as bf:
                bf.write(body_bytes)
                
            print(f"  -> Saved {out_path} ({len(body_bytes)} bytes)")
    except Exception as e:
        print(f"  -> Error fetching {url}: {e}")

