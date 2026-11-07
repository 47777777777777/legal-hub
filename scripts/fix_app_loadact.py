with open('static/js/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update sectionHeading to accept sourceInfo
old_sec = '''function sectionHeading(iconName, title, note) {
  return `<h3 class="sub-heading">${icon(iconName, 16)}<span>${title}</span>${note ? `<span class="sub-note">${note}</span>` : ""}</h3>`;
}'''

new_sec = '''function sectionHeading(iconName, title, note, sourceInfo) {
  return `<h3 class="sub-heading" style="display:flex; justify-content:space-between; align-items:center;">
    <span style="display:flex; align-items:center; gap:6px;">${icon(iconName, 16)}<span>${title}</span>${note ? `<span class="sub-note">${note}</span>` : ""}</span>
    ${sourceInfo ? `<span style="font-size:0.75rem; color:#a1a1aa; font-weight:normal;">來源：${esc(sourceInfo)}</span>` : ""}
  </h3>`;
}'''

text = text.replace(old_sec, new_sec)

# 2. Update loadAct to set this.currentActId = actId
old_load = '''  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (!json.success) return;
      this.currentAct = json.data;'''

new_load = '''  async loadAct(actId) {
    try {
      const resp = await fetch(`/api/acts/${actId}`);
      const json = await resp.json();
      if (!json.success) return;
      this.currentActId = actId;
      this.currentAct = json.data;'''

text = text.replace(old_load, new_load)

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated sectionHeading and loadAct in static/js/app.js')

