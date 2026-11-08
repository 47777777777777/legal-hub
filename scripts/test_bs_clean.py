from bs4 import BeautifulSoup
import re
import html as html_lib

raw_snippet = '<td class=artiupd_RS_2>　　一、本條新增。<br>\n　　二、參酌<漁業法第四十一條第二項>，增訂本條第一項。<br></td>'

# Old naive regex
old_clean = re.sub(r'\s+', '', re.sub(r'<[^>]+>', '', raw_snippet))
print("Old clean:", old_clean)

# BeautifulSoup get_text
bs_clean = re.sub(r'\s+', '', BeautifulSoup(raw_snippet, 'html.parser').get_text())
print("BS clean: ", bs_clean)

stored_reason = "一、本條新增。\n二、參酌<漁業法第四十一條第二項>，增訂本條第一項。"
clean_reason = re.sub(r'\s+', '', stored_reason)
print("Reason in BS clean:", clean_reason in bs_clean)

