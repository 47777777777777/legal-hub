import requests
import re

sess = requests.Session()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
r1 = sess.get('https://lis.ly.gov.tw/lglawc/lglawkm', headers=headers)
r2 = sess.post('https://lis.ly.gov.tw/lglawc/lglawkm', data={'ACTNM': '行政程序法', 'button': '查詢'}, headers=headers)

print("r2 length:", len(r2.text))
matches = re.findall(r'/lglawc/[a-zA-Z0-9_\?=\^]+', r2.text)
print("Found links:", matches[:10])

