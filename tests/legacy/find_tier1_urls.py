import xml.etree.ElementTree as ET
import urllib.request
import re
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

# Target names:
tier1_targets = {
    "中華民國憲法": "constitution",
    "民法": "civil_code",
    "中華民國刑法": "criminal_code",
    "民事訴訟法": "civil_procedure_code",
    "刑事訴訟法": "criminal_procedure_code",
    "行政程序法": "admin_procedure_act",
    "行政訴訟法": "admin_litigation_act",
    "公司法": "company_act",
    "勞動基準法": "labor_standards_act",
    "著作權法": "copyright_act",
    "個人資料保護法": "personal_data_protection_act",
    "道路交通管理處罰條例": "traffic_act"
}

# Also aliases
aliases = {
    "刑法": "中華民國刑法",
    "個資法": "個人資料保護法",
    "道路交通管理處罰條例": "道路交通管理處罰條例"
}

tree = ET.parse("data/raw/lawplayer/act-1-sitemap.xml")
root = tree.getroot()
urls = []
for child in root:
    loc = child.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
    if loc is not None and loc.text:
        urls.append(loc.text)

print(f"Total act URLs: {len(urls)}")
# Notice in sample output, URLs follow sequential hex:
# 6437d027e800e5f0b9300e5d -> 憲法
# 6437d054e800e5f0b930159a -> 民法
# 6437d054e800e5f0b93015aa -> 民事訴訟法
# 6437d05ae800e5f0b9301656 -> 刑法
# 6437d05ae800e5f0b9301666 -> 刑事訴訟法?
# Let's inspect url list

