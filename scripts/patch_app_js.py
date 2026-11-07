import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS_PATH = os.path.join(BASE_DIR, "static", "js", "app.js")

with open(APP_JS_PATH, "r", encoding="utf-8") as f:
    text = f.read()

old_block = """      // 2. Recent Changes List (Separated into 新增法規 & 條文修正)
      if (changesList) {
        const newActs = data.new_acts || [];
        const modArts = data.modified_articles || [];
        const changes = data.recent_changes || [];
        if (changes.length === 0) {
          changesList.innerHTML = `<div style="color:#71717a; font-size:0.85rem; padding:0.5rem 0;">近 30 天內無條文修正或變更紀錄</div>`;
        } else {
          changesList.innerHTML = changes.map((c) => {
            const dateStr = c.created_at ? c.created_at.substring(0, 10) : "";
            const actLabel = c.act_name ? `${c.act_name} (${c.act_id})` : c.act_id;
            const artLabel = c.article_no ? `第 ${c.article_no} 條` : "全法規";
            
            let diffHtml = "";
            const detail = c.detail || {};
            if (detail.old_content || detail.new_content) {
              diffHtml = `
                <div class="diff-block" style="margin-top:0.4rem; font-size:0.8rem;">
                  ${detail.old_content ? `<div class="diff-row del" style="padding:4px 8px;"><span class="diff-tag">修正前</span>${esc(detail.old_content)}</div>` : ""}
                  ${detail.new_content ? `<div class="diff-row add" style="padding:4px 8px;"><span class="diff-tag">修正後</span>${esc(detail.new_content)}</div>` : ""}
                </div>`;
            }

            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.65rem 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">
                  <div>
                    <span style="font-weight:600; color:#60a5fa;">${esc(actLabel)}</span>
                    <span style="color:#f4f4f5; margin-left:0.4rem;">${esc(artLabel)}</span>
                    <span style="color:#a1a1aa; font-size:0.75rem; margin-left:0.5rem;">[${esc(c.change_type)}]</span>
                  </div>
                  <span style="color:#71717a; font-size:0.75rem;">${esc(dateStr)}</span>
                </div>
                ${diffHtml}
              </div>`;
          }).join("");
        }
      }"""

new_block = """      // 2. Recent Changes List (Separated into 新增法規 & 條文修正 per Prompt 4C)
      if (changesList) {
        const newActs = data.new_acts || [];
        const modArts = data.modified_articles || [];
        let html = "";

        // Section 2A: 新增法規
        html += `<div style="margin-bottom:1rem;">
          <div style="font-size:0.88rem; font-weight:700; color:#22c55e; margin-bottom:0.5rem; display:flex; align-items:center; gap:6px;">
            <span>✨ 新增法規</span>
            <span style="font-size:0.75rem; background:#14532d; color:#86efac; padding:1px 6px; border-radius:10px;">${newActs.length}</span>
          </div>`;
        if (newActs.length === 0) {
          html += `<div style="color:#71717a; font-size:0.8rem; padding:0.3rem 0.5rem;">近期無新增法規</div>`;
        } else {
          html += `<div style="display:flex; flex-direction:column; gap:0.5rem;">` + newActs.map((na) => {
            const detail = na.detail || {};
            const pubDate = na.act_date_raw || detail.source_modified_date || detail.date_raw || "";
            const effNote = na.effective_note || detail.effective_note_raw || "";
            return `
              <div class="new-act-change-card" style="background:#18181b; border:1px solid #166534; border-radius:6px; padding:0.65rem 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span class="badge-new-act" style="background:#15803d; color:#ffffff; font-size:0.72rem; font-weight:700; padding:2px 6px; border-radius:4px;">新增</span>
                    <strong style="color:#f4f4f5; font-size:0.92rem;">${esc(na.act_name || na.act_id)}</strong>
                  </div>
                  <span class="source-date-raw" style="color:#86efac; font-family:monospace; font-size:0.8rem;">${esc(pubDate)}</span>
                </div>
                ${effNote ? `<div class="effective-note-raw" style="margin-top:0.35rem; font-size:0.78rem; color:#f59e0b; background:#291e0a; padding:3px 8px; border-radius:4px;">⏳ 未生效備註：${esc(effNote)}</div>` : ""}
              </div>`;
          }).join("") + `</div>`;
        }
        html += `</div>`;

        // Section 2B: 條文修正
        html += `<div>
          <div style="font-size:0.88rem; font-weight:700; color:#60a5fa; margin-bottom:0.5rem; display:flex; align-items:center; gap:6px;">
            <span>📝 條文修正</span>
            <span style="font-size:0.75rem; background:#1e3a8a; color:#93c5fd; padding:1px 6px; border-radius:10px;">${modArts.length}</span>
          </div>`;
        if (modArts.length === 0) {
          html += `<div style="color:#71717a; font-size:0.8rem; padding:0.3rem 0.5rem;">近 30 天內無條文修正紀錄</div>`;
        } else {
          html += `<div style="display:flex; flex-direction:column; gap:0.5rem;">` + modArts.map((c) => {
            const dateStr = c.created_at ? c.created_at.substring(0, 10) : "";
            const actLabel = c.act_name ? `${c.act_name} (${c.act_id})` : c.act_id;
            const artLabel = c.article_no ? `第 ${c.article_no} 條` : "全法規";
            let diffHtml = "";
            const detail = c.detail || {};
            if (detail.old_content || detail.new_content) {
              diffHtml = `
                <div class="diff-block" style="margin-top:0.4rem; font-size:0.8rem;">
                  ${detail.old_content ? `<div class="diff-row del" style="padding:4px 8px;"><span class="diff-tag">修正前</span>${esc(detail.old_content)}</div>` : ""}
                  ${detail.new_content ? `<div class="diff-row add" style="padding:4px 8px;"><span class="diff-tag">修正後</span>${esc(detail.new_content)}</div>` : ""}
                </div>`;
            }
            return `
              <div style="background:#18181b; border:1px solid #27272a; border-radius:6px; padding:0.65rem 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:0.85rem;">
                  <div>
                    <span style="font-weight:600; color:#60a5fa;">${esc(actLabel)}</span>
                    <span style="color:#f4f4f5; margin-left:0.4rem;">${esc(artLabel)}</span>
                    <span style="color:#a1a1aa; font-size:0.75rem; margin-left:0.5rem;">[${esc(c.change_type)}]</span>
                  </div>
                  <span style="color:#71717a; font-size:0.75rem;">${esc(dateStr)}</span>
                </div>
                ${diffHtml}
              </div>`;
          }).join("") + `</div>`;
        }
        html += `</div>`;

        changesList.innerHTML = html;
      }"""

assert old_block in text, "old_block not found in app.js"
with open(APP_JS_PATH, "w", encoding="utf-8") as f:
    f.write(text.replace(old_block, new_block))
print("Patched app.js successfully")

