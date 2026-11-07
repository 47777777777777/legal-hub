import os

app_js_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js", "app.js")

with open(app_js_path, "r", encoding="utf-8") as f:
    text = f.read()

idx1 = text.find("renderLegislativeHtml")
idx2 = text.find("renderLegislativeHtml", idx1 + 1)
# Find the start of the method declaration before renderLegislativeHtml
start_idx = text.rfind("\n", 0, idx2)
if start_idx == -1:
    start_idx = idx2

# Find the start of renderMyBookmarksHtml after idx2
end_idx = text.find("renderMyBookmarksHtml", idx2)
# Walk back to the comment or empty line before renderMyBookmarksHtml
cut_end = text.rfind("\n  // ---------------- Tab 5:", idx2, end_idx)
if cut_end == -1:
    cut_end = text.rfind("\n", idx2, end_idx)

replacement = """
  // ---------------- Tab 4: 立法理由與沿革 ----------------
  renderLegislativeHtml(art) {
    const history = (art.source && art.amendment_history) ? art.amendment_history : [];
    const sourceInfo = (art.source === "lawplayer" && art.source_url) 
      ? `法律人 (${(art.fetched_at || "").substring(0, 10)})` 
      : (art.source ? `${art.source} (${(art.fetched_at || "").substring(0, 10)})` : "");
    const paywalledReasons = (art.paywalled_counts && art.paywalled_counts.legislative_reasons) ? art.paywalled_counts.legislative_reasons : 0;

    let paywalledNoticeHtml = "";
    if (paywalledReasons > 0) {
      paywalledNoticeHtml = `
        <div class="card" style="margin-bottom:1rem; border-left:3px solid #f59e0b; background:rgba(245,158,11,0.05);">
          <div class="card-body" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
            <span>法律人頁面標示本條有 ${paywalledReasons} 段立法理由（會員內容），無法在此顯示</span>
            ${art.source_url ? `<a href="${esc(art.source_url)}" target="_blank" rel="noopener" class="source-link" style="color:#60a5fa; text-decoration:none;">在法律人查看 ↗</a>` : ""}
          </div>
        </div>`;
    }

    if (art.source && (history.length || art.legislative_reasons || paywalledReasons > 0)) {
      if (history.length) {
        return `
          <section>${sectionHeading("file", "歷次修法理由與新舊法對照 Diff", `${history.length}`, sourceInfo)}
            ${paywalledNoticeHtml}
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
      } else if (art.legislative_reasons) {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            ${paywalledNoticeHtml}
            <div class="card">
              <div class="card-body">${esc(art.legislative_reasons)}</div>
            </div>
          </section>`;
      } else {
        return `
          <section>${sectionHeading("file", "制定與修正理由", null, sourceInfo)}
            ${paywalledNoticeHtml}
          </section>`;
      }
    }

    return `<div style="padding:1.5rem 0.5rem; text-align:center; color:#71717a; font-size:0.9rem;">
      此條尚無立法理由資料
    </div>`;
  }
"""

new_text = text[:start_idx] + replacement + text[cut_end:]
with open(app_js_path, "w", encoding="utf-8") as f:
    f.write(new_text)

print("Successfully updated app.js renderLegislativeHtml!")
