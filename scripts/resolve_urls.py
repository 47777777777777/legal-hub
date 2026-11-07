import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) LegalHub/1.0'}
urls = [
    'https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQEaUBl5iCyAK0j4QRUINOI-s_ZmNlZjoj9ev3TV57Z00yYINoXzQOGwexfm-BuxejbyIEC8mpi86KQYjVu_aZfgnVKBIf2XJRWZLE18SOKYcX8BdrVTa2lP45A89oPY55t14R64jY9ur32_Q_D8VjTJ0fbI',
    'https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQHMaVnNwpvztjcXyS2_1YJ2Of9gW92Vwt95vJyA1cwiLV0z_4_1W7JIZ2Ic6dKeAME1oqaVaUbrGOy9_ScezGSe8LzBPOL7OjtLWwXFj6MOqJAzL4LJuZYXPXD13ni8jrMZD0FLLIl_'
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(u, '->', resp.geturl())
    except Exception as e:
        print(u, '-> error:', e)

