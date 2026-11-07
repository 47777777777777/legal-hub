import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.storage import LegalStorage

storage = LegalStorage('data/acts')
panel = storage.get_article_panel('admin_procedure_act', '128')
print('ACT:', panel['act_name'], panel['act_id'])
for s in panel['sections']:
    print(f"SECTION: {s['section_type']:<26} | SOURCE: {s['source']:<10} | STATUS: {s['status']:<16} | ITEMS: {len(s['items'])}")

print("\n--- SAMPLE ORDER ACT PANEL ---")
order_panel = storage.get_article_panel('a0000006', '1')
if order_panel:
    print('ORDER ACT:', order_panel['act_name'], order_panel['act_id'])
    for s in order_panel['sections']:
        print(f"SECTION: {s['section_type']:<26} | SOURCE: {s['source']:<10} | STATUS: {s['status']:<16} | ITEMS: {len(s['items'])}")
