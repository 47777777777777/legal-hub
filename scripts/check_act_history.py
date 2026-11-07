import sqlite3

conn = sqlite3.connect('data/legal_hub.db')
c = conn.cursor()
c.execute("SELECT id, name, history_json, effective_date, effective_note, abandon_note FROM acts WHERE id IN ('admin_procedure_act', 'constitution')")
for r in c.fetchall():
    print('ACT:', r[0], r[1])
    print('history_json:', repr(r[2])[:120])
conn.close()

