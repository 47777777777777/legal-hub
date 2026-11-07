import sys

with open("static/js/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Check lines 1739 to 1780
target_part = "".join(lines[1739:1781])

replacement_insights = """    if (insights.length) {
      const insightHeading = (art.source === "lawplayer") ? "裁判書與重要實務見解 (法律人)" : "裁判書與重要實務見解";
      html += `<section>${sectionHeading("gavel", insightHeading, `${insights.length}`, sourceInfo)}
        ${insights.filter(ins => ins.ref).map((ins) => `
          <div class="card judgment-card">
            <div class="card-title accent">${ins.court ? `${esc(ins.court)} · ` : ""}${esc(ins.ref)}</div>
            <div class="card-body" style="line-height: 1.6;">${esc(ins.summary || "")}</div>
            ${ins.url ? `<div style="margin-top:0.35rem;"><a href="${esc(ins.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看裁判原文 ↗</a></div>` : ""}
          </div>
        `).join("")}
      </section>`;
    }

    if (letters.length) {
      const letterHeading = (art.source === "lawplayer") ? "相關函釋 (法律人)" : "相關函釋";
      html += `
        <section>${sectionHeading("book", letterHeading, `${letters.length}`, sourceInfo)}
          ${letters.filter(letItem => letItem.ref || letItem.org || letItem.summary || letItem.content).map((letItem) => {
            const titleParts = [letItem.org, letItem.ref, letItem.date].filter(Boolean);
            const titleText = titleParts.map(p => esc(p)).join(" · ");
            return `
            <div class="card">
              ${titleText ? `<div class="card-title accent">${titleText}</div>` : ""}
              <div class="card-body" style="line-height: 1.6; white-space: pre-wrap;">${esc(letItem.summary || letItem.content || "")}</div>
              ${letItem.url ? `<div style="margin-top:0.35rem;"><a href="${esc(letItem.url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.8rem; color:#60a5fa; text-decoration:none;">查看函釋原文 ↗</a></div>` : ""}
            </div>`;
          }).join("")}
        </section>`;
    }

    if (!insights.length && !letters.length) {
      html += `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
        此條尚無實務見解資料
      </div>`;
    }

    const ccuAuth = window.currentCCUStatus === 'authenticated';
    html += `
      <section>${sectionHeading("search", "權威判解檢索 (含 AutoRPA 代理)")}
        <div class="link-grid">
          <a href="https://judgment.judicial.gov.tw/FJUD/default.aspx" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
            <span>🏛️ 司法院裁判書系統 (${actName} 第${esc(art.article_no)}條)</span>${icon("external", 13)}
          </a>
          ${ccuAuth ? `
            <a href="https://www-lawbank-com-tw.autorpa.lib.ccu.edu.tw:8443/" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>⚖️ 法源法律網 (中正代理，需登入)</span>${icon("external", 13)}
            </a>
            <a href="https://www-lawdata-com-tw.autorpa.lib.ccu.edu.tw:8443/anglekmc/ttswebx?@0:0:1:lawkm@@0.1702332962648232" target="_blank" rel="noopener noreferrer" class="judgment-link-btn">
              <span>📚 月旦知識庫 (中正代理，需登入)</span>${icon("external", 13)}
            </a>
          ` : ""}
        </div>
      </section>

"""

full_text = "".join(lines)
assert target_part in full_text, "target_part not found"
full_text = full_text.replace(target_part, replacement_insights)

# 2. Update renderLegislativeHtml
target_legis = """  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const history = (art.source && art.amendment_history) ? art.amendment_history : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    if (art.source && (history.length || art.legislative_reasons)) {
      if (history.length) {
        return `
          <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`, sourceInfo)}
            ${history.map((item) => `
              <div class="card">
                <div class="card-title accent">${item.date ? `${esc(item.date)} · ` : ""}${esc(item.change_type || item.type || "修正")}</div>
                <div class="card-body">${esc(item.reason || "")}</div>
                ${item.old_content ? `
                  <div class="diff-block">
                    <div class="diff-row del"><span class="diff-tag">修正前</span>${esc(item.old_content)}</div>
                    <div class="diff-row add"><span class="diff-tag">修正後</span>${esc(item.new_content || art.content)}</div>
                  </div>` : ""}
              </div>
            `).join("")}
          </section>`;
      } else {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            <div class="card">
              <div class="card-body">${esc(art.legislative_reasons)}</div>
            </div>
          </section>`;
      }
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      此條尚無外部解析資料
    </div>`;
  }"""

replacement_legis = """  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const history = (art.source && art.amendment_history) ? art.amendment_history : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");

    if (art.source && (history.length || art.legislative_reasons)) {
      if (history.length) {
        return `
          <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`, sourceInfo)}
            ${history.map((item) => `
              <div class="card">
                <div class="card-title accent">${item.date ? `${esc(item.date)} · ` : ""}${esc(item.change_type || item.type || "")}</div>
                <div class="card-body">${esc(item.reason || "")}</div>
                ${item.old_content ? `
                  <div class="diff-block">
                    <div class="diff-row del"><span class="diff-tag">修正前</span>${esc(item.old_content)}</div>
                    <div class="diff-row add"><span class="diff-tag">修正後</span>${esc(item.new_content || art.content)}</div>
                  </div>` : ""}
              </div>
            `).join("")}
          </section>`;
      } else {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            <div class="card">
              <div class="card-body">${esc(art.legislative_reasons)}</div>
            </div>
          </section>`;
      }
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      此條尚無立法理由資料
    </div>`;
  }"""

assert target_legis in full_text, "target_legis not found"
full_text = full_text.replace(target_legis, replacement_legis)

# 3. Update refreshCCUStatus to set window.currentCCUStatus
target_ccu_status = """      if (data.authenticated) {
        if (badge) {
          badge.textContent = "● 連線正常 (有效)";"""

replacement_ccu_status = """      window.currentCCUStatus = data.authenticated ? 'authenticated' : 'unauthenticated';
      if (data.authenticated) {
        if (badge) {
          badge.textContent = "● 連線正常 (有效)";"""

assert target_ccu_status in full_text, "target_ccu_status not found"
full_text = full_text.replace(target_ccu_status, replacement_ccu_status)

# 4. Remove literature fallbacks:
target_lit_modal = """            <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; background: #121216; padding: 0.85rem 1.1rem; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 1.5rem; font-size: 0.85rem;">
              <div>👤 <b>作者：</b>${esc(lit.author || "法學學者")}${lit.author_affiliation ? ` (${esc(lit.author_affiliation)})` : ''}</div>
              <div>📚 <b>期刊：</b>${esc(lit.journal_name || "法學專論")}</div>"""

replacement_lit_modal = """            <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; background: #121216; padding: 0.85rem 1.1rem; border-radius: 8px; border: 1px solid #27272a; margin-bottom: 1.5rem; font-size: 0.85rem;">
              <div>👤 <b>作者：</b>${esc(lit.author || "")}${lit.author_affiliation ? ` (${esc(lit.author_affiliation)})` : ''}</div>
              <div>📚 <b>期刊：</b>${esc(lit.journal_name || "")}</div>"""

assert target_lit_modal in full_text, "target_lit_modal not found"
full_text = full_text.replace(target_lit_modal, replacement_lit_modal)

# 5. Toolbar meta:
target_toolbar = """    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      meta.textContent = `(${this.currentAct.category || "法規"} · ${this.currentAct.last_modified || "現行"})`;
    }"""

replacement_toolbar = """    const meta = document.getElementById("act-meta-inline");
    if (meta && this.currentAct) {
      const parts = [this.currentAct.category, this.currentAct.last_modified].filter(Boolean);
      meta.textContent = parts.length ? `(${parts.join(" · ")})` : "";
    }"""

assert target_toolbar in full_text, "target_toolbar not found"
full_text = full_text.replace(target_toolbar, replacement_toolbar)

with open("static/js/app.js", "w", encoding="utf-8") as f:
    f.write(full_text)

print("Successfully replaced all targets in app.js!")
