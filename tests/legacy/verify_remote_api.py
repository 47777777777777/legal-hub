import urllib.request
import json

d = json.loads(urllib.request.urlopen('http://127.0.0.1:8080/api/acts/civil_code').read().decode('utf-8'))
print('Remote Act Name:', d['data']['name'])
print('First 6 articles:')
for a in d['data']['articles'][:6]:
    print(f"  Art {a['article_no']}: '{a['title']}'")

