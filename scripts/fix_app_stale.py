with open('static/js/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'const modDate = (this.currentAct && this.currentAct.last_modified) || "最新修法";'
replacement = 'const modDate = (this.currentAct && this.currentAct.last_modified) ? `於 ${esc(this.currentAct.last_modified)} ` : "";'
assert target in c, "target not found"
c = c.replace(target, replacement)
c = c.replace('<span>本條已於 ${esc(modDate)} 修正', '<span>本條已${modDate}修正')

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(c)

print("Replaced successfully")

