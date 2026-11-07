import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
conn = sqlite3.connect("data/legal_hub.db")
c = conn.cursor()
c.execute("SELECT id, pcode, name FROM acts WHERE id IN ('constitution', 'civil_code', 'criminal_code', 'civil_procedure_code', 'criminal_procedure_code', 'admin_procedure_act', 'admin_litigation_act', 'company_act', 'labor_standards_act', 'copyright_act', 'personal_data_protection_act', 'traffic_act')")
for r in c.fetchall():
    print(r)
conn.close()

