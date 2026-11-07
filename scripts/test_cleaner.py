import re

def clean_extracted_cell(raw_text: str) -> str:
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', raw_text)
    # Remove leading class=tdc... or similar artifacts
    text = re.sub(r'^(?:class|align|style|valign|width|height)=[^\s>]+[\s>]*', '', text, flags=re.I)
    # Remove &nbsp;
    text = text.replace('&nbsp;', ' ').strip()
    return text

print(repr(clean_extracted_cell("class=tdc2>\n集團公司內關係人交易之研析――以董事與公司交易為核心，兼論審計委員會之角色")))
print(repr(clean_extracted_cell("class=tdc4>\n曾宛如")))
print(repr(clean_extracted_cell("class=tdc5>\n202611")))
print(repr(clean_extracted_cell("class=tdc3>\n月旦法學雜誌")))

